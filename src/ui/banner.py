"""Banner e testata di stato."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text

from suiteav import __version__
from suiteav.core.deps import DepsStatus
from suiteav.core.i18n import _
from suiteav.core.updater import UpdateInfo
from suiteav.ui.theme import console

_BANNER = (
    "  ███████ ██    ██ ██ ████████ ███████      █████  ██    ██\n"
    "  ██      ██    ██ ██    ██    ██          ██   ██ ██    ██\n"
    "  ███████ ██    ██ ██    ██    █████       ███████ ██    ██\n"
    "       ██ ██    ██ ██    ██    ██          ██   ██  ██  ██\n"
    " ███████  ██████  ██    ██    ███████     ██   ██   ████\n"
)


def show_banner() -> None:
    console.print(Text(_BANNER, style="banner"), justify="center")
    console.print(Text(f"suiteAV {__version__} • YouTube / SoundCloud downloader & audio converter",
                       style="subtitle"), justify="center")
    console.print(Text("Coded by Alexis", style="author"), justify="center")
    console.print()


def _badge(label: str, style: str) -> Text:
    return Text(f" {label} ", style=style)


def _update_badge(info: UpdateInfo | None) -> Text:
    if info is None:
        return _badge(_("checking…"), "muted")
    if info.available is None:
        return _badge(_("N/A"), "unknown")
    if info.available:
        return _badge(_("UPDATE {version}").format(version=info.latest), "err")
    return _badge(_("UP TO DATE"), "ok")


def _tool_badge(found: bool, version: str | None = None) -> Text:
    if not found:
        return _badge(_("MISSING"), "err")
    return _badge(version or _("OK"), "ok")


def build_header(deps: DepsStatus,
                 suiteav_update: UpdateInfo | None,
                 yt_dlp_update: UpdateInfo | None) -> Table:
    grid = Table.grid(padding=(0, 1))
    grid.add_column(justify="right", style="bold")
    grid.add_column()
    grid.add_column(justify="right", style="bold")
    grid.add_column()

    ffmpeg_badge = _tool_badge(deps.ffmpeg.found, deps.ffmpeg.version)
    if deps.ffmpeg.found and not deps.libmp3lame:
        ffmpeg_badge = _badge(_("NO MP3 ENCODER"), "warn")

    grid.add_row(f"suiteAV {__version__}", _update_badge(suiteav_update),
                 "ffmpeg", ffmpeg_badge)
    grid.add_row(f"yt-dlp {deps.yt_dlp_version}", _update_badge(yt_dlp_update),
                 _("JS runtime"), _tool_badge(deps.deno.found and deps.yt_dlp_ejs, deps.deno.version))
    return grid


def show_header(deps: DepsStatus,
                suiteav_update: UpdateInfo | None,
                yt_dlp_update: UpdateInfo | None) -> None:
    show_banner()
    console.print(build_header(deps, suiteav_update, yt_dlp_update), justify="center")
    console.print()
