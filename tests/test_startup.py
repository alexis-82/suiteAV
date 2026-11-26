"""Avvio con configurazioni problematiche: messaggio chiaro, niente traceback."""

import subprocess
import sys


def _run(tmp_path, config_text):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "config.toml").write_text(config_text, encoding="utf-8")
    # La cartella di config si sostituisce nel processo figlio: su Windows platformdirs
    # la chiede al sistema e ignora APPDATA, quindi le variabili d'ambiente non bastano.
    code = ("import sys; from pathlib import Path; from suiteav.core import platform as p; "
            "p.config_dir = lambda: Path(sys.argv[1]); "
            "from suiteav.__main__ import main; main()")
    return subprocess.run([sys.executable, "-c", code, str(cfg)], capture_output=True,
                          text=True, timeout=30, stdin=subprocess.DEVNULL)


def test_download_dir_not_creatable(tmp_path):
    blocker = tmp_path / "file.txt"
    blocker.write_text("un file, non una cartella")
    res = _run(tmp_path, f"download_dir = '{blocker / 'sub'}'\nlanguage = 'en'\n")
    assert res.returncode == 1
    assert "Traceback" not in res.stderr
    assert "folder not accessible" in res.stderr and "config.toml" in res.stderr


def test_malformed_config(tmp_path):
    res = _run(tmp_path, "download_dir = \n")
    assert res.returncode == 1
    assert "Traceback" not in res.stderr and "invalid" in res.stderr
