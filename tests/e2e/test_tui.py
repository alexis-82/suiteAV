"""Criteri di accettazione verificati guidando la TUI reale in un pseudo-terminale.

Ambiente isolato: HOME, config e cache in tmp_path; rete verso GitHub/PyPI
bloccata da un proxy inesistente (testata = N/A, nessuna dipendenza dalla rete);
D-Bus non raggiungibile, quindi nessuna notifica reale durante i test.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pexpect = pytest.importorskip("pexpect")  # non disponibile su Windows

pytestmark = pytest.mark.e2e

DOWN, ESC = "\x1b[B", "\x1b"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg/ffprobe non disponibili")

# Voci selezionabili del menu principale, nell'ordine (la voce disabilitata
# "Video conversion" sta tra la 2ª e la 3ª e le frecce la saltano)
MAIN = ["YouTube / SoundCloud", "Audio conversion (to MP3)",
        "Open downloads folder", "Updates", "Dependencies", "Quit"]


def strip(text: str) -> str:
    return ANSI.sub("", text)


def _latest_header_checking(screen: str) -> bool:
    """True se l'ultima riga di stato di suiteAV disegnata dice ancora 'checking…'."""
    rows = [line for line in screen.splitlines()
            if "suiteAV " in line and "•" not in line and "Coded by" not in line]
    return bool(rows) and ("checking…" in rows[-1] or "verifica…" in rows[-1])


class Tui:
    def __init__(self, tmp: Path, lang: str = "en_US.UTF-8", config_lang: str = "auto",
                 path: str | None = None, shell_wrap: bool = False, proxy: str | None = None,
                 rows: int = 50):
        self.home = tmp / "home"
        self.cwd = tmp / "cwd"
        self.cwd.mkdir(parents=True, exist_ok=True)
        cfg = tmp / "xdg_config" / "suiteav"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "config.toml").write_text(
            f"download_dir = '{self.home / 'Downloads' / 'suiteAV'}'\nlanguage = '{config_lang}'\n",
            encoding="utf-8")
        env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(tmp / "xdg_config"),
            "XDG_CACHE_HOME": str(tmp / "xdg_cache"),
            "LANG": lang, "LC_ALL": "", "LC_MESSAGES": "", "LANGUAGE": "",
            "https_proxy": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
            # pexpect non risponde alla richiesta di posizione del cursore (CPR): dopo un
            # timeout prompt_toolkit stampa un avviso e ridisegna il menu da solo.
            # Un terminale vero risponde, quindi negli e2e la richiesta va disattivata.
            "PROMPT_TOOLKIT_NO_CPR": "1",
        }
        if path is not None:
            env["PATH"] = path
        if proxy is not None:
            env["https_proxy"] = env["HTTPS_PROXY"] = proxy
        cmd = f"{sys.executable} -m suiteav"
        if shell_wrap:
            # Una shell che sopravvive all'uscita del programma: il terminale non viene chiuso
            self.p = pexpect.spawn("/bin/sh", ["-c", f"{cmd}; echo SHELL_STILL_ALIVE"],
                                   cwd=str(self.cwd), env=env, encoding="utf-8",
                                   codec_errors="replace", timeout=30, dimensions=(rows, 130))
        else:
            self.p = pexpect.spawn(sys.executable, ["-m", "suiteav"], cwd=str(self.cwd), env=env,
                                   encoding="utf-8", codec_errors="replace", timeout=30,
                                   dimensions=(rows, 130))

    @property
    def downloads(self) -> Path:
        return self.home / "Downloads" / "suiteAV"

    HINT = r"\((arrows|frecce) \+ (Enter|Invio), Esc = (back|indietro)\)"

    def wait_menu(self, last: str = "Quit|Back|Esci|Indietro", settle: bool = True) -> str:
        """Attende un menu completamente disegnato; restituisce il testo visto.

        L'indicazione dei tasti è l'ultima riga del menu, sotto `last` (Esci/Indietro).
        settle=True: se la testata dice ancora "checking…", attende il ridisegno
        automatico che arriva con l'esito dei check. Un Esc premuto proprio durante
        quel ridisegno può andare perso, e renderebbe i test instabili.
        """
        # Una schermata è pronta quando, dopo l'ultimo banner disegnato, ci sono
        # l'indicazione dei tasti e la voce finale (e la testata stabile, se settle).
        # Non basta la prima indicazione che arriva: prompt_toolkit la ristampa anche
        # quando ridisegna il menu per una freccia o per conto suo.
        text = ""
        while True:
            self.p.expect(self.HINT, timeout=15)
            text += strip(self.p.before + self.p.after)
            banner_at = text.rfind("███")
            if banner_at == -1:
                continue
            screen = text[text.rfind("\n", 0, banner_at) + 1:]
            if not re.search(last, screen):
                continue
            if settle and _latest_header_checking(screen):
                continue
            time.sleep(0.3)
            return screen

    def choose(self, index: int) -> None:
        for _ in range(index):
            self.p.send(DOWN)
            time.sleep(0.05)
        self.p.send("\r")

    def expect_text(self, pattern: str, timeout: int = 30) -> str:
        self.p.expect(pattern, timeout=timeout)
        return strip(self.p.before)

    def close(self) -> None:
        if self.p.isalive():
            self.p.terminate(force=True)


