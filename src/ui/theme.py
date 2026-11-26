"""Console Rich condivisa e palette usata da tutte le schermate."""

from rich.console import Console
from rich.theme import Theme

from suiteav.core.platform import enable_windows_vt

THEME = Theme({
    "banner": "bold red",
    "subtitle": "bold green",
    "author": "dim green",
    "title": "bold cyan",
    "ok": "bold black on green",
    "warn": "bold black on yellow",
    "err": "bold black on red",
    "unknown": "bold black on cyan",
    "muted": "dim",
    "hint": "bold yellow",
})

# Prima della Console: Rich decide alla creazione se usare ANSI o le API legacy di Windows.
# Se l'attivazione è riuscita lo si dice esplicitamente, invece di lasciarlo dedurre.
_vt = enable_windows_vt()
console = Console(theme=THEME, highlight=False, legacy_windows=False if _vt else None)


def clear_all() -> None:
    """Pulisce schermo e scrollback: all'avvio non resta il testo precedente del terminale."""
    if not console.is_terminal:
        return
    console.clear()
    if not console.legacy_windows:
        # ESC[3J cancella anche lo scrollback (xterm, VTE, Konsole, Windows Terminal, iTerm2).
        # Sulla console legacy di Windows la sequenza verrebbe stampata come testo.
        console.file.write("\x1b[3J")
        console.file.flush()
