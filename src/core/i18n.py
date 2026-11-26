"""Risoluzione della lingua e catalogo gettext.

Le stringhe sorgente sono in inglese; l'unico catalogo è l'italiano.
Il .mo si legge con importlib.resources (funziona anche da zip/build congelata).
"""

from __future__ import annotations

import gettext
import locale
import os
from collections.abc import Callable, Mapping
from importlib import resources

DOMAIN = "suiteav"
_ENV_VARS = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")

_translations: gettext.NullTranslations = gettext.NullTranslations()


def _is_italian(value: str) -> bool:
    value = value.lower()
    # 'it_IT.UTF-8', 'it', 'Italian_Italy' (Windows)
    return value.startswith("it_") or value == "it" or value.startswith("it.") \
        or value.startswith("italian")


def resolve_language(setting: str,
                     environ: Mapping[str, str] = os.environ,
                     getlocale: Callable[[], tuple[str | None, str | None]] = locale.getlocale) -> str:
    """'it' o 'en' a partire dal valore di config ('auto' | 'it' | 'en')."""
    if setting in ("it", "en"):
        return setting
    for var in _ENV_VARS:
        value = environ.get(var)
        if value:
            # LANGUAGE può essere una lista 'it:en'
            return "it" if _is_italian(value.split(":")[0]) else "en"
    try:
        name = getlocale()[0]
    except ValueError:
        name = None
    return "it" if name and _is_italian(name) else "en"


def _load_catalog(lang: str) -> gettext.NullTranslations:
    if lang == "en":
        return gettext.NullTranslations()
    mo = resources.files("suiteav").joinpath("locales", lang, "LC_MESSAGES", f"{DOMAIN}.mo")
    if not mo.is_file():
        return gettext.NullTranslations()
    with mo.open("rb") as f:
        return gettext.GNUTranslations(f)


def setup(setting: str) -> str:
    """Attiva la lingua e restituisce quella scelta ('it' | 'en')."""
    global _translations
    lang = resolve_language(setting)
    _translations = _load_catalog(lang)
    return lang


def _(message: str) -> str:
    return _translations.gettext(message)


def N_(message: str) -> str:
    """Marca una stringa per l'estrazione senza tradurla subito (tradotta poi con _())."""
    return message