@pytest.fixture
def tui(tmp_path):
    created = []

    def factory(**kwargs) -> Tui:
        t = Tui(tmp_path, **kwargs)
        created.append(t)
        return t

    yield factory
    for t in created:
        t.close()


def _audio(path: Path, codec: str = "flac", seconds: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"sine=duration={seconds}", "-c:a", codec, str(path)], check=True)
    return path


# --- menu, uscita, lingua ---------------------------------------------------------------

def test_quit_leaves_terminal_open(tui):
    t = tui(shell_wrap=True)
    t.wait_menu()
    t.choose(MAIN.index("Quit"))
    t.p.expect("SHELL_STILL_ALIVE")
    t.p.expect(pexpect.EOF)


def test_esc_and_ctrl_c_on_main_menu_exit_cleanly(tui):
    for key in (ESC, "\x03"):
        t = tui()
        t.wait_menu()
        t.p.send(key)
        t.p.expect(pexpect.EOF)
        t.p.close()
        assert t.p.exitstatus == 0


def test_video_conversion_visible_but_disabled(tui):
    t = tui()
    screen = t.wait_menu()
    assert "Video conversion (not available yet)" in screen
    # In colonna con le altre voci, senza il "- " di questionary
    assert "- Video conversion" not in screen
    lines = screen.splitlines()
    audio = next(ln for ln in reversed(lines) if "Audio conversion" in ln)
    video = next(ln for ln in reversed(lines) if "Video conversion" in ln)
    assert audio.index("Audio conversion") == video.index("Video conversion")
    # Due frecce giù dalla prima voce: la voce disabilitata viene saltata.
    # Non si preme Invio (aprirebbe il file manager): si legge la voce evidenziata.
    t.p.send(DOWN)
    time.sleep(0.1)
    t.p.send(DOWN)
    # Il ridisegno può arrivare a pezzi (runner lenti): si legge finché la voce
    # evidenziata è "Open downloads folder", al massimo 5 s. La riga della domanda
    # ("» What do you want to do?") ha anch'essa "»" e va esclusa.
    redraw, pointed = "", []
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            redraw += strip(t.p.read_nonblocking(100_000, timeout=0.5))
        except pexpect.TIMEOUT:
            pass
        pointed = [line for line in redraw.splitlines()
                   if "»" in line and "What do you want" not in line]
        if pointed and "Open downloads folder" in pointed[-1]:
            break
    assert pointed and "Open downloads folder" in pointed[-1]
    t.p.send(ESC)
    t.p.expect(pexpect.EOF)


