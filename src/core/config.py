"""Lettura/creazione di config.toml nella cartella di config dell'OS."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

from suiteav.core import platform as plat
from suiteav.core.i18n import N_

CONFIG_FILENAME = "config.toml"
LANGUAGES = ("auto", "it", "en")
DEFAULT_LANGUAGE = "auto"
OUTPUT_SUBDIRS = ("Audio", "Video", "Converted")


@dataclass
class Config:
    download_dir: Path
    language: str
    # Avvisi su valori non validi: (messaggio sorgente, parametri), tradotti alla
    # visualizzazione perché la config si carica prima di attivare la lingua.
    warnings: list[tuple[str, dict]] = field(default_factory=list)

    @property
    def audio_dir(self) -> Path:
        return self.download_dir / "Audio"

    @property
    def video_dir(self) -> Path:
        return self.download_dir / "Video"

    @property
    def converted_dir(self) -> Path:
        return self.download_dir / "Converted"


def default_download_dir() -> str:
    # Cartella Download dell'OS col suo nome reale: su Linux XDG_DOWNLOAD_DIR di
    # user-dirs.dirs (es. ~/Scaricati), su Windows/macOS la cartella di sistema.
    return str(Path(platformdirs.user_downloads_dir()) / "suiteAV")


def _toml_literal(value: str) -> str:
    # Stringa letterale TOML: nessun escape, quindi C:\Users\... resta valido.
    if "'" in value or "\n" in value:
        raise ValueError(f"valore non rappresentabile come stringa letterale TOML: {value!r}")
    return f"'{value}'"


def write(path: Path, download_dir: str, language: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Configurazione suiteAV\n"
        f"download_dir = {_toml_literal(download_dir)}\n"
        "# auto | it | en\n"
        f"language = {_toml_literal(language)}\n",
        encoding="utf-8",
    )


def load(config_dir: Path | None = None) -> Config:
    """Carica la config, creandola con i default al primo avvio.

    Un file TOML malformato solleva tomllib.TOMLDecodeError: meglio fermarsi
    con un errore chiaro che sovrascrivere la config dell'utente.
    """
    path = (config_dir or plat.config_dir()) / CONFIG_FILENAME
    if not path.exists():
        write(path, default_download_dir(), DEFAULT_LANGUAGE)

    with path.open("rb") as f:
        data = tomllib.load(f)

    warnings = []

    language = data.get("language", DEFAULT_LANGUAGE)
    if language not in LANGUAGES:
        warnings.append((N_("language = {value!r} is not valid (allowed: {allowed}): using {default!r}"),
                         dict(value=language, allowed=", ".join(LANGUAGES), default=DEFAULT_LANGUAGE)))
        language = DEFAULT_LANGUAGE

    raw_dir = data.get("download_dir", None)
    if raw_dir is None:
        raw_dir = default_download_dir()
    if not isinstance(raw_dir, str) or not raw_dir.strip():
        warnings.append((N_("download_dir = {value!r} is not valid: using {default!r}"),
                         dict(value=raw_dir, default=default_download_dir())))
        raw_dir = default_download_dir()
    download_dir = Path(raw_dir).expanduser()

    cfg = Config(download_dir=download_dir, language=language, warnings=warnings)
    for sub in OUTPUT_SUBDIRS:
        (cfg.download_dir / sub).mkdir(parents=True, exist_ok=True)
    return cfg
