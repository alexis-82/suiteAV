import subprocess
from unittest import mock

import pytest

from suiteav.core import deps

FFMPEG_VERSION = "ffmpeg version n8.0.1 Copyright (c) 2000-2026 the FFmpeg developers\n"
ENCODERS_OK = " A....D libmp3lame           libmp3lame MP3 (MPEG audio layer 3)\n"
ENCODERS_NO = " A....D aac                  AAC (Advanced Audio Coding)\n"


def _fake_run(encoders):
    def run(args, **kwargs):
        if "-encoders" in args:
            out = encoders
        elif args[-1] == "--version":
            out = "deno 2.9.8 (stable, release, x86_64-unknown-linux-gnu)\n"
        else:
            out = FFMPEG_VERSION.replace("ffmpeg", args[0].rsplit("/", 1)[-1], 1)
        return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")
    return run


@pytest.fixture(autouse=True)
def fixed_yt_dlp_version(monkeypatch):
    # Evita di importare yt_dlp mentre subprocess.run è mockato
    monkeypatch.setattr(deps, "_yt_dlp_version", lambda: "2026.11.23")


@pytest.fixture
def no_venv_deno(tmp_path, monkeypatch):
    monkeypatch.setattr(deps.sysconfig, "get_path", lambda name: str(tmp_path))


def test_all_present(no_venv_deno):
    with mock.patch.object(deps.shutil, "which", side_effect=lambda n: f"/usr/bin/{n}"), \
         mock.patch.object(deps.subprocess, "run", side_effect=_fake_run(ENCODERS_OK)):
        st = deps.check()
    assert st.ffmpeg.found and st.ffmpeg.version == "n8.0.1"
    assert st.ffprobe.version == "n8.0.1"
    assert st.libmp3lame is True
    assert st.deno.path == "/usr/bin/deno" and st.deno.version == "2.9.8"
    assert st.can_convert
    assert st.yt_dlp_version == "2026.11.23"


def test_ffmpeg_missing(no_venv_deno):
    with mock.patch.object(deps.shutil, "which", return_value=None), \
         mock.patch.object(deps.subprocess, "run") as run:
        st = deps.check()
    assert not st.ffmpeg.found and not st.ffprobe.found and not st.deno.found
    assert st.libmp3lame is False
    assert not st.can_convert
    run.assert_not_called()


def test_without_libmp3lame(no_venv_deno):
    with mock.patch.object(deps.shutil, "which", side_effect=lambda n: f"/usr/bin/{n}"), \
         mock.patch.object(deps.subprocess, "run", side_effect=_fake_run(ENCODERS_NO)):
        st = deps.check()
    assert st.ffmpeg.found and st.libmp3lame is False
    assert not st.can_convert


def test_deno_only_in_venv(tmp_path, monkeypatch):
    exe = tmp_path / ("deno" + (deps.sysconfig.get_config_var("EXE") or ""))
    exe.write_text("")
    exe.chmod(0o755)
    monkeypatch.setattr(deps.sysconfig, "get_path", lambda name: str(tmp_path))
    with mock.patch.object(deps.shutil, "which", return_value=None):
        assert deps.find_deno() == str(exe)


def test_deno_next_to_frozen_exe(tmp_path, monkeypatch):
    """Build Windows: deno.exe sta accanto a suiteAV.exe, fuori da qualunque venv."""
    exe = tmp_path / "app" / ("deno" + (deps.sysconfig.get_config_var("EXE") or ""))
    exe.parent.mkdir()
    exe.write_text("")
    exe.chmod(0o755)
    monkeypatch.setattr(deps.sysconfig, "get_path", lambda name: str(tmp_path / "nope"))
    monkeypatch.setattr(deps.sys, "frozen", True, raising=False)
    monkeypatch.setattr(deps.sys, "executable", str(tmp_path / "app" / "suiteAV.exe"))
    with mock.patch.object(deps.shutil, "which", return_value=None):
        assert deps.find_deno() == str(exe)


def test_deno_next_to_exe_ignored_when_not_frozen(tmp_path, monkeypatch):
    exe = tmp_path / ("deno" + (deps.sysconfig.get_config_var("EXE") or ""))
    exe.write_text("")
    exe.chmod(0o755)
    monkeypatch.setattr(deps.sysconfig, "get_path", lambda name: str(tmp_path / "nope"))
    monkeypatch.delattr(deps.sys, "frozen", raising=False)
    monkeypatch.setattr(deps.sys, "executable", str(tmp_path / "python"))
    with mock.patch.object(deps.shutil, "which", return_value=None):
        assert deps.find_deno() is None


def test_deno_only_in_path(no_venv_deno):
    with mock.patch.object(deps.shutil, "which", return_value="/opt/deno/bin/deno"):
        assert deps.find_deno() == "/opt/deno/bin/deno"


def test_version_command_failure(no_venv_deno):
    def run(args, **kwargs):
        raise OSError("boom")
    with mock.patch.object(deps.shutil, "which", side_effect=lambda n: f"/usr/bin/{n}"), \
         mock.patch.object(deps.subprocess, "run", side_effect=run):
        st = deps.check()
    assert st.ffmpeg.found and st.ffmpeg.version is None
    assert st.libmp3lame is False
