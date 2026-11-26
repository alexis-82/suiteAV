import sys
import tomllib
from pathlib import Path

import pytest

from suiteav.core import config


def test_first_run_creates_file_and_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config.platformdirs, "user_downloads_dir",
                        lambda: str(tmp_path / "home" / "Scaricati"))
    cfg = config.load(tmp_path / "cfg")

    assert (tmp_path / "cfg" / "config.toml").exists()
    assert cfg.language == "auto"
    assert cfg.download_dir == tmp_path / "home" / "Scaricati" / "suiteAV"
    # Il percorso scelto viene scritto nel file, visibile e modificabile dall'utente
    saved = tomllib.loads((tmp_path / "cfg" / "config.toml").read_text(encoding="utf-8"))
    assert saved["download_dir"] == str(cfg.download_dir)
    for sub in ("Audio", "Video", "Converted"):
        assert (cfg.download_dir / sub).is_dir()
    assert cfg.warnings == []


def test_existing_file_is_read(tmp_path):
    out = tmp_path / "out"
    config.write(tmp_path / "config.toml", str(out), "en")
    cfg = config.load(tmp_path)
    assert cfg.download_dir == out
    assert cfg.language == "en"
    assert cfg.audio_dir == out / "Audio"


def test_invalid_language_falls_back_with_warning(tmp_path):
    (tmp_path / "config.toml").write_text(
        f"download_dir = '{tmp_path / 'out'}'\nlanguage = 'fr'\n", encoding="utf-8")
    cfg = config.load(tmp_path)
    assert cfg.language == "auto"
    assert len(cfg.warnings) == 1
    message, params = cfg.warnings[0]
    assert params["value"] == "fr" and "fr" in message.format(**params)


def test_tilde_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    config.write(tmp_path / "cfg" / "config.toml", "~/musica", "it")
    cfg = config.load(tmp_path / "cfg")
    assert cfg.download_dir == tmp_path / "musica"


def test_windows_path_roundtrip(tmp_path):
    win_path = r"C:\Users\Prova\Downloads\suiteAV"
    path = tmp_path / "config.toml"
    config.write(path, win_path, "auto")
    with path.open("rb") as f:
        assert tomllib.load(f)["download_dir"] == win_path


def test_malformed_toml_raises(tmp_path):
    (tmp_path / "config.toml").write_text("download_dir = \n", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        config.load(tmp_path)


def test_literal_rejects_single_quote():
    with pytest.raises(ValueError):
        config._toml_literal("it's")


@pytest.mark.skipif(sys.platform != "linux", reason="user-dirs.dirs esiste solo su Linux")
def test_default_follows_xdg_user_dirs(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    (home / ".config" / "user-dirs.dirs").write_text('XDG_DOWNLOAD_DIR="$HOME/Scaricati"\n')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DOWNLOAD_DIR", raising=False)
    assert config.default_download_dir() == str(home / "Scaricati" / "suiteAV")


@pytest.mark.skipif(sys.platform != "linux", reason="user-dirs.dirs esiste solo su Linux")
def test_default_without_xdg_user_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DOWNLOAD_DIR", raising=False)
    assert config.default_download_dir() == str(tmp_path / "Downloads" / "suiteAV")
