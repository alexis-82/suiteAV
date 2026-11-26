"""Avvio con configurazioni problematiche: messaggio chiaro, niente traceback."""

import os
import subprocess
import sys


def _run(tmp_path, config_text):
    # Linux/Windows leggono da XDG_CONFIG_HOME/APPDATA, macOS da ~/Library/Application Support
    for cfg in (tmp_path / "xdg" / "suiteav",
                tmp_path / "Library" / "Application Support" / "suiteav"):
        cfg.mkdir(parents=True)
        (cfg / "config.toml").write_text(config_text, encoding="utf-8")
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "xdg"), "HOME": str(tmp_path),
           "APPDATA": str(tmp_path / "xdg"), "LOCALAPPDATA": str(tmp_path / "xdg")}
    return subprocess.run([sys.executable, "-m", "suiteav"], env=env, capture_output=True,
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