@pytest.mark.parametrize("lang, config_lang, expected, unexpected", [
    ("it_IT.UTF-8", "auto", "Conversione audio (in MP3)", "Audio conversion"),
    ("en_US.UTF-8", "auto", "Audio conversion (to MP3)", "Conversione audio"),
    ("it_IT.UTF-8", "en", "Audio conversion (to MP3)", "Conversione audio"),
])
def test_language(tui, lang, config_lang, expected, unexpected):
    t = tui(lang=lang, config_lang=config_lang)
    screen = t.wait_menu()
    assert expected in screen and unexpected not in screen


def test_youtube_menu_has_every_v33_entry(tui):
    t = tui()
    t.wait_menu()
    t.choose(MAIN.index("YouTube / SoundCloud"))
    screen = t.wait_menu("Back")
    entries = ["Which resolutions are available?", "Download choosing the format manually",
               "Download up to 360p", "Download up to 480p", "Download up to 720p",
               "Download best quality", "Download best MP4",
               "Download best quality, split by chapters", "Download best quality with metadata",
               "Download MP3 HQ", "Download album to MP3 HQ, split by chapters",
               "Download MP3 from a file of links", "Playlist from a file of links"]
    missing = [e for e in entries if e not in screen]
    assert missing == []
    # Sottomenu playlist: 4 varianti della v3.3
    t.choose(12)  # ultima voce selezionabile prima di "Back"
    screen = t.wait_menu("Back")
    for e in ("Playlist with metadata", "Playlist split by chapters",
              "Playlist with numbering", "Playlist"):
        assert e in screen


def test_url_file_missing_is_readable(tui, tmp_path):
    t = tui()
    t.wait_menu()
    t.choose(MAIN.index("YouTube / SoundCloud"))
    t.wait_menu("Back")
    if not shutil.which("ffmpeg"):
        pytest.skip("le voci di download richiedono ffmpeg")
    t.choose(11)  # MP3 da file di link
    t.expect_text("File with the links")
    t.p.send(str(tmp_path / "non_esiste.txt") + "\r")
    out = t.expect_text("Press Enter")
    assert "Cannot read the file" in out and "Traceback" not in out


# --- conversione dalla TUI ----------------------------------------------------------

def _start_conversion(t: Tui, source: Path) -> str:
    t.wait_menu()
    t.choose(MAIN.index("Audio conversion (to MP3)"))
    t.expect_text("File or folder to convert")
    t.p.send(f"{source}\r")
    return t.expect_text(r"Start the conversion\?|Press Enter")


@needs_ffmpeg
def test_conversion_end_to_end_with_rerun(tui, tmp_path):
    src = tmp_path / "Album"
    _audio(src / "CD1" / "01.flac")
    _audio(src / "CD2" / "01.m4a", "aac")
    (src / "CD2" / "rotto.ogg").write_text("non sono audio")
    (src / "note.txt").write_text("x")

    t = tui()
    preview = _start_conversion(t, src)
    assert "To convert: 3" in preview and "ignored: 1" in preview
    t.p.send("\r")
    out = t.expect_text("Press Enter")
    assert re.search(r"Converted\s+2", out)
    assert re.search(r"Errors\s+1", out) and "rotto.ogg" in out
    assert "note.txt" in out and "Traceback" not in out
    converted = t.downloads / "Converted" / "Album"
    assert (converted / "CD1" / "01.mp3").is_file() and (converted / "CD2" / "01.mp3").is_file()

    # Seconda esecuzione: i due convertiti risultano saltati
    t.p.send("\r")
    preview = _start_conversion(t, src)
    assert "To convert: 1" in preview and "skipped: 2" in preview  # resta solo il corrotto


@needs_ffmpeg
def test_single_file_conversion(tui, tmp_path):
    src = _audio(tmp_path / "musica" / "brano.flac")
    t = tui()
    _start_conversion(t, src)
    t.p.send("\r")
    t.expect_text("Press Enter")
    assert (t.downloads / "Converted" / "brano.mp3").is_file()


