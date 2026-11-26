"""Stato delle dipendenze esterne e istruzioni di installazione."""

from __future__ import annotations

from rich.table import Table

from suiteav.app import AppContext
from suiteav.core import platform as plat
from suiteav.core.i18n import _
from suiteav.ui import prompts
from suiteav.ui.theme import console


def _row(ok: bool, detail: str | None) -> tuple[str, str]:
    return (f"[ok] {_('OK')} [/]" if ok else f"[err] {_('MISSING')} [/]"), (detail or "")


def run(ctx: AppContext) -> None:
    ctx.refresh_deps()
    d = ctx.deps
    ctx.screen(_("Dependencies"))

    reinstall = _("reinstall suiteAV (uv tool install --reinstall …)")
    ffmpeg_hint = plat.ffmpeg_install_hint()
    table = Table(header_style="title")
    table.add_column(_("Component"))
    table.add_column(_("Status"))
    table.add_column(_("Version / path"))
    table.add_column(_("How to fix"))

    table.add_row("ffmpeg", *_row(d.ffmpeg.found, d.ffmpeg.version), "" if d.ffmpeg.found else ffmpeg_hint)
    table.add_row("ffprobe", *_row(d.ffprobe.found, d.ffprobe.version), "" if d.ffprobe.found else ffmpeg_hint)
    table.add_row(_("MP3 encoder (libmp3lame)"), *_row(d.libmp3lame, None),
                  "" if d.libmp3lame or not d.ffmpeg.found else ffmpeg_hint)
    table.add_row("yt-dlp", *_row(True, d.yt_dlp_version), "")
    table.add_row("yt-dlp-ejs", *_row(d.yt_dlp_ejs, None), "" if d.yt_dlp_ejs else reinstall)
    table.add_row(_("JS runtime (deno)"), *_row(d.deno.found, d.deno.version or d.deno.path),
                  "" if d.deno.found else reinstall)
    console.print(table)
    if not (d.deno.found and d.yt_dlp_ejs):
        console.print(f"[warn] {_('JS runtime missing')} [/] "
                      f"{_('YouTube downloads may fail or miss formats.')}")
    prompts.pause()
