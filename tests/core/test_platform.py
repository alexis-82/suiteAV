from pathlib import Path
from unittest import mock

import pytest

from suiteav.core import platform as plat


def _os_release(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "os-release"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.mark.parametrize("content, expected", [
    ('ID=arch\n', "pacman"),
    ('ID=cachyos\nID_LIKE=arch\n', "pacman"),
    ('ID=ubuntu\nID_LIKE=debian\n', "apt"),
    ('ID="linuxmint"\nID_LIKE="ubuntu debian"\n', "apt"),
    ('ID=fedora\n', "dnf"),
    ('ID=gentoo\n', None),
])
def test_linux_package_manager(tmp_path, content, expected):
    assert plat.linux_package_manager(_os_release(tmp_path, content)) == expected


def test_linux_package_manager_missing_file(tmp_path):
    assert plat.linux_package_manager(tmp_path / "nope") is None


@pytest.mark.parametrize("content, hint", [
    ('ID=arch\n', "sudo pacman -S ffmpeg"),
    ('ID=ubuntu\n', "sudo apt install ffmpeg"),
    ('ID=fedora\n', "sudo dnf install ffmpeg-free"),
    ('ID=gentoo\n', "https://ffmpeg.org/download.html"),
])
def test_ffmpeg_hint_linux(tmp_path, content, hint):
    assert plat.ffmpeg_install_hint("linux", _os_release(tmp_path, content)) == hint


def test_ffmpeg_hint_windows_macos():
    assert plat.ffmpeg_install_hint("windows") == "winget install --source winget Gyan.FFmpeg"
    assert plat.ffmpeg_install_hint("macos") == "brew install ffmpeg"


@pytest.mark.parametrize("platform_id, expected", [
    ("win32", "windows"), ("darwin", "macos"), ("linux", "linux"),
])
def test_os_name(platform_id, expected):
    with mock.patch.object(plat.sys, "platform", platform_id):
        assert plat.os_name() == expected


def test_open_folder_linux_does_not_wait(tmp_path):
    with mock.patch.object(plat, "os_name", return_value="linux"), \
         mock.patch.object(plat.subprocess, "Popen") as popen:
        plat.open_folder(tmp_path)
    assert popen.call_args.args[0] == ["xdg-open", str(tmp_path)]
    assert popen.call_args.kwargs["start_new_session"] is True
    popen.return_value.wait.assert_not_called()


def test_open_folder_macos(tmp_path):
    with mock.patch.object(plat, "os_name", return_value="macos"), \
         mock.patch.object(plat.subprocess, "Popen") as popen:
        plat.open_folder(tmp_path)
    assert popen.call_args.args[0] == ["open", str(tmp_path)]


def test_open_folder_missing_command_raises(tmp_path):
    with mock.patch.object(plat, "os_name", return_value="linux"), \
         mock.patch.object(plat.subprocess, "Popen", side_effect=FileNotFoundError("xdg-open")):
        with pytest.raises(OSError):
            plat.open_folder(tmp_path)


def test_open_folder_windows(tmp_path):
    startfile = mock.Mock()
    with mock.patch.object(plat, "os_name", return_value="windows"), \
         mock.patch.object(plat.os, "startfile", startfile, create=True), \
         mock.patch.object(plat.subprocess, "Popen") as popen:
        plat.open_folder(tmp_path)
    startfile.assert_called_once_with(tmp_path)
    popen.assert_not_called()


def test_ensure_console_rows_noop_outside_windows():
    with mock.patch.object(plat, "os_name", return_value="linux"):
        assert plat.ensure_console_rows() is False


@pytest.mark.skipif(plat.sys.platform != "win32", reason="API della console di Windows")
def test_ensure_console_rows_without_console_does_not_fail():
    # In CI l'output è rediretto: nessuna console, nessuna eccezione
    assert plat.ensure_console_rows() is False


def test_enable_windows_vt_noop_outside_windows():
    with mock.patch.object(plat, "os_name", return_value="linux"):
        assert plat.enable_windows_vt() is False


@pytest.mark.skipif(plat.sys.platform != "win32", reason="API della console di Windows")
def test_enable_windows_vt_without_console_does_not_fail():
    assert plat.enable_windows_vt() is False


@pytest.mark.parametrize("var", ["WT_SESSION", "TERM_PROGRAM"])
def test_ensure_console_rows_skipped_in_conpty_terminals(monkeypatch, var):
    """In Windows Terminal la finestra non si allunga: ridimensionare la console interna
    farebbe credere a Rich di avere righe che non si vedono."""
    monkeypatch.setenv(var, "x")
    with mock.patch.object(plat, "os_name", return_value="windows"), \
         mock.patch("ctypes.windll", create=True) as windll:
        assert plat.ensure_console_rows() is False
    windll.kernel32.SetConsoleWindowInfo.assert_not_called()