@needs_ffmpeg
def test_ctrl_c_during_conversion_returns_to_menu_without_partials(tui, tmp_path):
    src = tmp_path / "lunghi"
    for i in range(2):
        _audio(src / f"t{i}.flac", seconds=300)
    t = tui()
    _start_conversion(t, src)
    t.p.send("\r")
    t.expect_text("Total")
    time.sleep(1)
    t.p.sendintr()
    out = t.expect_text("Press Enter")
    assert "Operation interrupted" in out and "Traceback" not in out
    t.p.send("\r")
    t.wait_menu()  # di nuovo al menu principale
    # Su una macchina veloce il primo file può finire prima del Ctrl+C: è una
    # conversione completa, non un residuo. Il file interrotto non deve lasciare nulla.
    files = [p for p in (t.downloads / "Converted").rglob("*") if p.is_file()]
    assert [p for p in files if p.suffix == ".part"] == []
    assert len(files) < 2


def test_no_work_files_in_cwd(tui, tmp_path):
    t = tui()
    t.wait_menu()
    t.choose(MAIN.index("Dependencies"))
    t.expect_text("Press Enter")
    t.p.send("\r")
    t.wait_menu()
    t.choose(MAIN.index("Updates"))
    t.expect_text("Press Enter")
    t.p.send("\r")
    t.wait_menu()
    t.choose(MAIN.index("Quit"))
    t.p.expect(pexpect.EOF)
    assert list(t.cwd.iterdir()) == []


# --- ffmpeg assente -------------------------------------------------------------------

def test_without_ffmpeg_header_and_conversion_warn(tui):
    t = tui(path=str(Path("/nonexistent")))
    screen = t.wait_menu()
    headers = [line for line in screen.splitlines() if "ffmpeg" in line]
    assert headers, f"testata non trovata nello schermo:\n{screen[-1500:]!r}"
    assert "MISSING" in headers[0]
    t.choose(MAIN.index("Audio conversion (to MP3)"))
    out = t.expect_text("Press Enter")
    assert "ffmpeg is missing" in out
    assert "Install it with" in out
    assert "File or folder" not in out  # la conversione non parte


def test_without_ffmpeg_download_warns_before_asking_link(tui):
    t = tui(path=str(Path("/nonexistent")))
    t.wait_menu()
    t.choose(MAIN.index("YouTube / SoundCloud"))
    t.wait_menu("Back")
    t.choose(5)  # migliore qualità
    out = t.expect_text("Press Enter")
    assert "ffmpeg is missing" in out and "Paste the link" not in out


def _fake_proxy(close_after: float | None):
    """Proxy HTTP che accetta le connessioni e non risponde: le tiene aperte (i check
    versioni restano in attesa fino al timeout, 3 s) o le chiude dopo close_after
    secondi (i check falliscono a quel punto). start() va chiamato dopo lo spawn
    della TUI, perché forkpty in un processo multi-thread è sconsigliato."""
    import socket
    import threading

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    server.settimeout(0.2)
    conns, timers, stop = [], [], threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, addr = server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            conns.append(conn)
            if close_after is not None:
                timer = threading.Timer(close_after, conn.close)
                timers.append(timer)
                timer.start()

    acceptor = threading.Thread(target=serve, daemon=True)

    class Proxy:
        url = f"http://127.0.0.1:{server.getsockname()[1]}"
        start = acceptor.start

    yield Proxy
    # I thread devono terminare qui: i test successivi creano altri pseudo-terminali
    stop.set()
    if acceptor.is_alive():
        acceptor.join(timeout=2)
    for timer in timers:
        timer.cancel()
        timer.join(timeout=2)
    for conn in conns:
        conn.close()
    server.close()


@pytest.fixture
def hanging_proxy():
    yield from _fake_proxy(close_after=None)


@pytest.fixture
def slow_proxy():
    """Check che falliscono dopo 1 s: più lenti del primo disegno, entro l'attesa iniziale."""
    yield from _fake_proxy(close_after=1.0)


