"""ui/notify non ha logica di dominio, ma il contratto 'mai bloccante' va garantito."""

import sys
import types

from suiteav.ui import notify


def test_backend_error_is_swallowed(monkeypatch):
    class Broken:
        def __init__(self, **kwargs):
            pass

        def send(self, **kwargs):
            raise RuntimeError("dbus non disponibile")

    monkeypatch.setitem(sys.modules, "desktop_notifier",
                        types.SimpleNamespace(DesktopNotifierSync=Broken))
    monkeypatch.setattr(notify, "_notifier", None)
    assert notify._deliver("suiteAV", "fatto") is False


def test_uses_suiteav_icon(monkeypatch):
    from desktop_notifier import Icon

    created = {}

    class Recorder:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def send(self, **kwargs):
            pass

    monkeypatch.setitem(sys.modules, "desktop_notifier",
                        types.SimpleNamespace(DesktopNotifierSync=Recorder, Icon=Icon))
    monkeypatch.setattr(notify, "_notifier", None)
    assert notify._deliver("suiteAV", "fatto") is True
    icon = created["app_icon"]
    assert icon.path.name == "suiteav.png" and icon.path.read_bytes()[:4] == b"\x89PNG"


def test_import_error_is_swallowed(monkeypatch):
    monkeypatch.setitem(sys.modules, "desktop_notifier", None)  # import → ImportError
    monkeypatch.setattr(notify, "_notifier", None)
    assert notify._deliver("suiteAV", "fatto") is False


def test_library_logged_errors_do_not_reach_stderr():
    """In un processo pulito (senza gli handler di logging di pytest)."""
    import subprocess

    script = """
import logging, sys, types

class LogsInternally:
    # Come desktop-notifier: cattura l'errore e lo registra con logger.exception
    def __init__(self, **kwargs):
        pass
    def send(self, **kwargs):
        try:
            raise ConnectionError("dbus non raggiungibile")
        except ConnectionError:
            logging.getLogger("desktop_notifier.backends.dbus").exception("Notification failed")

sys.modules["desktop_notifier"] = types.SimpleNamespace(DesktopNotifierSync=LogsInternally)
from suiteav.ui import notify
notify._deliver("suiteAV", "fatto")
"""
    res = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert "Traceback" not in res.stderr and "Notification failed" not in res.stderr


def test_files_summary():
    assert notify.files_summary([]) == ""
    assert notify.files_summary(["/a/Video/Brano.mp3"]) == "Brano.mp3"
    assert notify.files_summary(["/a/01.mp3", "/a/02.mp3", "/a/03.mp3"]) == "01.mp3 (+2)"


def test_send_returns_immediately_when_backend_hangs(monkeypatch):
    """Come su macOS senza autorizzazione: il backend non risponde mai."""
    import threading
    import time

    release = threading.Event()
    delivered = []

    def hanging_deliver(title, message):
        release.wait(10)
        delivered.append(title)
        return True

    monkeypatch.setattr(notify, "_deliver", hanging_deliver)
    monkeypatch.setattr(notify, "_queue", None)
    start = time.monotonic()
    notify.send("suiteAV", "fatto")
    assert time.monotonic() - start < 0.5
    assert delivered == []
    release.set()
    for _ in range(50):
        if delivered:
            break
        time.sleep(0.02)
    assert delivered == ["suiteAV"]
