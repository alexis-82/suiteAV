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
    assert plat.ffmpeg_install_hint("windows") == "winget install Gyan.FFmpeg"
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