def test_ctrl_c_while_waiting_returns_to_main_menu(tui, hanging_proxy):
    """Ctrl+C durante un'attesa di rete (fuori dai prompt) torna al menu, non chiude."""
    t = tui(proxy=hanging_proxy.url)
    hanging_proxy.start()
    t.wait_menu(settle=False)  # Updates va aperto mentre il check è ancora in attesa
    t.choose(MAIN.index("Updates"))
    t.expect_text("Checking the latest versions")
    t.p.sendintr()
    t.wait_menu()  # di nuovo al menu principale
    assert t.p.isalive()


def test_header_updates_without_keypress(tui, hanging_proxy):
    """La testata passa da 'checking…' all'esito senza cambiare schermata,
    e il cursore resta sulla voce evidenziata."""
    t = tui(proxy=hanging_proxy.url)
    hanging_proxy.start()
    screen = t.wait_menu(settle=False)
    assert "checking…" in screen
    t.p.send(DOWN)
    time.sleep(0.1)
    t.p.send(DOWN)  # su "Open downloads folder" (la voce disabilitata viene saltata)
    # Nessun altro tasto: entro il timeout dei check (3 s) la schermata si ridisegna
    redrawn = t.wait_menu()  # settle: attende la testata con l'esito
    assert "N/A" in redrawn and "checking…" not in redrawn
    pointed = [line for line in redrawn.splitlines() if "»" in line and "Esc" not in line]
    assert pointed and "Open downloads folder" in pointed[-1]
    t.p.send(ESC)
    t.p.expect(pexpect.EOF)


def test_arrows_stop_at_the_ends(tui):
    """Niente wrap-around: Su dalla prima voce resta sulla prima, Giù oltre l'ultima resta sull'ultima."""
    t = tui()
    t.wait_menu()
    t.p.send("\x1b[A")  # Su sulla prima voce: con il wrap andrebbe su "Quit"
    time.sleep(0.2)
    t.p.send("\r")
    t.wait_menu("Back")  # siamo entrati in YouTube / SoundCloud, il programma non è uscito
    assert t.p.isalive()
    t.p.send(ESC)
    t.wait_menu()
    for _ in range(len(MAIN) + 3):  # oltre la fine: con il wrap ripartirebbe da "YouTube"
        t.p.send(DOWN)
        time.sleep(0.05)
    time.sleep(0.2)
    t.p.send("\r")  # l'ultima voce è "Quit"
    t.p.expect(pexpect.EOF)


def test_startup_clears_screen_and_scrollback(tui):
    """All'avvio: schermo (ESC[2J) e scrollback (ESC[3J) puliti prima del primo disegno."""
    t = tui()
    t.p.expect(r"\(arrows \+ Enter, Esc = back\)")
    raw = t.p.before
    first_draw = raw.find("███")
    assert first_draw != -1
    assert "\x1b[2J" in raw[:first_draw] and "\x1b[3J" in raw[:first_draw]


def test_key_hint_below_last_entry(tui):
    """Indicazione dei tasti sotto 'Quit', separata da due righe vuote, non sulla riga della domanda."""
    t = tui()
    screen = t.wait_menu()
    lines = [line.rstrip() for line in screen.replace("\r", "").split("\n")]
    question = next(line for line in lines if "What do you want to do?" in line)
    assert "Esc" not in question
    quit_at = max(i for i, line in enumerate(lines) if line.strip() == "Quit")
    hint_at = max(i for i, line in enumerate(lines) if "(arrows + Enter, Esc = back)" in line)
    assert hint_at > quit_at
    assert [line.strip() for line in lines[quit_at + 1:hint_at]] == ["", ""]


def test_key_hint_is_grey_italic(tui):
    """L'indicazione dei tasti è grigia (SGR 90) e in corsivo (SGR 3); le intestazioni no."""
    t = tui()
    t.p.expect(r"\x1b\[([0-9;]*)m {3}\(arrows \+ Enter, Esc = back\)")
    sgr = t.p.match.group(1).split(";")
    assert "90" in sgr and "3" in sgr


