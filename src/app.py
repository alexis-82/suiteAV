"""Loop del menu principale e stato condiviso tra le schermate."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Callable

from suiteav.core import deps as deps_mod
from suiteav.core import platform as plat
from suiteav.core import updater
from suiteav.core.config import Config
from suiteav.core.i18n import _
from suiteav.core.updater import UpdateInfo
from suiteav.ui import prompts
from suiteav.ui.banner import show_header
from suiteav.ui.theme import clear_all, console

# Secondi di attesa dei check aggiornamenti prima del primo disegno (timeout di rete: 3 s)
STARTUP_CHECK_WAIT = 2.0


@dataclass
class AppContext:
    config: Config
    deps: deps_mod.DepsStatus
    _suiteav_update: Future | None = field(default=None, repr=False)
    _yt_dlp_update: Future | None = field(default=None, repr=False)

    @staticmethod
    def _result(future: Future | None) -> UpdateInfo | None:
        # None finché il check di rete non ha risposto: la testata mostra "checking…"
        if future is None or not future.done():
            return None
        if future.exception() is not None:
            # Un errore inatteso nel check di rete non deve rompere ogni schermata
            return None
        return future.result()

    @property
    def suiteav_update(self) -> UpdateInfo | None:
        return self._result(self._suiteav_update)

    @property
    def yt_dlp_update(self) -> UpdateInfo | None:
        return self._result(self._yt_dlp_update)

    def refresh_deps(self) -> None:
        self.deps = deps_mod.check()

    def screen(self, title: str) -> None:
        """Pulisce schermo e scrollback e mostra testata + titolo della schermata.

        Anche lo scrollback: in Windows Terminal "pulisci schermo" sposta il contenuto
        sopra la finestra, e le schermate precedenti resterebbero visibili scorrendo.
        """
        clear_all()
        show_header(self.deps, self.suiteav_update, self.yt_dlp_update)
        console.rule(f"[title]{title}[/]")
        console.print()


def require_ffmpeg(ctx: AppContext, reason: str, for_conversion: bool = False) -> bool:
    """Rilegge lo stato di ffmpeg (può essere stato installato a programma aperto);
    se manca, avvisa con il comando di installazione e restituisce False.

    for_conversion=True richiede anche ffprobe e l'encoder libmp3lame.
    """
    ctx.refresh_deps()
    d = ctx.deps
    if d.can_convert if for_conversion else d.ffmpeg.found:
        return True
    if for_conversion and d.ffmpeg.found and d.ffprobe.found:
        console.print(f"[err] {_('MP3 encoder missing')} [/] "
                      f"{_('this ffmpeg build has no libmp3lame.')}")
    else:
        console.print(f"[err] {_('ffmpeg is missing')} [/] {reason}")
    console.print(f"{_('Install it with')}: [hint]{plat.ffmpeg_install_hint()}[/]")
    prompts.pause()
    return False


def not_available(ctx: AppContext) -> None:
    ctx.screen(_("Not available yet"))
    console.print(_("This feature is not available yet."))
    prompts.pause()


def open_downloads(ctx: AppContext) -> None:
    try:
        plat.open_folder(ctx.config.download_dir)
    except OSError as e:
        ctx.screen(_("Downloads"))
        console.print(f"[err] {_('ERROR')} [/] {_('Cannot open the folder')}: {e}")
        console.print(str(ctx.config.download_dir))
        prompts.pause()


def _main_items() -> list[tuple[prompts.Item, Callable[[AppContext], None] | None]]:
    # Import locali: le schermate importano yt_dlp, che è lento da caricare
    from suiteav.screens import convert, updates, youtube
    from suiteav.screens import deps as deps_screen

    return [
        (prompts.Item(_("YouTube / SoundCloud"), "youtube"), youtube.run),
        (prompts.Item(_("Audio conversion (to MP3)"), "convert_audio"), convert.run),
        (prompts.Item(_("Video conversion"), "convert_video", disabled=_("not available yet")), None),
        (prompts.Item(_("Open downloads folder"), "downloads"), open_downloads),
        (prompts.Item(_("Updates"), "updates"), updates.run),
        (prompts.Item(_("Dependencies"), "deps"), deps_screen.run),
    ]


def run(config: Config) -> None:
    plat.ensure_console_rows()  # console di Windows 10: 30 righe non bastano al menu YouTube
    clear_all()  # subito, prima dei check: niente testo precedente mentre l'app parte
    with ThreadPoolExecutor(max_workers=2) as pool:
        deps = deps_mod.check()
        ctx = AppContext(
            config=config,
            deps=deps,
            _suiteav_update=pool.submit(updater.check_suiteav),
            _yt_dlp_update=pool.submit(updater.check_yt_dlp, deps.yt_dlp_version),
        )
        # Si aspettano i check per un attimo, così il menu si disegna una volta sola con
        # l'esito; solo con una rete lenta si ricade nel ridisegno con Refresh.
        with console.status(_("Checking for updates…")):
            wait([ctx._suiteav_update, ctx._yt_dlp_update], timeout=STARTUP_CHECK_WAIT)
        entries = _main_items()
        handlers = {item.value: handler for item, handler in entries}

        pointed = None
        while True:
            # Finché i check di rete sono in corso la testata dice "checking…": quando
            # arrivano, il menu si chiude con Refresh e la schermata viene ridisegnata.
            # I check in corso si leggono PRIMA di disegnare la testata: se un check
            # finisse tra il disegno e questa lettura, la testata resterebbe "checking…".
            pending = [f for f in (ctx._suiteav_update, ctx._yt_dlp_update)
                       if f is not None and not f.done()]
            ctx.screen(_("Main menu"))
            for message, params in config.warnings:
                console.print("[warn] config [/]", _(message).format(**params))
            choice = prompts.select(_("What do you want to do?"),
                                    [item for item, _h in entries], back_label=_("Quit"),
                                    pointed=pointed, refresh_on=pending)
            if isinstance(choice, prompts.Refresh):
                pointed = choice.pointed
                continue
            pointed = None
            if choice is None:
                break
            handler = handlers.get(choice) or not_available
            try:
                handler(ctx)
            except KeyboardInterrupt:
                # Ctrl+C in un punto senza gestione propria (es. attese di rete): torna al menu
                pass

        console.clear()
