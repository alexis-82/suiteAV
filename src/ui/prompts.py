"""Prompt interattivi (questionary) con 'indietro' uniforme.

Ogni funzione restituisce None quando l'utente torna indietro:
voce "Indietro", Esc oppure Ctrl+C.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any

import questionary
from prompt_toolkit.filters import IsDone, to_filter
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.layout import ConditionalContainer, FormattedTextControl, Window
from questionary import Separator, Style
from questionary.prompts.common import InquirerControl

from suiteav.core.i18n import _
from suiteav.ui.theme import console

_BACK = object()

STYLE = Style([
    ("qmark", "fg:ansired bold"),
    ("question", "bold"),
    ("pointer", "fg:ansicyan bold"),
    ("highlighted", "fg:ansicyan bold"),
    ("selected", "fg:ansigreen"),
    ("disabled", "fg:ansibrightblack italic"),
    ("answer", "fg:ansigreen bold"),
    ("instruction", "fg:ansibrightblack"),
    ("hint", "fg:ansibrightblack italic"),
])

# Attesa massima per distinguere Esc da una sequenza (frecce = ESC [ A).
# Il default di prompt_toolkit (0.5 s) rende Esc lento.
_ESC_TIMEOUT = 0.1


@dataclass
class Refresh:
    """Restituito da select() quando il menu si chiude per ridisegnare la schermata
    (es. è arrivato l'esito del check aggiornamenti). `pointed` è la voce evidenziata."""
    pointed: Any


@dataclass
class Item:
    label: str
    value: Any
    disabled: str | None = None  # motivo mostrato accanto alla voce


def _with_escape(question: questionary.Question) -> questionary.Question:
    kb = KeyBindings()

    @kb.add("escape", eager=True)
    def _(event):
        event.app.exit(result=_BACK)

    app = question.application
    app.key_bindings = merge_key_bindings([app.key_bindings, kb])
    app.ttimeoutlen = _ESC_TIMEOUT
    return question


def _control(question: questionary.Question) -> InquirerControl:
    return next(c for c in question.application.layout.find_all_controls()
                if isinstance(c, InquirerControl))


def _without_wrap(question: questionary.Question) -> questionary.Question:
    """Il cursore si ferma sulla prima/ultima voce invece di ricominciare dall'altro capo.

    questionary sposta il cursore con un modulo (wrap-around): i binding aggiunti
    qui, registrati dopo i suoi, hanno la precedenza sugli stessi tasti.
    """
    app = question.application
    control = _control(question)

    def selectable(index: int) -> bool:
        choice = control.filtered_choices[index]
        return not isinstance(choice, Separator) and not choice.disabled

    def move(step: int):
        def handler(event) -> None:
            i = control.pointed_at + step
            while 0 <= i < control.choice_count:
                if selectable(i):
                    control.pointed_at = i
                    return
                i += step
            # Nessuna voce selezionabile oltre: a fine corsa il cursore resta dov'è
        return handler

    kb = KeyBindings()
    for key in ("down", "j", "c-n"):
        kb.add(key, eager=True)(move(+1))
    for key in ("up", "k", "c-p"):
        kb.add(key, eager=True)(move(-1))
    app.key_bindings = merge_key_bindings([app.key_bindings, kb])
    return question


def _point_at(question: questionary.Question, value: Any) -> None:
    # Posizionamento diretto: il `default` di questionary colorerebbe la voce come scelta
    control = _control(question)
    for i, choice in enumerate(control.filtered_choices):
        if not isinstance(choice, Separator) and not choice.disabled and choice.value == value:
            control.pointed_at = i
            return


def _refresh_when_done(question: questionary.Question, futures: list[Future]) -> None:
    """Chiude il menu con Refresh quando tutti i future sono completati, per ridisegnare."""
    app = question.application
    control = _control(question)

    def setup() -> None:
        loop = asyncio.get_running_loop()

        def close() -> None:
            if app.is_running and not app.is_done and all(f.done() for f in futures):
                app.exit(result=Refresh(control.get_pointed_at().value))

        for f in futures:
            # Chiamato dal thread del check (o subito, se già completato)
            f.add_done_callback(lambda _f: loop.call_soon_threadsafe(close))

    app.pre_run_callables.append(setup)


def _with_key_hint(question: questionary.Question) -> questionary.Question:
    """Indicazione dei tasti sotto la lista, dopo due righe vuote, grigia e in corsivo.

    È un riquadro a sé nel layout (non un Separator di questionary): lo stile dei
    separatori varrebbe anche per le intestazioni di gruppo dei menu.
    """
    hint = Window(FormattedTextControl([
        ("", "\n\n"),
        ("class:hint", "   " + _("(arrows + Enter, Esc = back)")),
    ]), dont_extend_height=True)
    # children[1] è la lista delle voci: il riquadro va subito sotto, visibile come lei
    # solo finché il menu è aperto
    layout = question.application.layout
    layout.container.children.insert(2, ConditionalContainer(hint, filter=~IsDone()))
    # Quando conosce la posizione del cursore (CPR su Linux, API della console su
    # Windows) prompt_toolkit riempie il menu fino in fondo alla finestra: lo spazio
    # in più andava alla lista, che spingeva l'indicazione sull'ultima riga.
    for window in layout.find_all_windows():
        if isinstance(window.content, InquirerControl):
            window.dont_extend_height = to_filter(True)
    return question


def _disabled_aligned(question: questionary.Question) -> questionary.Question:
    """Toglie il "- " che questionary mette davanti alle voci disabilitate,
    così restano in colonna con le altre (il grigio basta a distinguerle)."""
    control = _control(question)
    original = control.text  # InquirerControl passa i suoi token come callable

    def tokens():
        return [(style, text[2:]) if style == "class:disabled" and text.startswith("- ")
                else (style, text) for style, text in original()]

    control.text = tokens
    return question


def _ask(question: questionary.Question) -> Any:
    try:
        result = _with_escape(question).unsafe_ask()
    except KeyboardInterrupt:
        return None
    return None if result is _BACK else result


def select(message: str, items: list[Item | str], back_label: str | None = None,
           pointed: Any = None, refresh_on: list[Future] | None = None) -> Any:
    """Le stringhe in `items` diventano intestazioni di gruppo non selezionabili.

    pointed: valore della voce su cui posizionare il cursore.
    refresh_on: se tutti completano mentre il menu è aperto, restituisce Refresh.
    """
    choices = [questionary.Separator(f"── {i}") if isinstance(i, str)
               else questionary.Choice(i.label, value=i.value, disabled=i.disabled)
               for i in items]
    choices.append(questionary.Separator(" "))
    choices.append(questionary.Choice(back_label or _("Back"), value=_BACK))
    question = _disabled_aligned(_with_key_hint(_without_wrap(questionary.select(
        message, choices=choices, style=STYLE, qmark="»",
        # Non vuota, altrimenti questionary aggiunge il suo "(Use arrow keys)";
        # l'indicazione dei tasti è sotto la lista (_with_key_hint)
        instruction=" ",
    ))))
    if pointed is not None:
        _point_at(question, pointed)
    if refresh_on:
        _refresh_when_done(question, refresh_on)
    return _ask(question)


def text(message: str, default: str = "") -> str | None:
    result = _ask(questionary.text(message, default=default, style=STYLE, qmark="»"))
    if result is None:
        return None
    result = result.strip()
    return result or None


def path(message: str, only_directories: bool = False) -> str | None:
    result = _ask(questionary.path(message, only_directories=only_directories,
                                   style=STYLE, qmark="»"))
    if result is None:
        return None
    # Il terminale/file manager a volte aggiunge virgolette quando si trascina un file
    result = result.strip().strip('"').strip("'")
    return result or None


def confirm(message: str, default: bool = True) -> bool:
    result = _ask(questionary.confirm(message, default=default, style=STYLE, qmark="»"))
    return bool(result)


def pause() -> None:
    console.print()
    try:
        console.input(f"[muted]{_('Press Enter to continue')}[/]")
    except (KeyboardInterrupt, EOFError):
        pass
