"""Verifica delle dipendenze esterne: ffmpeg/ffprobe, deno, yt-dlp, yt-dlp-ejs."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass

_TIMEOUT = 10


@dataclass
class Tool:
    name: str
    path: str | None = None
    version: str | None = None

    @property
    def found(self) -> bool:
        return self.path is not None


@dataclass
class DepsStatus:
    ffmpeg: Tool
    ffprobe: Tool
    libmp3lame: bool
    deno: Tool
    yt_dlp_version: str
    yt_dlp_ejs: bool

    @property
    def can_convert(self) -> bool:
        return self.ffmpeg.found and self.ffprobe.found and self.libmp3lame


def _run(args: list[str]) -> str | None:
    try:
        res = subprocess.run(args, capture_output=True, text=True,
                             timeout=_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return res.stdout if res.returncode == 0 else None


def _first_line_token(output: str | None, index: int) -> str | None:
    if not output:
        return None
    tokens = output.splitlines()[0].split()
    return tokens[index] if len(tokens) > index else None


def _ffmpeg_like(name: str) -> Tool:
    path = shutil.which(name)
    if not path:
        return Tool(name)
    # "ffmpeg version n8.0.1 Copyright ..." → token 2
    return Tool(name, path, _first_line_token(_run([path, "-version"]), 2))


def _has_libmp3lame(ffmpeg: Tool) -> bool:
    if not ffmpeg.found:
        return False
    out = _run([ffmpeg.path, "-hide_banner", "-encoders"])
    return bool(out) and "libmp3lame" in out


def find_deno() -> str | None:
    """Stessa logica di yt-dlp: prima il bin/ del venv (wheel `deno`), poi accanto
    all'eseguibile se congelato (build Windows), poi il PATH."""
    exe = "deno" + (sysconfig.get_config_var("EXE") or "")
    dirs = [sysconfig.get_path("scripts")]
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))
    for d in dirs:
        candidate = os.path.join(d, exe)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("deno")


def _deno() -> Tool:
    path = find_deno()
    if not path:
        return Tool("deno")
    # "deno 2.9.8 (stable, release, x86_64-unknown-linux-gnu)" → token 1
    return Tool("deno", path, _first_line_token(_run([path, "--version"]), 1))


def _yt_dlp_version() -> str:
    from yt_dlp.version import __version__
    return __version__


def check() -> DepsStatus:
    ffmpeg = _ffmpeg_like("ffmpeg")
    return DepsStatus(
        ffmpeg=ffmpeg,
        ffprobe=_ffmpeg_like("ffprobe"),
        libmp3lame=_has_libmp3lame(ffmpeg),
        deno=_deno(),
        yt_dlp_version=_yt_dlp_version(),
        yt_dlp_ejs=importlib.util.find_spec("yt_dlp_ejs") is not None,
    )
