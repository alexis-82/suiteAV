"""Check (solo lettura) delle ultime versioni di suiteAV e yt-dlp."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from suiteav import __version__

GITHUB_LATEST = "https://api.github.com/repos/alexis-82/suiteAV/releases/latest"
PYPI_YT_DLP = "https://pypi.org/pypi/yt-dlp/json"
TIMEOUT = 3


@dataclass
class UpdateInfo:
    installed: str
    latest: str | None  # None = non verificabile (rete, API, tag senza numeri)

    @property
    def available(self) -> bool | None:
        if self.latest is None:
            return None
        latest, installed = parse_version(self.latest), parse_version(self.installed)
        if latest is None or installed is None:
            return None
        return latest > installed


def parse_version(tag: str) -> tuple[int, ...] | None:
    """'v4.0.0' → (4,0,0), 'suiteAV-3.3' → (3,3), '2026.10.26' → (2026,10,26)."""
    numbers = re.findall(r"\d+", tag)
    return tuple(int(n) for n in numbers) if numbers else None


def _get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={
        "User-Agent": f"suiteAV/{__version__}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    # Proxy o captive portal possono rispondere con JSON valido ma non oggetto
    return data if isinstance(data, dict) else None


def latest_suiteav() -> str | None:
    data = _get_json(GITHUB_LATEST)
    tag = data.get("tag_name") if data else None
    return tag if tag and parse_version(tag) else None


def latest_yt_dlp() -> str | None:
    data = _get_json(PYPI_YT_DLP)
    return data.get("info", {}).get("version") if data else None


def check_suiteav() -> UpdateInfo:
    return UpdateInfo(__version__, latest_suiteav())


def check_yt_dlp(installed: str) -> UpdateInfo:
    return UpdateInfo(installed, latest_yt_dlp())
