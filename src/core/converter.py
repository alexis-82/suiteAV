"""Conversione audio locale → MP3 320 kbps CBR con ffmpeg; copertina copiata con mutagen."""

from __future__ import annotations

import base64
import os
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover

from suiteav.core.i18n import _

# Ordine = priorità quando lo stesso brano esiste in più formati nella stessa cartella
AUDIO_EXTS = (".flac", ".wav", ".m4a", ".aac", ".opus", ".ogg")
BITRATE = "320k"


@dataclass
class Job:
    src: Path
    dst: Path


@dataclass
class Plan:
    jobs: list[Job] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)  # (sorgente, motivo)
    ignored: list[Path] = field(default_factory=list)              # file non audio


class ConversionError(Exception):
    pass


# --- pianificazione -----------------------------------------------------------------

def _priority(path: Path) -> int:
    return AUDIO_EXTS.index(path.suffix.lower())


def plan(source: Path, converted_dir: Path) -> Plan:
    """Cartella X/ → Converted/X/<relativo>.mp3; file singolo → Converted/<stem>.mp3."""
    source = source.expanduser().resolve()
    result = Plan()

    if source.is_file():
        candidates = [(source, converted_dir / f"{source.stem}.mp3")] \
            if source.suffix.lower() in AUDIO_EXTS else []
        if not candidates:
            result.ignored.append(source)
    elif source.is_dir():
        candidates = []
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            # "._nome.flac": metadati AppleDouble lasciati da macOS su FAT/exFAT, non audio
            if path.suffix.lower() in AUDIO_EXTS and not path.name.startswith("._"):
                rel = path.relative_to(source).with_suffix(".mp3")
                candidates.append((path, converted_dir / source.name / rel))
            else:
                result.ignored.append(path)
    else:
        raise FileNotFoundError(source)

    # Raggruppate senza distinguere maiuscole/minuscole: su macOS, Windows e chiavette
    # FAT "Brano.mp3" e "brano.mp3" sono lo stesso file e uno sovrascriverebbe l'altro.
    by_dst: dict[str, tuple[Path, list[Path]]] = {}
    for src, dst in candidates:
        by_dst.setdefault(str(dst).casefold(), (dst, []))[1].append(src)

    for dst, sources in by_dst.values():
        sources.sort(key=_priority)
        chosen, duplicates = sources[0], sources[1:]
        for dup in duplicates:
            result.skipped.append((dup, _("duplicate of {name}").format(name=chosen.name)))
        if dst.exists():
            result.skipped.append((chosen, _("already converted")))
        else:
            result.jobs.append(Job(chosen, dst))

    result.jobs.sort(key=lambda j: j.src)
    return result


# --- copertina ----------------------------------------------------------------------

def _read_cover(src: Path) -> tuple[bytes, str] | None:
    """(dati, mime) della copertina incorporata nel sorgente, se presente."""
    try:
        audio = mutagen.File(src)
    except mutagen.MutagenError:
        return None
    if audio is None or audio.tags is None:
        return None

    if isinstance(audio, FLAC) and audio.pictures:
        pic = next((p for p in audio.pictures if p.type == 3), audio.pictures[0])
        return pic.data, pic.mime
    if isinstance(audio, MP4):
        covers = audio.tags.get("covr")
        if covers:
            cover = covers[0]
            mime = "image/png" if cover.imageformat == MP4Cover.FORMAT_PNG else "image/jpeg"
            return bytes(cover), mime
        return None
    # Ogg Vorbis / Opus: immagine in base64 nel commento METADATA_BLOCK_PICTURE
    blocks = audio.tags.get("metadata_block_picture") if hasattr(audio.tags, "get") else None
    if blocks and isinstance(blocks, list) and isinstance(blocks[0], str):
        try:
            pic = Picture(base64.b64decode(blocks[0]))
        except (ValueError, mutagen.MutagenError):
            return None
        return pic.data, pic.mime
    # WAV / AAC con tag ID3
    if isinstance(audio.tags, ID3):
        apics = audio.tags.getall("APIC")
        if apics:
            return apics[0].data, apics[0].mime
    return None


def _write_cover(mp3: Path, cover: tuple[bytes, str]) -> None:
    data, mime = cover
    try:
        tags = ID3(mp3)
    except ID3NoHeaderError:
        tags = ID3()
    tags.delall("APIC")
    tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
    # v2.3 come scrive ffmpeg (-id3v2_version 3): mutagen salverebbe in v2.4
    tags.save(mp3, v2_version=3)


