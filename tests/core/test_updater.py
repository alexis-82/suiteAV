import io
import json
import urllib.error
from unittest import mock

import pytest

from suiteav.core import updater


def _response(payload):
    resp = io.BytesIO(json.dumps(payload).encode())
    resp.__enter__ = lambda self=resp: self
    resp.__exit__ = lambda *a: None
    cm = mock.MagicMock()
    cm.__enter__.return_value = resp
    return cm


@pytest.mark.parametrize("tag, expected", [
    ("v4.0.0", (4, 0, 0)),
    ("suiteAV-3.3", (3, 3)),
    ("2026.10.26", (2026, 10, 26)),
    ("suiteav", None),
])
def test_parse_version(tag, expected):
    assert updater.parse_version(tag) == expected


def test_newer_suiteav_available():
    with mock.patch.object(updater.urllib.request, "urlopen",
                           return_value=_response({"tag_name": "v99.0.0"})):
        info = updater.check_suiteav()
    assert info.latest == "v99.0.0" and info.available is True


def test_same_or_older_suiteav():
    with mock.patch.object(updater.urllib.request, "urlopen",
                           return_value=_response({"tag_name": "suiteAV-3.3"})):
        info = updater.check_suiteav()
    assert info.available is False


def test_tag_without_numbers_is_unknown():
    with mock.patch.object(updater.urllib.request, "urlopen",
                           return_value=_response({"tag_name": "suiteav"})):
        info = updater.check_suiteav()
    assert info.latest is None and info.available is None


def test_timeout_is_unknown():
    with mock.patch.object(updater.urllib.request, "urlopen", side_effect=TimeoutError):
        info = updater.check_yt_dlp("2026.11.23")
    assert info.latest is None and info.available is None


def test_network_error_is_unknown():
    with mock.patch.object(updater.urllib.request, "urlopen",
                           side_effect=urllib.error.URLError("offline")):
        assert updater.latest_suiteav() is None


def test_yt_dlp_update():
    with mock.patch.object(updater.urllib.request, "urlopen",
                           return_value=_response({"info": {"version": "2026.12.01"}})):
        info = updater.check_yt_dlp("2026.11.23")
    assert info.available is True


@pytest.mark.parametrize("payload", [[], "blocked", 42, None])
def test_non_object_json_is_unknown(payload):
    with mock.patch.object(updater.urllib.request, "urlopen", return_value=_response(payload)):
        assert updater.check_suiteav().latest is None
        assert updater.check_yt_dlp("2026.11.23").latest is None
