"""Unico punto in cui il codice distingue tra Linux, Windows e macOS."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import platformdirs

APP_NAME = "suiteav"
OS_RELEASE = Path("/etc/os-release")

# Famiglie di distro riconosciute tramite ID / ID_LIKE di /etc/os-release
_DISTRO_FAMILIES = {
    "arch": "pacman",
    "debian": "apt",
    "ubuntu": "apt",
    "fedora": "dnf",
    "rhel": "dnf",
    "centos": "dnf",
}

_FFMPEG_HINTS = {
    "windows": "winget install --source winget Gyan.FFmpeg",
    "macos": "brew install ffmpeg",
    "apt": "sudo apt install ffmpeg",
    "pacman": "sudo pacman -S ffmpeg",
    # Nei repo ufficiali Fedora il pacchetto si chiama ffmpeg-free (include libmp3lame)
    "dnf": "sudo dnf install ffmpeg-free",
}
_FFMPEG_GENERIC_HINT = "https://ffmpeg.org/download.html"


def os_name() -> str:
    """Restituisce 'windows', 'macos' o 'linux'."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _parse_os_release(text: str) -> dict[str, str]:
    data = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def linux_package_manager(os_release: Path = OS_RELEASE) -> str | None:
    """Package manager della distro ('apt', 'pacman', 'dnf') o None se non riconosciuta."""
    try:
        data = _parse_os_release(os_release.read_text(encoding="utf-8"))
    except OSError:
        return None
    ids = [data.get("ID", "")] + data.get("ID_LIKE", "").split()
    for distro_id in ids:
        if distro_id in _DISTRO_FAMILIES:
            return _DISTRO_FAMILIES[distro_id]
    return None


def ffmpeg_install_hint(system: str | None = None, os_release: Path = OS_RELEASE) -> str:
    """Comando (o URL) da mostrare all'utente per installare ffmpeg."""
    system = system or os_name()
    if system == "linux":
        key = linux_package_manager(os_release)
    else:
        key = system
    return _FFMPEG_HINTS.get(key, _FFMPEG_GENERIC_HINT)


def open_folder(path: Path) -> None:
    """Apre la cartella nel file manager dell'OS. Solleva OSError se il comando manca."""
    system = os_name()
    if system == "windows":
        os.startfile(path)  # type: ignore[attr-defined]  # esiste solo su Windows
        return
    cmd = "open" if system == "macos" else "xdg-open"
    # Non si attende il processo: senza desktop environment xdg-open può ripiegare su
    # un programma che resta in primo piano e bloccherebbe la TUI.
    subprocess.Popen([cmd, str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def config_dir() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False))


def cache_dir() -> Path:
    return Path(platformdirs.user_cache_dir(APP_NAME, appauthor=False))


# Altezza a cui si allunga la console di Windows: il menu più lungo (YouTube) ne usa
# 36 col banner grande, le altre 4 sono margine.
MIN_CONSOLE_ROWS = 40


def ensure_console_rows(min_rows: int = MIN_CONSOLE_ROWS) -> bool:
    """Su Windows allunga la finestra della console classica (conhost) se è più bassa
    di min_rows: Windows 10 la apre di 30 righe. Windows Terminal ignora la richiesta.

    Puramente estetico: qualunque errore viene ignorato. True se la finestra è cambiata.
    """
    if os_name() != "windows":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class COORD(ctypes.Structure):
            _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [("Left", wintypes.SHORT), ("Top", wintypes.SHORT),
                        ("Right", wintypes.SHORT), ("Bottom", wintypes.SHORT)]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                        ("wAttributes", wintypes.WORD), ("srWindow", SMALL_RECT),
                        ("dwMaximumWindowSize", COORD)]

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k32.GetLargestConsoleWindowSize.restype = COORD
        handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        info = CONSOLE_SCREEN_BUFFER_INFO()
        if not k32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
            return False  # nessuna console (output rediretto)
        win = info.srWindow
        if win.Bottom - win.Top + 1 >= min_rows:
            return False
        # Non oltre quanto entra sullo schermo
        largest = k32.GetLargestConsoleWindowSize(handle).Y
        rows = min(min_rows, largest) if largest > 0 else min_rows
        if info.dwSize.Y < win.Top + rows:
            k32.SetConsoleScreenBufferSize(handle, COORD(info.dwSize.X, win.Top + rows))
        rect = SMALL_RECT(win.Left, win.Top, win.Right, win.Top + rows - 1)
        return bool(k32.SetConsoleWindowInfo(handle, True, ctypes.byref(rect)))
    except Exception:  # noqa: BLE001 — estetico, non deve mai impedire l'avvio
        return False