# --- conversione singola ------------------------------------------------------------

def _duration(src: Path, ffprobe: str) -> float | None:
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
            capture_output=True, text=True, timeout=30, check=False).stdout
        return float(out.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def _metadata_source(src: Path) -> str:
    # Ogg/Opus tengono i tag sullo stream audio, gli altri contenitori a livello di file;
    # l'MP3 li vuole a livello di file.
    return "0:s:a:0" if src.suffix.lower() in (".ogg", ".opus") else "0"


def _ffmpeg_cmd(src: Path, part: Path, ffmpeg: str) -> list[str]:
    # Percorsi assoluti: un nome che inizia con '-' non viene letto come opzione.
    return [
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
        "-i", str(src),
        "-vn",
        "-map_metadata", _metadata_source(src),
        "-c:a", "libmp3lame", "-b:a", BITRATE,
        "-id3v2_version", "3",
        "-f", "mp3",  # ffmpeg non deduce il formato dall'estensione .part
        "-progress", "pipe:1", "-nostats",
        str(part),
    ]


def convert_one(src: Path, dst: Path,
                on_progress: Callable[[float], None] | None = None,
                ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> None:
    """Converte src in dst (MP3). Scrive su dst.part e rinomina solo a conversione riuscita."""
    src, dst = src.resolve(), dst.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.name + ".part")
    duration = _duration(src, ffprobe)

    proc = subprocess.Popen(_ffmpeg_cmd(src, part, ffmpeg), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, errors="replace")
    # stderr va svuotato mentre ffmpeg lavora: un file parzialmente danneggiato
    # produce centinaia di KB di errori, la pipe si riempie e ffmpeg si blocca.
    # Si tengono solo le ultime righe per il messaggio d'errore.
    stderr_tail: deque[str] = deque(maxlen=20)
    stderr_reader = threading.Thread(
        target=lambda: stderr_tail.extend(ln for ln in proc.stderr if ln.strip()), daemon=True)
    stderr_reader.start()
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if on_progress and duration and line.startswith("out_time_us="):
                try:
                    us = int(line.split("=", 1)[1])
                except ValueError:
                    continue
                on_progress(min(us / 1_000_000 / duration, 1.0))
        proc.wait()
    except BaseException:
        # Ctrl+C o altro: niente processi orfani né .part residui
        proc.kill()
        proc.wait()
        part.unlink(missing_ok=True)
        raise
    finally:
        stderr_reader.join(timeout=5)

    if proc.returncode != 0:
        part.unlink(missing_ok=True)
        last = stderr_tail[-1].strip() if stderr_tail else f"ffmpeg exit code {proc.returncode}"
        raise ConversionError(last)

    try:
        cover = _read_cover(src)
        if cover:
            _write_cover(part, cover)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    os.replace(part, dst)
    if on_progress:
        on_progress(1.0)


# --- batch --------------------------------------------------------------------------

@dataclass
class ConvertEvent:
    kind: str  # "start" | "progress" | "done" | "failed"
    index: int
    total: int
    src: Path
    fraction: float = 0.0
    error: str = ""


@dataclass
class BatchResult:
    converted: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    ignored: list[Path] = field(default_factory=list)


def run_batch(p: Plan, on_event: Callable[[ConvertEvent], None],
              ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> BatchResult:
    """Conversione sequenziale; un file che fallisce non ferma gli altri.

    KeyboardInterrupt si propaga (il .part corrente è già stato rimosso).
    """
    result = BatchResult(skipped=list(p.skipped), ignored=list(p.ignored))
    total = len(p.jobs)
    for i, job in enumerate(p.jobs, 1):
        on_event(ConvertEvent("start", i, total, job.src))
        try:
            convert_one(job.src, job.dst,
                        lambda f, i=i, job=job: on_event(ConvertEvent("progress", i, total, job.src, f)),
                        ffmpeg=ffmpeg, ffprobe=ffprobe)
        except (ConversionError, OSError, mutagen.MutagenError) as e:
            result.failed.append((job.src, str(e)))
            on_event(ConvertEvent("failed", i, total, job.src, error=str(e)))
            continue
        result.converted.append(job.dst)
        on_event(ConvertEvent("done", i, total, job.src, 1.0))
    return result
