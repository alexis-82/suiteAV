"""Barre di avanzamento Rich alimentate dagli eventi di core/."""

from __future__ import annotations

from rich.filesize import decimal
from rich.progress import (BarColumn, Progress, SpinnerColumn, TaskID, TaskProgressColumn,
                           TextColumn)

from suiteav.core.downloader import DownloadEvent
from suiteav.core.i18n import _
from suiteav.ui.theme import console


def _fmt_speed(speed: float | None) -> str:
    return f"{decimal(int(speed))}/s" if speed else ""


def _fmt_eta(eta: int | None) -> str:
    if eta is None:
        return ""
    m, s = divmod(int(eta), 60)
    h, m = divmod(m, 60)
    return f"ETA {h}:{m:02d}:{s:02d}" if h else f"ETA {m:02d}:{s:02d}"


def _fmt_size(done: int, total: int | None) -> str:
    return f"{decimal(done)}/{decimal(total)}" if total else decimal(done)


class DownloadProgress:
    """Una riga per file: barra, dimensione, velocità, ETA, fase di postprocessing."""

    def __init__(self) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", markup=False),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            TextColumn("{task.fields[size]}"),
            TextColumn("{task.fields[speed]}"),
            TextColumn("{task.fields[eta]}"),
            console=console,
        )
        self._task: TaskID | None = None
        self._title: str | None = None

    def __enter__(self) -> "DownloadProgress":
        self._progress.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self._progress.__exit__(*exc)

    @staticmethod
    def _label(event: DownloadEvent) -> str:
        title = event.title if len(event.title) <= 40 else event.title[:39] + "…"
        if event.index and event.count:
            return f"[{event.index}/{event.count}] {title}"
        return title

    def _ensure_task(self, event: DownloadEvent) -> TaskID:
        if self._task is None or event.title != self._title:
            if self._task is not None:
                # Chiude la riga precedente prima di aprirne una nuova
                self._progress.update(self._task, description=self._label_done())
            self._title = event.title
            self._task = self._progress.add_task(self._label(event), total=None,
                                                 size="", speed="", eta="")
        return self._task

    def _label_done(self) -> str:
        task = self._progress.tasks[-1]
        return task.description.replace(" · " + _("processing…"), "")

    def handle(self, event: DownloadEvent) -> None:
        if event.kind == "warning":
            self._progress.console.print(f"[warn] ! [/] {event.message}")
            return
        task = self._ensure_task(event)
        if event.kind == "downloading":
            self._progress.update(task, completed=event.downloaded, total=event.total,
                                  size=_fmt_size(event.downloaded, event.total),
                                  speed=_fmt_speed(event.speed), eta=_fmt_eta(event.eta))
        elif event.kind == "downloaded":
            total = event.total or event.downloaded or 1
            self._progress.update(task, completed=total, total=total,
                                  size=_fmt_size(event.downloaded, event.total), speed="", eta="")
        elif event.kind == "postprocessing":
            description = self._label(event) + " · " + _("processing…")
            self._progress.update(task, description=description)


class ConvertProgress:
    """Barra totale (file N/M) + barra del file corrente."""

    def __init__(self, total: int) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}", markup=False),
            BarColumn(bar_width=30),
            TaskProgressColumn(),
            console=console,
        )
        self._total_task = self._progress.add_task(_("Total"), total=total)
        self._file_task = self._progress.add_task("", total=1.0)

    def __enter__(self) -> "ConvertProgress":
        self._progress.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self._progress.__exit__(*exc)

    def handle(self, event) -> None:
        name = event.src.name if len(event.src.name) <= 40 else event.src.name[:39] + "…"
        if event.kind == "start":
            self._progress.update(self._total_task,
                                  description=f"{_('Total')} [{event.index}/{event.total}]")
            self._progress.update(self._file_task, description=name, completed=0)
        elif event.kind == "progress":
            self._progress.update(self._file_task, completed=event.fraction)
        elif event.kind in ("done", "failed"):
            self._progress.update(self._file_task, completed=1.0)
            self._progress.advance(self._total_task)
            if event.kind == "failed":
                self._progress.console.print(f"[err] ! [/] {event.src.name}: {event.error}")
