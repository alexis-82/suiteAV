import base64
import shutil
import subprocess
from pathlib import Path

import pytest
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3
from mutagen.mp3 import MP3, BitrateMode
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from suiteav.core import converter as conv

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg/ffprobe non disponibili")

TAGS = {"title": "Brano", "artist": "Artista", "album": "Album", "track": "3"}
CODECS = {".flac": "flac", ".m4a": "aac", ".aac": "aac", ".wav": "pcm_s16le",
          ".ogg": "libvorbis", ".opus": "libopus"}


def _touch(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# --- plan() ---------------------------------------------------------------------------

def test_plan_single_file(tmp_path):
    src = _touch(tmp_path / "musica" / "brano.flac")
    p = conv.plan(src, tmp_path / "Converted")
    assert [(j.src, j.dst) for j in p.jobs] == [(src, tmp_path / "Converted" / "brano.mp3")]


def test_plan_single_non_audio(tmp_path):
    src = _touch(tmp_path / "cover.jpg")
    p = conv.plan(src, tmp_path / "Converted")
    assert p.jobs == [] and p.ignored == [src]


def test_plan_nested_folder_no_collision(tmp_path):
    root = tmp_path / "Disco"
    a = _touch(root / "CD1" / "01.flac")
    b = _touch(root / "CD2" / "01.FLAC")
    txt = _touch(root / "note.txt")
    p = conv.plan(root, tmp_path / "Converted")
    assert {(j.src, j.dst) for j in p.jobs} == {
        (a, tmp_path / "Converted" / "Disco" / "CD1" / "01.mp3"),
        (b, tmp_path / "Converted" / "Disco" / "CD2" / "01.mp3"),
    }
    assert p.ignored == [txt]


def test_plan_same_stem_prefers_flac(tmp_path):
    root = tmp_path / "X"
    m4a = _touch(root / "01.m4a")
    flac = _touch(root / "01.flac")
    p = conv.plan(root, tmp_path / "Converted")
    assert [j.src for j in p.jobs] == [flac]
    assert p.skipped == [(m4a, "duplicate of 01.flac")]


def test_plan_ignores_appledouble_files(tmp_path):
    root = tmp_path / "X"
    real = _touch(root / "01.flac")
    meta = _touch(root / "._01.flac")
    p = conv.plan(root, tmp_path / "Converted")
    assert [j.src for j in p.jobs] == [real]
    assert p.ignored == [meta]


def test_plan_case_insensitive_destinations(tmp_path):
    root = tmp_path / "X"
    flac = _touch(root / "Brano.flac")
    m4a = _touch(root / "brano.m4a")
    p = conv.plan(root, tmp_path / "Converted")
    assert [j.src for j in p.jobs] == [flac]
    assert p.skipped == [(m4a, "duplicate of Brano.flac")]


def test_plan_existing_mp3_skipped(tmp_path):
    root = tmp_path / "X"
    src = _touch(root / "a.wav")
    _touch(tmp_path / "Converted" / "X" / "a.mp3")
    p = conv.plan(root, tmp_path / "Converted")
    assert p.jobs == [] and p.skipped == [(src, "already converted")]


def test_plan_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        conv.plan(tmp_path / "nope", tmp_path / "Converted")


# --- generazione file di prova -------------------------------------------------------

def _make_audio(path: Path, ext: str, with_tags: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", CODECS[ext]]
    if with_tags and ext != ".aac":  # ADTS grezzo non ha contenitore per i tag
        for k, v in TAGS.items():
            cmd += ["-metadata", f"{k}={v}"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


@pytest.fixture(scope="module")
def cover_jpg(tmp_path_factory):
    path = tmp_path_factory.mktemp("img") / "cover.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "color=red:s=16x16", "-frames:v", "1", str(path)], check=True)
    return path.read_bytes()


def _embed_cover(path: Path, data: bytes) -> None:
    pic = Picture()
    pic.type, pic.mime, pic.data = 3, "image/jpeg", data
    ext = path.suffix
    if ext == ".flac":
        f = FLAC(path)
        f.add_picture(pic)
        f.save()
    elif ext == ".m4a":
        f = MP4(path)
        f["covr"] = [MP4Cover(data, imageformat=MP4Cover.FORMAT_JPEG)]
        f.save()
    elif ext in (".ogg", ".opus"):
        f = OggVorbis(path) if ext == ".ogg" else OggOpus(path)
        f["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]
        f.save()
    else:
        raise ValueError(ext)


# --- convert_one ----------------------------------------------------------------------

@needs_ffmpeg
@pytest.mark.parametrize("ext", list(CODECS))
def test_convert_one_formats(tmp_path, ext):
    src = _make_audio(tmp_path / f"in{ext}", ext)
    dst = tmp_path / "out" / "brano.mp3"
    progress = []
    conv.convert_one(src, dst, progress.append)

    mp3 = MP3(dst)
    # Senza header Xing mutagen stima il bitrate da durata e dimensione: tolleranza minima
    assert abs(mp3.info.bitrate - 320_000) < 1_000
    assert mp3.info.bitrate_mode in (BitrateMode.CBR, BitrateMode.UNKNOWN)
    assert progress and progress[-1] == 1.0
    assert not list(dst.parent.glob("*.part"))
    if ext != ".aac":
        tags = ID3(dst)
        assert str(tags["TIT2"]) == "Brano"
        assert str(tags["TPE1"]) == "Artista"
        assert str(tags["TALB"]) == "Album"
        assert str(tags["TRCK"]).split("/")[0] == "3"
        assert tags.version == (2, 3, 0)


@needs_ffmpeg
def test_convert_one_dash_filename(tmp_path, monkeypatch):
    src = _make_audio(tmp_path / "-strano.flac", ".flac")
    monkeypatch.chdir(tmp_path)
    dst = Path("-out.mp3")
    conv.convert_one(Path("-strano.flac"), dst)
    assert (tmp_path / "-out.mp3").exists()


@needs_ffmpeg
def test_convert_one_corrupt_raises_and_cleans(tmp_path):
    src = _touch(tmp_path / "rotto.flac", "non sono un flac")
    dst = tmp_path / "out" / "rotto.mp3"
    with pytest.raises(conv.ConversionError):
        conv.convert_one(src, dst)
    assert not dst.exists() and not list(dst.parent.glob("*.part"))


# --- copertina ------------------------------------------------------------------------

@needs_ffmpeg
@pytest.mark.parametrize("ext", [".flac", ".m4a", ".ogg", ".opus"])
def test_cover_copied(tmp_path, cover_jpg, ext):
    src = _make_audio(tmp_path / f"in{ext}", ext)
    _embed_cover(src, cover_jpg)
    dst = tmp_path / "out.mp3"
    conv.convert_one(src, dst)
    tags = ID3(dst)
    apics = tags.getall("APIC")
    assert len(apics) == 1 and apics[0].data == cover_jpg and apics[0].type == 3
    assert tags.version == (2, 3, 0)


@needs_ffmpeg
def test_no_cover_no_error(tmp_path):
    src = _make_audio(tmp_path / "in.flac", ".flac")
    conv.convert_one(src, tmp_path / "out.mp3")
    assert ID3(tmp_path / "out.mp3").getall("APIC") == []


# --- batch ----------------------------------------------------------------------------

@needs_ffmpeg
def test_batch_corrupt_file_does_not_stop_others(tmp_path):
    root = tmp_path / "X"
    _make_audio(root / "a.flac", ".flac")
    _touch(root / "b.flac", "rotto")
    _make_audio(root / "sub" / "c.wav", ".wav")
    _touch(root / "readme.txt")
    out = tmp_path / "Converted"

    events = []
    res = conv.run_batch(conv.plan(root, out), events.append)
    assert sorted(p.name for p in res.converted) == ["a.mp3", "c.mp3"]
    assert [p.name for p, _ in res.failed] == ["b.flac"]
    assert [p.name for p in res.ignored] == ["readme.txt"]
    assert {e.kind for e in events} >= {"start", "progress", "done", "failed"}
    assert (out / "X" / "sub" / "c.mp3").exists()

    # Secondo lancio: i convertiti risultano saltati, il corrotto riprova e fallisce
    res2 = conv.run_batch(conv.plan(root, out), lambda e: None)
    assert res2.converted == []
    assert sorted(p.name for p, why in res2.skipped if why == "already converted") == ["a.flac", "c.wav"]
    assert [p.name for p, _ in res2.failed] == ["b.flac"]


@needs_ffmpeg
def test_batch_interrupt_propagates_and_cleans(tmp_path, monkeypatch):
    root = tmp_path / "X"
    _make_audio(root / "a.flac", ".flac")
    p = conv.plan(root, tmp_path / "Converted")

    def on_event(e):
        if e.kind == "progress":
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        conv.run_batch(p, on_event)
    out_dir = tmp_path / "Converted" / "X"
    assert not list(out_dir.glob("*.part")) and not list(out_dir.glob("*.mp3"))


@needs_ffmpeg
def test_noisy_stderr_does_not_deadlock(tmp_path):
    """File parzialmente danneggiato: ffmpeg scrive centinaia di KB di errori su stderr.

    Se stderr non viene svuotato durante la conversione, la pipe si riempie e
    convert_one resta bloccato per sempre (review #1).
    """
    import threading

    good = tmp_path / "good.flac"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "sine=duration=600", "-c:a", "flac", str(good)], check=True)
    data = bytearray(good.read_bytes())
    for i in range(20_000, len(data), 997):
        data[i] ^= 0xFF
    broken = tmp_path / "broken.flac"
    broken.write_bytes(bytes(data))

    outcome = {}

    def work():
        try:
            conv.convert_one(broken, tmp_path / "out" / "broken.mp3")
            outcome["result"] = "converted"
        except conv.ConversionError as e:
            outcome["result"] = f"error: {e}"

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout=90)
    assert not t.is_alive(), "convert_one bloccato: stderr di ffmpeg non svuotato"
    assert "result" in outcome
