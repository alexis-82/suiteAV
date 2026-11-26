"""AppContext: un check di rete fallito in modo inatteso vale come 'N/A'."""

from concurrent.futures import Future

from suiteav.app import AppContext


def test_failed_future_is_unknown():
    failed = Future()
    failed.set_exception(AttributeError("'list' object has no attribute 'get'"))
    pending = Future()
    ctx = AppContext(config=None, deps=None, _suiteav_update=failed, _yt_dlp_update=pending)
    assert ctx.suiteav_update is None
    assert ctx.yt_dlp_update is None
