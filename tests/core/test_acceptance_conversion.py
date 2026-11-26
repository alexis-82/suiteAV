"""Criteri di accettazione della conversione, con ffmpeg reale (plan + run_batch)."""

import base64
import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

from suiteav.core import converter as conv

pytestmark = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                reason="ffmpeg/ffprobe non disponibili")

CODECS = {".flac": "flac", ".m4a": "aac", ".aac": "aac", ".wav": "pcm_s16le",
          ".ogg": "vorbis", ".opus": "libopus"}


def _audio(path: Path, ext: str, title: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
           "-i", "sine=duration=1", "-c:a", CODECS[ext]]
    if CODECS[ext] == "vorbis":  # encoder nativo, presente in ogni build (libvorbis no)
        cmd += ["-strict", "-2", "-ac", "2"]
    if ext != ".aac":
        cmd += ["-metadata", f"title={title}", "-metadata", "artist=Artista",
                "-metadata", "album=Album"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


def test_single_file_goes_to_converted_root(tmp_path):
    src = _audio(tmp_path / "musica" / "brano.flac", ".flac", "Brano")
    converted = tmp_path / "Converted"
    res = conv.run_batch(conv.plan(src, converted), lambda e: None)
    assert res.converted == [converted / "brano.mp3"]
    assert (converted / "brano.mp3").is_file()


def test_folder_all_formats_nested_with_cover_and_ignored(tmp_path):
    root = tmp_path / "X"
    sources = {
        "a.flac": ".flac", "sub/b.m4a": ".m4a", "sub/c.aac": ".aac",
        "sub/deep/d.wav": ".wav", "e.ogg": ".ogg", "sub/f.opus": ".opus",
    }
    for rel, ext in sources.items():
        _audio(root / rel, ext, Path(rel).stem)
    cover = tmp_path / "cover.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "color=blue:s=8x8", "-frames:v", "1", str(cover)], check=True)
    pic = Picture()
    pic.type, pic.mime, pic.data = 3, "image/jpeg", cover.read_bytes()
    flac = FLAC(root / "a.flac")
    flac.add_picture(pic)
    flac.save()
    (root / "sub" / "leggimi.txt").write_text("non audio")
    (root / "folder.jpg").write_bytes(cover.read_bytes())

    converted = tmp_path / "Converted"
    res = conv.run_batch(conv.plan(root, converted), lambda e: None)

    expected = {(converted / "X" / rel).with_suffix(".mp3") for rel in sources}
    assert set(res.converted) == expected and res.failed == []
    assert sorted(p.name for p in res.ignored) == ["folder.jpg", "leggimi.txt"]
    for mp3 in expected:
        assert abs(MP3(mp3).info.bitrate - 320_000) < 1_000
    for rel in sources:
        if rel.endswith(".aac"):
            continue  # ADTS grezzo non ha tag da copiare
        tags = ID3((converted / "X" / rel).with_suffix(".mp3"))
        assert str(tags["TIT2"]) == Path(rel).stem
        assert str(tags["TPE1"]) == "Artista" and str(tags["TALB"]) == "Album"
    apics = ID3(converted / "X" / "a.mp3").getall("APIC")
    assert len(apics) == 1 and apics[0].data == cover.read_bytes()

    # Criterio: rilanciare salta i file già convertiti e li conta come saltati
    res2 = conv.run_batch(conv.plan(root, converted), lambda e: None)
    assert res2.converted == [] and len(res2.skipped) == len(sources)
