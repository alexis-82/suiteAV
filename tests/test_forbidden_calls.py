"""Criterio: nessun os.system / shell=True / eval nel codice (G6)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"os\.system|shell=True|eval\(")


def test_no_shell_or_eval_in_source():
    files = [ROOT / "suiteAV.py", *sorted((ROOT / "src").rglob("*.py"))]
    assert len(files) > 10  # il glob ha trovato davvero il codice
    hits = [f"{f.relative_to(ROOT)}:{n}: {line.strip()}"
            for f in files
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
            if FORBIDDEN.search(line)]
    assert hits == []
