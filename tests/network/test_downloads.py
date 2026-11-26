"""Download reali da YouTube (criterio: ogni preset scarica nella cartella giusta).

Lenti e dipendenti dalla rete e da YouTube: girano solo con SUITEAV_NETWORK=1.
Video di prova: "Me at the zoo" (19 s).
"""

import os
import shutil
from pathlib import Path

import pytest

from suiteav.core import downloader as dl
from suiteav.core.downloader import Preset

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(os.environ.get("SUITEAV_NETWORK") != "1",
                       reason="test di rete: impostare SUITEAV_NETWORK=1"),
    pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg non disponibile"),
]

URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Preset a URL singolo; le varianti "split" richiedono un video con capitoli (vedi sotto)
SINGLE = [Preset.MAX_360, Preset.MAX_480, Preset.MAX_720, Preset.BEST, Preset.BEST_MP4,
          Preset.BEST_META, Preset.MP3]
FROM_FILE = [Preset.MP3_BATCH, Preset.PL_META, Preset.PL_NUMBERED, Preset.PL_PLAIN]


def _run(preset, tmp_path, urls=(URL,), format_id=None):
    home = tmp_path / ("Audio" if preset in dl.AUDIO_PRESETS else "Video")
    res = dl.download(list(urls), preset, home, tmp_path / "cache", lambda e: None,
                      format_id=format_id)
    return home, res


@pytest.mark.parametrize("preset", SINGLE + FROM_FILE, ids=lambda p: p.value)
def test_preset_downloads_into_right_folder(preset, tmp_path):
    home, res = _run(preset, tmp_path)
    assert res.errors == []
    assert res.files and all(Path(f).parent == home for f in res.files)
    assert all(Path(f).is_file() for f in res.files)
    if preset in dl.AUDIO_PRESETS:
        assert all(f.endswith(".mp3") for f in res.files)
    if preset is Preset.BEST_MP4:
        assert res.files[0].endswith(".mp4")
    if preset is Preset.PL_NUMBERED:
        assert Path(res.files[0]).name.startswith("00001-")
    assert list((tmp_path / "cache" / "tmp").iterdir()) == []


def test_manual_format(tmp_path):
    info = dl.list_formats(URL)
    fmt = next(f["format_id"] for f in info["formats"]
               if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none"))
    home, res = _run(Preset.MANUAL, tmp_path, format_id=fmt)
    assert res.files and Path(res.files[0]).parent == home


def test_invalid_link_is_readable(tmp_path):
    with pytest.raises(dl.DownloadFailed) as exc:
        _run(Preset.BEST, tmp_path, urls=("https://www.youtube.com/watch?v=xxxxxxxxxxx",))
    assert "Traceback" not in str(exc.value) and str(exc.value).strip()


def test_unsupported_link_is_readable(tmp_path):
    with pytest.raises(dl.DownloadFailed) as exc:
        _run(Preset.BEST, tmp_path, urls=("https://example.invalid/nothing",))
    assert "Traceback" not in str(exc.value)


SPLIT_URL = os.environ.get("SUITEAV_CHAPTERS_URL")


@pytest.mark.skipif(not SPLIT_URL, reason="impostare SUITEAV_CHAPTERS_URL con un video con capitoli")
@pytest.mark.parametrize("preset", [Preset.BEST_SPLIT, Preset.MP3_ALBUM_SPLIT, Preset.PL_SPLIT],
                         ids=lambda p: p.value)
def test_split_by_chapters(preset, tmp_path):
    home, res = _run(preset, tmp_path, urls=(SPLIT_URL,))
    chapters = [f for f in res.files if " - 0" in Path(f).name]
    assert len(chapters) > 1  # un file per capitolo, riportati nel risultato
    assert all(Path(f).is_file() and Path(f).parent == home for f in res.files)
    if preset in dl.AUDIO_PRESETS:
        assert all(f.endswith(".mp3") for f in chapters)
