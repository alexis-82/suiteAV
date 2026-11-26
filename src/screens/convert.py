"""Conversione audio locale → MP3 320 kbps."""

from __future__ import annotations

from pathlib import Path

from rich.table import Table

from suiteav.app import AppContext
from suiteav.core import converter as conv
from suiteav.core import platform as plat
from suiteav.core.i18n import _
from suiteav.ui import notify, prompts
from suiteav.ui.progress import ConvertProgress
from suiteav.ui.theme import console


def _require_ffmpeg(ctx: AppContext) -> bool:
    ctx.refresh_deps()
    if ctx.deps.can_convert:
        return True
    if not (ctx.deps.ffmpeg.found and ctx.deps.ffprobe.found):
        console.print(f"[err] {_('ffmpeg is missing')} [/] {_('it is required for the conversion.')}")
    else:
        console.print(f"[err] {_('MP3 encoder missing')} [/] "
                      f"{_('this ffmpeg build has no libmp3lame.')}")
    console.print(f"{_('Install it with')}: [hint]{plat.ffmpeg_install_hint()}[/]")
    prompts.pause()
    return False


def _summary(result: conv.BatchResult, out_dir: Path) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[ok] OK [/]", _("Converted"), str(len(result.converted)))
    table.add_row("[unknown] = [/]", _("Skipped"), str(len(result.skipped)))
    table.add_row("[err] ! [/]", _("Errors"), str(len(result.failed)))
    table.add_row("[muted] - [/]", _("Ignored (not audio)"), str(len(result.ignored)))
    console.print(table)
    console.print(f"{_('Output folder')}: {out_dir}")

    if result.failed:
        console.print()
        console.print(f"[err] {_('Errors')} [/]")
        for path, err in result.failed:
            console.print(f"  • {path.name}: {err}")
    if result.skipped:
        console.print()
        console.print(f"[unknown] {_('Skipped')} [/]")
        for path, why in result.skipped[:20]:
            console.print(f"  • {path.name}: {why}")
        if len(result.skipped) > 20:
            console.print(f"  … +{len(result.skipped) - 20}")
    if result.ignored:
        console.print()
        console.print(f"[muted]{_('Ignored (not audio)')}[/]")
        for path in result.ignored[:20]:
            console.print(f"  • {path.name}")
        if len(result.ignored) > 20:
            console.print(f"  … +{len(result.ignored) - 20}")


def run(ctx: AppContext) -> None:
    ctx.screen(_("Audio conversion (to MP3)"))
    console.print(_("Input formats: FLAC, M4A/AAC, WAV, OGG, OPUS → MP3 320 kbps."))
    console.print()
    if not _require_ffmpeg(ctx):
        return

    raw = prompts.path(_("File or folder to convert (Esc = back):"))
    if not raw:
        return
    source = Path(raw).expanduser()
    try:
        plan = conv.plan(source, ctx.config.converted_dir)
    except FileNotFoundError:
        console.print(f"[err] {_('ERROR')} [/] {_('Not found')}: {source}")
        prompts.pause()
        return

    out_dir = ctx.config.converted_dir if source.is_file() \
        else ctx.config.converted_dir / source.resolve().name
    console.print()
    console.print(_("To convert: {n}  ·  skipped: {s}  ·  ignored: {i}").format(
        n=len(plan.jobs), s=len(plan.skipped), i=len(plan.ignored)))

    if not plan.jobs:
        console.print(f"[warn] {_('Nothing to convert')} [/]")
        prompts.pause()
        return
    if not prompts.confirm(_("Start the conversion?")):
        return

    console.print()
    try:
        with ConvertProgress(len(plan.jobs)) as progress:
            result = conv.run_batch(plan, progress.handle,
                                    ffmpeg=ctx.deps.ffmpeg.path, ffprobe=ctx.deps.ffprobe.path)
    except KeyboardInterrupt:
        console.print(f"\n[warn] {_('Operation interrupted')} [/]")
        prompts.pause()
        return

    notify.send(_("Conversion completed with errors") if result.failed
                else _("Conversion completed"), notify.files_summary(result.converted))
    console.print()
    _summary(result, out_dir)
    prompts.pause()
