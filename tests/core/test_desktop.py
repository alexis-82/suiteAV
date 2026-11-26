import configparser
import os
import subprocess
import sys

import pytest

from suiteav.core import desktop

linux_only = pytest.mark.skipif(sys.platform != "linux", reason="lanciatore .desktop solo su Linux")


def _parse(text: str) -> configparser.SectionProxy:
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    cp.read_string(text)
    return cp["Desktop Entry"]


def test_entry_fields(tmp_path):
    entry = _parse(desktop.desktop_entry(["/home/u/.local/bin/suiteav"], tmp_path / "i.png"))
    assert entry["Exec"] == "/home/u/.local/bin/suiteav"
    assert entry["Terminal"] == "true"
    assert entry["Type"] == "Application"
    assert entry["Icon"] == str(tmp_path / "i.png")


def test_exec_quoting():
    text = desktop.desktop_entry(["/opt/my apps/python", "/a/$b/100%.py"], desktop.icon_path())
    assert _parse(text)["Exec"] == '"/opt/my apps/python" "/a/\\$b/100%%.py"'


@linux_only
def test_install_and_uninstall(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path = desktop.install()
    assert path == tmp_path / "applications" / "suiteav.desktop"
    icon = tmp_path / "icons" / "suiteav.png"
    assert icon.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert _parse(path.read_text())["Icon"] == str(icon)

    desktop.install()  # ripetibile
    assert desktop.uninstall() is True
    assert not path.exists() and not icon.exists()
    assert desktop.uninstall() is False


@linux_only
def test_cli_flag(tmp_path):
    env = {**os.environ, "XDG_DATA_HOME": str(tmp_path)}
    res = subprocess.run([sys.executable, "-m", "suiteav", "--install-desktop"], env=env,
                         capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "applications" / "suiteav.desktop").exists()
    if (validate := __import__("shutil").which("desktop-file-validate")):
        out = subprocess.run([validate, str(tmp_path / "applications" / "suiteav.desktop")],
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr

    res = subprocess.run([sys.executable, "-m", "suiteav", "--uninstall-desktop"], env=env,
                         capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    assert res.returncode == 0 and "removed" in res.stdout
    assert not (tmp_path / "applications" / "suiteav.desktop").exists()


@pytest.mark.parametrize("argv0, expected", [
    ("/home/u/.local/bin/suiteav", ["/home/u/.local/bin/suiteav"]),
    ("/x/src/__main__.py", [sys.executable, "-m", "suiteav"]),
])
def test_launch_command(monkeypatch, argv0, expected):
    monkeypatch.setattr(sys, "argv", [argv0])
    assert desktop.launch_command() == expected
