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


def _deps(ffmpeg=True, ffprobe=True, lame=True):
    from suiteav.core.deps import DepsStatus, Tool
    return DepsStatus(ffmpeg=Tool("ffmpeg", "/x" if ffmpeg else None),
                      ffprobe=Tool("ffprobe", "/x" if ffprobe else None),
                      libmp3lame=lame, deno=Tool("deno", "/x"),
                      yt_dlp_version="2026.11.23", yt_dlp_ejs=True)


def test_require_ffmpeg_rereads_state(monkeypatch):
    """ffmpeg installato a programma aperto: lo stato dell'avvio non deve bloccare."""
    from suiteav import app

    monkeypatch.setattr(app.deps_mod, "check", lambda: _deps())
    ctx = AppContext(config=None, deps=_deps(ffmpeg=False, ffprobe=False, lame=False))
    assert app.require_ffmpeg(ctx, "motivo") is True
    assert app.require_ffmpeg(ctx, "motivo", for_conversion=True) is True


def test_require_ffmpeg_conversion_needs_encoder(monkeypatch, capsys):
    from suiteav import app

    monkeypatch.setattr(app.deps_mod, "check", lambda: _deps(lame=False))
    monkeypatch.setattr(app.prompts, "pause", lambda: None)
    ctx = AppContext(config=None, deps=_deps())
    assert app.require_ffmpeg(ctx, "motivo") is True  # i download non richiedono libmp3lame
    assert app.require_ffmpeg(ctx, "motivo", for_conversion=True) is False
    assert "MP3 encoder missing" in capsys.readouterr().out
