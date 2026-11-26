"""Menu YouTube / SoundCloud: voci video, audio e accesso alle playlist da file."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from suiteav.app import AppContext, require_ffmpeg
from suiteav.core import downloader as dl
from suiteav.core import platform as plat
from suiteav.core.downloader import Preset
from suiteav.core.i18n import _
from suiteav.ui import notify, prompts
from suiteav.ui.progress import DownloadProgress
from suiteav.ui.theme import console


# --- helper condivisi con screens/playlist.py ----------------------------------------

def _require_ffmpeg(ctx: AppContext) -> bool:
    return require_ffmpeg(ctx, _("it is required to merge and convert files."))


def read_url_file(path: str) -> list[str] | None:
    """URL da file: una per riga, righe vuote e commenti (#) ignorati."""
    try:
        lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        console.print(f"[err] {_('ERROR')} [/] {_('Cannot read the file')}: {e}")
        return None
    urls = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if not urls:
        console.print(f"[warn] {_('Empty file')} [/] {_('No links found in')} {path}")
        return None
    return urls


def run_download(ctx: AppContext, urls: list[str], preset: Preset,
                 format_id: str | None = None) -> None:
    home = ctx.config.audio_dir if preset in dl.AUDIO_PRESETS else ctx.config.video_dir
    console.print()
    try:
        with DownloadProgress() as progress:
            result = dl.download(urls, preset, home, plat.cache_dir(), progress.handle,
                                 format_id=format_id)
    except KeyboardInterrupt:
        console.print(f"\n[warn] {_('Operation interrupted')} [/]")
        return
    except dl.DownloadFailed as e:
        console.print(f"\n[err] {_('ERROR')} [/] {e}")
        notify.send(_("Download failed"), str(e))
        return

    console.print()
    console.print(f"[ok] {_('Completed')} [/] {_('Files saved in')} {home}:")
    for f in result.files:
        console.print(f"  • {Path(f).name}")
    for err in dict.fromkeys(result.errors):
        console.print(f"  [err] ! [/] {err}")
    notify.send(_("Download completed with errors") if result.errors
                else _("Download completed"), notify.files_summary(result.files))


# --- voci del menu ----------------------------------------------------------------

def _ask_url() -> str | None:
    return prompts.text(_("Paste the link (Esc = back):"))


def _formats_table(info: dict) -> Table:
    table = Table(title=info.get("title"), header_style="title", expand=False)
    for col in ("ID", "EXT", _("Resolution"), "FPS", _("Video codec"), _("Audio codec"), _("Size")):
        table.add_column(col)
    for f in info.get("formats") or []:
        size = f.get("filesize") or f.get("filesize_approx")
        table.add_row(
            str(f.get("format_id", "")), str(f.get("ext", "")),
            str(f.get("resolution") or ""), str(f.get("fps") or ""),
            str(f.get("vcodec") or "").replace("none", "—"),
            str(f.get("acodec") or "").replace("none", "—"),
            f"{size / 1_000_000:.1f} MB" if size else "",
        )
    return table


def _show_formats(url: str) -> bool:
    with console.status(_("Reading available formats…")):
        try:
            info = dl.list_formats(url)
        except dl.DownloadFailed as e:
            console.print(f"[err] {_('ERROR')} [/] {e}")
            return False
    if not info.get("formats"):
        console.print(f"[warn] {_('No formats found')} [/]")
        return False
    console.print(_formats_table(info))
    return True


def list_formats(ctx: AppContext) -> None:
    url = _ask_url()
    if url:
        _show_formats(url)
        prompts.pause()


def manual(ctx: AppContext) -> None:
    if not _require_ffmpeg(ctx):
        return
    url = _ask_url()
    if not url or not _show_formats(url):
        if url:
            prompts.pause()
        return
    format_id = prompts.text(_("Format ID (e.g. 137+140):"))
    if format_id:
        run_download(ctx, [url], Preset.MANUAL, format_id=format_id)
        prompts.pause()


def single(preset: Preset):
    def handler(ctx: AppContext) -> None:
        if not _require_ffmpeg(ctx):
            return
        url = _ask_url()
        if url:
            run_download(ctx, [url], preset)
            prompts.pause()
    return handler


def from_file(preset: Preset):
    def handler(ctx: AppContext) -> None:
        if not _require_ffmpeg(ctx):
            return
        path = prompts.path(_("File with the links, one per line (Esc = back):"))
        if not path:
            return
        urls = read_url_file(path)
        if urls:
            run_download(ctx, urls, preset)
        prompts.pause()
    return handler


def run(ctx: AppContext) -> None:
    from suiteav.screens import playlist

    entries = [
        _("Video"),
        (prompts.Item(_("Which resolutions are available?"), "formats"), list_formats),
        (prompts.Item(_("Download choosing the format manually"), "manual"), manual),
        (prompts.Item(_("Download up to 360p"), "max_360"), single(Preset.MAX_360)),
        (prompts.Item(_("Download up to 480p"), "max_480"), single(Preset.MAX_480)),
        (prompts.Item(_("Download up to 720p"), "max_720"), single(Preset.MAX_720)),
        (prompts.Item(_("Download best quality"), "best"), single(Preset.BEST)),
        (prompts.Item(_("Download best MP4"), "best_mp4"), single(Preset.BEST_MP4)),
        (prompts.Item(_("Download best quality, split by chapters"), "best_split"), single(Preset.BEST_SPLIT)),
        (prompts.Item(_("Download best quality with metadata"), "best_meta"), single(Preset.BEST_META)),
        _("Audio"),
        (prompts.Item(_("Download MP3 HQ"), "mp3"), single(Preset.MP3)),
        (prompts.Item(_("Download album to MP3 HQ, split by chapters"), "mp3_album"), single(Preset.MP3_ALBUM_SPLIT)),
        (prompts.Item(_("Download MP3 from a file of links"), "mp3_batch"), from_file(Preset.MP3_BATCH)),
        _("Playlist"),
        (prompts.Item(_("Playlist from a file of links…"), "playlist"), playlist.run),
    ]
    items = [e if isinstance(e, str) else e[0] for e in entries]
    handlers = {e[0].value: e[1] for e in entries if not isinstance(e, str)}

    while True:
        ctx.screen("YouTube / SoundCloud")
        choice = prompts.select(_("Choose an option"), items)
        if choice is None:
            return
        handlers[choice](ctx)
