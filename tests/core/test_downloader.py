from pathlib import Path
from unittest import mock

import pytest
from yt_dlp.utils import DownloadError

from suiteav.core import downloader as dl
from suiteav.core.downloader import Preset

HOME, TEMP = Path("/out/Video"), Path("/cache/tmp/job")


def _pp_keys(opts):
    # FFmpegConcat è sempre presente (when=playlist) ma inattivo senza --concat-playlist
    return [(p["key"], p.get("when")) for p in opts["postprocessors"] if p["key"] != "FFmpegConcat"]


BEST = "bv*+ba/b"
EXPECTED = {
    Preset.MAX_360: ("bv*[height<=360]+ba/b[height<=360]", []),
    Preset.MAX_480: ("bv*[height<=480]+ba/b[height<=480]", []),
    Preset.MAX_720: ("bv*[height<=720]+ba/b[height<=720]", []),
    Preset.BEST: (BEST, []),
    Preset.BEST_MP4: ("bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]", []),
    Preset.BEST_SPLIT: (BEST, [("FFmpegSplitChapters", None)]),
    Preset.BEST_META: (BEST, [("FFmpegMetadata", None)]),
    Preset.MP3: ("bestaudio/best", [("FFmpegThumbnailsConvertor", "before_dl"),
                                    ("FFmpegExtractAudio", None), ("EmbedThumbnail", None)]),
    Preset.MP3_ALBUM_SPLIT: ("bestaudio/best", [("FFmpegThumbnailsConvertor", "before_dl"),
                                                ("FFmpegExtractAudio", None), ("EmbedThumbnail", None),
                                                ("FFmpegSplitChapters", None)]),
    Preset.MP3_BATCH: ("bestaudio/best", [("FFmpegExtractAudio", None)]),
    Preset.PL_META: (BEST, [("FFmpegMetadata", None)]),
    Preset.PL_SPLIT: (BEST, [("FFmpegSplitChapters", None)]),
    Preset.PL_NUMBERED: (BEST, []),
    Preset.PL_PLAIN: (BEST, []),
}


def test_every_preset_has_expectation():
    assert set(EXPECTED) | {Preset.MANUAL} == set(Preset)


@pytest.mark.parametrize("preset", list(EXPECTED))
def test_build_options(preset):
    fmt, pps = EXPECTED[preset]
    opts = dl.build_options(preset, HOME, TEMP)
    assert opts["format"] == fmt
    assert _pp_keys(opts) == pps
    assert opts["paths"] == {"home": str(HOME), "temp": str(TEMP)}
    assert opts["quiet"] is True and opts["noprogress"] is True
    expected_tmpl = "%(autonumber)s-%(title)s.%(ext)s" if preset is Preset.PL_NUMBERED else "%(title)s.%(ext)s"
    assert opts["outtmpl"]["default"] == expected_tmpl
    assert bool(opts.get("writethumbnail")) == (preset in (Preset.MP3, Preset.MP3_ALBUM_SPLIT))
    assert opts.get("merge_output_format") == ("mp4" if preset is Preset.BEST_MP4 else None)


def test_mp3_extracts_mp3_vbr0():
    opts = dl.build_options(Preset.MP3, HOME, TEMP)
    extract = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "mp3"
    assert extract["preferredquality"] == "0"


def test_manual_requires_format():
    assert dl.build_options(Preset.MANUAL, HOME, TEMP, format_id="137+140")["format"] == "137+140"
    with pytest.raises(ValueError):
        dl.build_argv(Preset.MANUAL)


# --- esecuzione con YoutubeDL mockato ---------------------------------------------

