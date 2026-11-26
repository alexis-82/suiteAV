"""Playlist da file di link (4 varianti della v3.3)."""

from __future__ import annotations

from suiteav.app import AppContext
from suiteav.core.downloader import Preset
from suiteav.core.i18n import _
from suiteav.screens.youtube import from_file
from suiteav.ui import prompts


def run(ctx: AppContext) -> None:
    entries = [
        (prompts.Item(_("Playlist with metadata"), "meta"), from_file(Preset.PL_META)),
        (prompts.Item(_("Playlist split by chapters"), "split"), from_file(Preset.PL_SPLIT)),
        (prompts.Item(_("Playlist with numbering"), "numbered"), from_file(Preset.PL_NUMBERED)),
        (prompts.Item(_("Playlist"), "plain"), from_file(Preset.PL_PLAIN)),
    ]
    handlers = {item.value: handler for item, handler in entries}

    while True:
        ctx.screen(_("Playlist from a file of links"))
        choice = prompts.select(_("Choose an option"), [item for item, _h in entries])
        if choice is None:
            return
        handlers[choice](ctx)
