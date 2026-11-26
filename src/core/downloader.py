"""Download con yt-dlp: preset del menu → opzioni, esecuzione, eventi di avanzamento.

Le opzioni si costruiscono con yt_dlp.parse_options() a partire dagli stessi
flag CLI della v3.3: ordine dei postprocessor e dipendenze tra opzioni
(es. --embed-thumbnail → writethumbnail) restano identici alla CLI.
"""

from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

import yt_dlp
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


class Preset(Enum):
    MANUAL = "manual"
    MAX_360 = "max_360"
    MAX_480 = "max_480"
    MAX_720 = "max_720"
    BEST = "best"
    BEST_MP4 = "best_mp4"
    BEST_SPLIT = "best_split"
    BEST_META = "best_meta"
    MP3 = "mp3"
    MP3_ALBUM_SPLIT = "mp3_album_split"
    MP3_BATCH = "mp3_batch"
    PL_META = "pl_meta"
    PL_SPLIT = "pl_split"
    PL_NUMBERED = "pl_numbered"
    PL_PLAIN = "pl_plain"


AUDIO_PRESETS = frozenset({Preset.MP3, Preset.MP3_ALBUM_SPLIT, Preset.MP3_BATCH})

_BEST = "bv*+ba/b"
_MP3 = ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
_MP3_THUMB = [*_MP3, "--embed-thumbnail", "--convert-thumbnails", "jpg"]
_DEFAULT_OUTTMPL = "%(title)s.%(ext)s"


def _max_height(n: int) -> list[str]:
    return ["-f", f"bv*[height<={n}]+ba/b[height<={n}]"]


_FLAGS: dict[Preset, list[str]] = {
    Preset.MAX_360: _max_height(360),
    Preset.MAX_480: _max_height(480),
    Preset.MAX_720: _max_height(720),
    Preset.BEST: ["-f", _BEST],
    Preset.BEST_MP4: ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                      "--merge-output-format", "mp4"],
    Preset.BEST_SPLIT: ["-f", _BEST, "--split-chapters"],
    Preset.BEST_META: ["-f", _BEST, "--embed-metadata"],
    Preset.MP3: _MP3_THUMB,
    Preset.MP3_ALBUM_SPLIT: [*_MP3_THUMB, "--yes-playlist", "--split-chapters"],
    Preset.MP3_BATCH: _MP3,
    Preset.PL_META: ["-f", _BEST, "--embed-metadata"],
    Preset.PL_SPLIT: ["-f", _BEST, "--split-chapters"],
    Preset.PL_NUMBERED: ["-f", _BEST, "-o", "%(autonumber)s-%(title)s.%(ext)s"],
    Preset.PL_PLAIN: ["-f", _BEST],
}


def build_argv(preset: Preset, format_id: str | None = None) -> list[str]:
    if preset is Preset.MANUAL:
        if not format_id:
            raise ValueError("il preset MANUAL richiede format_id")
        flags = ["-f", format_id]
    else:
        flags = list(_FLAGS[preset])
    if "-o" not in flags:
        flags += ["-o", _DEFAULT_OUTTMPL]
    return flags


def build_options(preset: Preset, home: Path, temp: Path,
                  format_id: str | None = None) -> dict:
    argv = build_argv(preset, format_id) + ["-P", f"home:{home}", "-P", f"temp:{temp}"]
    # Con argv esplicito parse_options ignora i file di config di yt-dlp dell'utente
    opts = yt_dlp.parse_options(argv).ydl_opts
    # yt-dlp non deve stampare nulla: l'avanzamento passa dagli hook verso Rich
    opts.update(quiet=True, noprogress=True, no_warnings=False)
    return opts


# --- esecuzione ---------------------------------------------------------------

@dataclass
class DownloadEvent:
    kind: str  # "downloading" | "downloaded" | "postprocessing" | "warning"
    title: str = ""
    downloaded: int = 0
    total: int | None = None
    speed: float | None = None
    eta: int | None = None
    message: str = ""
    index: int | None = None   # posizione nella playlist/batch
    count: int | None = None