class FakeYDL:
    """Simula YoutubeDL: chiama gli hook come farebbe un download vero."""

    behaviour = "ok"

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def download(self, urls):
        temp = Path(self.opts["paths"]["temp"])
        (temp / "video.f137.mp4.part").write_text("x")
        info = {"title": "Video", "playlist_index": None}
        for hook in self.opts["progress_hooks"]:
            hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100,
                  "speed": 10.0, "eta": 5, "info_dict": info, "filename": "video.mp4"})
        if self.behaviour == "interrupt":
            raise KeyboardInterrupt
        if self.behaviour == "error":
            self.opts["logger"].error("\x1b[0;31mERROR:\x1b[0m [youtube] abc: Video unavailable")
            raise DownloadError("ERROR: [youtube] abc: Video unavailable")
        self.opts["logger"].warning("WARNING: something odd")
        for hook in self.opts["postprocessor_hooks"]:
            hook({"status": "started", "postprocessor": "Merger", "info_dict": info})
        for hook in self.opts["post_hooks"]:
            hook("/out/Video/Video.mp4")
        return 0


@pytest.fixture
def fake_ydl(monkeypatch):
    monkeypatch.setattr(dl, "YoutubeDL", FakeYDL)
    FakeYDL.behaviour = "ok"
    return FakeYDL


def test_download_emits_events(fake_ydl, tmp_path):
    events = []
    res = dl.download(["https://x"], Preset.BEST, tmp_path / "out", tmp_path, events.append)
    kinds = [e.kind for e in events]
    assert kinds == ["downloading", "warning", "postprocessing"]
    assert events[0].downloaded == 50 and events[0].total == 100 and events[0].title == "Video"
    assert events[1].message == "something odd"
    assert res.files == ["/out/Video/Video.mp4"] and res.errors == []
    assert list((tmp_path / "tmp").iterdir()) == []  # temp del job rimossa


def test_chapter_files_are_reported(fake_ydl, monkeypatch, tmp_path):
    def download(self, urls):
        info = {"title": "Album", "chapters": [
            {"title": "Uno", "filepath": "/out/Audio/Album - 001 Uno.mp3"},
            {"title": "Due", "filepath": "/out/Audio/Album - 002 Due.mp3"}]}
        for hook in self.opts["postprocessor_hooks"]:
            hook({"status": "started", "postprocessor": "SplitChapters", "info_dict": info})
            hook({"status": "finished", "postprocessor": "SplitChapters", "info_dict": info})
        for hook in self.opts["post_hooks"]:
            hook("/out/Audio/Album.mp3")
        return 0
    monkeypatch.setattr(FakeYDL, "download", download)
    res = dl.download(["https://x"], Preset.MP3_ALBUM_SPLIT, tmp_path / "out", tmp_path, lambda e: None)
    assert res.files == ["/out/Audio/Album - 001 Uno.mp3", "/out/Audio/Album - 002 Due.mp3",
                         "/out/Audio/Album.mp3"]


def test_download_error_is_readable(fake_ydl, tmp_path):
    fake_ydl.behaviour = "error"
    with pytest.raises(dl.DownloadFailed) as exc:
        dl.download(["https://x"], Preset.BEST, tmp_path / "out", tmp_path, lambda e: None)
    assert str(exc.value) == "[youtube] abc: Video unavailable"
    assert list((tmp_path / "tmp").iterdir()) == []


def test_interrupt_cleans_temp(fake_ydl, tmp_path):
    fake_ydl.behaviour = "interrupt"
    with pytest.raises(KeyboardInterrupt):
        dl.download(["https://x"], Preset.BEST, tmp_path / "out", tmp_path, lambda e: None)
    assert list((tmp_path / "tmp").iterdir()) == []


def test_list_formats_error(monkeypatch):
    def boom(self, url, download=False):
        self.params["logger"].error("ERROR: Unsupported URL: https://nope")
        raise DownloadError("ERROR: Unsupported URL: https://nope")
    monkeypatch.setattr(dl.YoutubeDL, "extract_info", boom)
    with pytest.raises(dl.DownloadFailed, match="Unsupported URL"):
        dl.list_formats("https://nope")
