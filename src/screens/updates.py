"""Aggiornamenti: solo verifica, nessuna installazione (Non-Goal)."""

from __future__ import annotations

from rich.table import Table

from suiteav.app import AppContext
from suiteav.core import updater
from suiteav.core.i18n import _
from suiteav.core.updater import UpdateInfo
from suiteav.ui import prompts
from suiteav.ui.theme import console


def _status(info: UpdateInfo) -> str:
    if info.available is None:
        return f"[unknown] {_('N/A')} [/]"
    if info.available:
        return f"[err] {_('update available')} [/]"
    return f"[ok] {_('up to date')} [/]"


def run(ctx: AppContext) -> None:
    ctx.screen(_("Updates"))
    with console.status(_("Checking the latest versions…")):
        rows = [("suiteAV", updater.check_suiteav()),
                ("yt-dlp", updater.check_yt_dlp(ctx.deps.yt_dlp_version))]

    table = Table(header_style="title")
    table.add_column(_("Component"))
    table.add_column(_("Installed"))
    table.add_column(_("Latest"))
    table.add_column(_("Status"))
    for name, info in rows:
        table.add_row(name, info.installed, info.latest or "—", _status(info))
    console.print(table)
    if any(info.latest is None for _n, info in rows):
        console.print(f"[muted]{_('N/A: network unavailable or version not readable.')}[/]")
    prompts.pause()
