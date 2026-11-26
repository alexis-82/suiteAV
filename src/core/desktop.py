"""Lanciatore nel menu applicazioni di Linux (.desktop per l'utente, senza sudo)."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

import platformdirs

DESKTOP_NAME = "suiteav.desktop"
ICON_NAME = "suiteav.png"


def _data_home() -> Path:
    # $XDG_DATA_HOME o ~/.local/share: cartelle lette da tutti i desktop environment
    return Path(platformdirs.user_data_dir())


def desktop_path() -> Path:
    return _data_home() / "applications" / DESKTOP_NAME


def icon_path() -> Path:
    return _data_home() / "icons" / ICON_NAME


def launch_command() -> list[str]:
    """Comando assoluto: il PATH della sessione grafica spesso non contiene ~/.local/bin."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    argv0 = Path(sys.argv[0]).absolute()
    if argv0.name == "__main__.py":  # python -m suiteav
        return [sys.executable, "-m", "suiteav"]
    if argv0.suffix == ".py":        # python suiteAV.py (da sorgente)
        return [sys.executable, str(argv0.resolve())]
    # Comando suiteav installato: niente resolve(), il link in ~/.local/bin
    # resta valido dopo `uv tool upgrade`.
    return [str(argv0)]


def _quote(arg: str) -> str:
    # Regole di quoting della Desktop Entry Specification per la chiave Exec
    if not any(c in arg for c in ' \t\n"\'\\><~|&;$*?#()`'):
        return arg
    escaped = "".join("\\" + c if c in '"`$\\' else c for c in arg)
    return f'"{escaped}"'


def desktop_entry(command: list[str], icon: Path) -> str:
    exec_line = " ".join(_quote(a) for a in command).replace("%", "%%")
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=suiteAV\n"
        "GenericName=YouTube downloader & audio converter\n"
        "GenericName[it]=Downloader YouTube e convertitore audio\n"
        "Comment=Download audio and video from YouTube and SoundCloud, convert audio to MP3\n"
        "Comment[it]=Scarica audio e video da YouTube e SoundCloud, converte audio in MP3\n"
        f"Exec={exec_line}\n"
        f"Icon={icon}\n"
        "Terminal=true\n"
        "Categories=AudioVideo;Audio;Video;\n"
    )


def install() -> Path:
    """Scrive icona e .desktop; sovrascrive un'installazione precedente."""
    icon = icon_path()
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes(resources.files("suiteav").joinpath("assets", ICON_NAME).read_bytes())

    desktop = desktop_path()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop.write_text(desktop_entry(launch_command(), icon), encoding="utf-8")
    return desktop


def uninstall() -> bool:
    """Rimuove .desktop e icona; False se non c'era nulla da rimuovere."""
    removed = False
    for p in (desktop_path(), icon_path()):
        if p.exists():
            p.unlink()
            removed = True
    return removed
