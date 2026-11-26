#!/usr/bin/env python3
"""Avvio da sorgente: python suiteAV.py (senza installare il pacchetto).

Registra src/ come package `suiteav`, lo stesso nome che ha una volta installato.
"""

import importlib.util
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
_spec = importlib.util.spec_from_file_location(
    "suiteav", _SRC / "__init__.py", submodule_search_locations=[str(_SRC)])
_pkg = importlib.util.module_from_spec(_spec)
sys.modules["suiteav"] = _pkg
_spec.loader.exec_module(_pkg)

from suiteav.__main__ import main  # noqa: E402

main()
