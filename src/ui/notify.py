"""Notifiche desktop a fine job. Mai bloccanti: se falliscono, si prosegue.

Su macOS funzionano solo con un interprete Python firmato (best effort).
La consegna avviene in un thread a parte: su macOS la richiesta di
autorizzazione può non rispondere mai, su Linux D-Bus senza server di
notifiche attende fino a 25 s. La TUI non deve aspettare nessuno dei due.
"""

from __future__ import annotations

import logging
import queue
import threading
from importlib.resources import as_file, files
from pathlib import Path

_notifier = None
_queue: queue.SimpleQueue | None = None
_icon_file = None  # tiene vivo il file dell'icona (estratto se il pacchetto è zippato)

# desktop-notifier intercetta da sé gli errori del backend ma li registra con
# logger.exception: senza handler Python li stampa su stderr, dentro la TUI.
_lib_logger = logging.getLogger("desktop_notifier")
_lib_logger.addHandler(logging.NullHandler())
_lib_logger.propagate = False


def _app_icon():
    """Icona di suiteAV; senza, desktop-notifier mostra il logo di Python."""
    global _icon_file
    try:
        from desktop_notifier import Icon
        if _icon_file is None:
            _icon_file = as_file(files("suiteav") / "assets" / "suiteav.png").__enter__()
        return Icon(path=_icon_file)
    except Exception:  # noqa: BLE001 — meglio una notifica senza icona che nessuna notifica
        return None


def files_summary(paths: list) -> str:
    """Testo della notifica: nome del file, oppure il primo seguito da (+N)."""
    names = [Path(p).name for p in paths]
    if len(names) <= 1:
        return "".join(names)
    return f"{names[0]} (+{len(names) - 1})"


def send(title: str, message: str) -> None:
    """Accoda la notifica e ritorna subito."""
    global _queue
    if _queue is None:
        _queue = queue.SimpleQueue()
        # daemon: un backend bloccato non impedisce l'uscita dal programma
        threading.Thread(target=_worker, args=(_queue,), name="suiteav-notify",
                         daemon=True).start()
    _queue.put((title, message))


def _worker(q: queue.SimpleQueue) -> None:
    while True:
        _deliver(*q.get())


def _deliver(title: str, message: str) -> bool:
    """Consegna sincrona (solo dal thread delle notifiche); False se non riuscita."""
    global _notifier
    try:
        if _notifier is None:
            from desktop_notifier import DesktopNotifierSync
            _notifier = DesktopNotifierSync(app_name="suiteAV", app_icon=_app_icon())
        _notifier.send(title=title, message=message)
        return True
    except Exception:  # noqa: BLE001 — qualunque errore del backend non deve fermare il programma
        return False