@dataclass
class DownloadResult:
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DownloadFailed(Exception):
    """Errore leggibile da mostrare all'utente (senza stack trace)."""


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _clean(msg: str) -> str:
    msg = _ANSI.sub("", str(msg)).strip()
    return re.sub(r"^(ERROR|WARNING):\s*", "", msg)


class _Logger:
    """Inoltra warning ed errori di yt-dlp invece di stamparli."""

    def __init__(self, on_event: Callable[[DownloadEvent], None], result: DownloadResult):
        self._on_event = on_event
        self._result = result

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self._on_event(DownloadEvent("warning", message=_clean(msg)))

    def error(self, msg: str) -> None:
        self._result.errors.append(_clean(msg))


def _progress_hook(on_event: Callable[[DownloadEvent], None]):
    def hook(d: dict) -> None:
        info = d.get("info_dict") or {}
        common = dict(title=info.get("title") or Path(d.get("filename", "")).name,
                      index=info.get("playlist_index") or info.get("__autonumber"),
                      count=info.get("n_entries"))
        if d["status"] == "downloading":
            on_event(DownloadEvent(
                "downloading",
                downloaded=d.get("downloaded_bytes") or 0,
                total=d.get("total_bytes") or d.get("total_bytes_estimate"),
                speed=d.get("speed"), eta=d.get("eta"), **common))
        elif d["status"] == "finished":
            on_event(DownloadEvent("downloaded", downloaded=d.get("downloaded_bytes") or 0,
                                   total=d.get("total_bytes"), **common))
    return hook


def _pp_hook(on_event: Callable[[DownloadEvent], None]):
    def hook(d: dict) -> None:
        if d["status"] == "started":
            info = d.get("info_dict") or {}
            on_event(DownloadEvent("postprocessing", title=info.get("title", ""),
                                   message=d.get("postprocessor", "")))
    return hook


def _chapter_files_hook(result: DownloadResult):
    """post_hooks riceve solo il file principale: i capitoli creati da
    FFmpegSplitChapters si leggono da info['chapters'][i]['filepath']."""
    def hook(d: dict) -> None:
        if d["status"] == "finished" and d.get("postprocessor") == "SplitChapters":
            for chapter in (d.get("info_dict") or {}).get("chapters") or []:
                path = chapter.get("filepath")
                if path and path not in result.files:
                    result.files.append(path)
    return hook


def new_temp_dir(cache_root: Path) -> Path:
    """Cartella temporanea dedicata al job, da rimuovere a fine job."""
    path = cache_root / "tmp" / f"job-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_formats(url: str) -> dict:
    """Info del video (formati inclusi) senza scaricare."""
    result = DownloadResult()
    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "noplaylist": True, "logger": _Logger(lambda e: None, result)}
    try:
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except DownloadError as e:
        raise DownloadFailed(result.errors[-1] if result.errors else _clean(e)) from None


def download(urls: list[str], preset: Preset, home: Path, cache_root: Path,
             on_event: Callable[[DownloadEvent], None],
             format_id: str | None = None) -> DownloadResult:
    """Scarica gli URL; errori per singolo URL finiscono in result.errors.

    La temp del job viene sempre rimossa, anche su Ctrl+C, così non
    restano file .part da nessuna parte.
    """
    temp = new_temp_dir(cache_root)
    result = DownloadResult()
    opts = build_options(preset, home, temp, format_id)
    opts.update(
        logger=_Logger(on_event, result),
        progress_hooks=[_progress_hook(on_event)],
        postprocessor_hooks=[_pp_hook(on_event), _chapter_files_hook(result)],
        post_hooks=[result.files.append],
    )
    try:
        with YoutubeDL(opts) as ydl:
            ydl.download(urls)
    except DownloadError as e:
        msg = _clean(e)
        if msg not in result.errors:
            result.errors.append(msg)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    if not result.files and result.errors:
        raise DownloadFailed("\n".join(dict.fromkeys(result.errors)))
    return result