def test_short_terminal_uses_compact_banner(tui):
    """Windows Terminal apre 30 righe e non si lascia ridimensionare: banner su una riga,
    così il menu più lungo (YouTube) resta tutto visibile insieme a titolo e testata."""
    t = tui(rows=30)
    t.p.expect(Tui.HINT)
    t.p.send("\r")  # prima voce: YouTube / SoundCloud
    t.p.expect("── Video")  # c'è solo nel menu YouTube
    out = strip(t.p.before)
    assert "███" not in out
    assert re.search(r"suiteAV \d+\.\d+\.\d+ • YouTube / SoundCloud downloader", out)
    t.p.send(ESC)


def test_36_rows_keep_big_banner(tui):
    """36 righe bastano al menu più lungo col banner grande: niente versione compatta."""
    t = tui(rows=36)
    t.p.expect(Tui.HINT)
    t.p.send("\r")  # prima voce: YouTube / SoundCloud
    t.p.expect("── Video")  # c'è solo nel menu YouTube
    assert "███" in strip(t.p.before)
    t.p.send(ESC)


def test_startup_draws_menu_once(tui, slow_proxy):
    """Check di rete che rispondono dopo 1 s: il menu aspetta e si disegna una volta sola.
    In Windows Terminal un secondo disegno lascerebbe il primo visibile nello storico."""
    t = tui(proxy=slow_proxy.url)
    slow_proxy.start()
    t.p.expect(Tui.HINT)
    raw = t.p.before
    deadline = time.monotonic() + 3  # un eventuale ridisegno arriverebbe in questo intervallo
    while time.monotonic() < deadline:
        try:
            raw += t.p.read_nonblocking(100_000, timeout=0.5)
        except pexpect.TIMEOUT:
            pass
    assert strip(raw).count("Coded by Alexis") == 1
    # Cambio schermata: pulisce anche lo scrollback
    t.p.send("\r")
    t.p.expect("── Video")
    assert "\x1b[3J" in t.p.before
    t.p.send(ESC)


def test_key_hint_stays_below_list_when_terminal_reports_cursor():
    """Un terminale vero risponde alla richiesta di posizione del cursore (CPR; su
    Windows prompt_toolkit la legge dall'API della console) e prompt_toolkit riempie il
    menu fino al fondo della finestra: l'indicazione deve restare sotto la lista, non
    finire sull'ultima riga spingendo in alto il banner."""
    pyte = pytest.importorskip("pyte")
    rows, cols = 40, 120
    env = {**os.environ, "LANG": "en_US.UTF-8", "LANGUAGE": "", "LC_ALL": "",
           "https_proxy": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
           "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent", "TERM": "xterm-256color"}
    env.pop("PROMPT_TOOLKIT_NO_CPR", None)
    screen = pyte.Screen(cols, rows)
    stream = pyte.ByteStream(screen)
    p = pexpect.spawn(sys.executable, ["-m", "suiteav"], env=env, dimensions=(rows, cols),
                      timeout=30)
    screen.write_process_input = p.send  # risponde alla CPR come un terminale vero
    try:
        def pump(seconds: float) -> list[str]:
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                try:
                    stream.feed(p.read_nonblocking(100_000, timeout=0.3))
                except pexpect.TIMEOUT:
                    pass
            return [line.rstrip() for line in screen.display]

        lines = pump(0)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not any("Quit" in ln for ln in lines):
            lines = pump(0.3)
        # Il menu viene ridisegnato quando arriva la risposta CPR: si misura dopo
        lines = pump(1.5)
        quit_row = next(i for i, line in enumerate(lines) if line.strip() == "Quit")
        hint_row = next(i for i, line in enumerate(lines) if "Esc = back" in line)
        assert hint_row == quit_row + 3  # due righe vuote, poi l'indicazione
        assert hint_row < rows - 1      # non sull'ultima riga
    finally:
        p.terminate(force=True)
