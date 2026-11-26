"""Spazio occupato dai menu quando prompt_toolkit conosce la posizione del cursore."""
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from suiteav.ui import prompts


class WindowsLikeOutput(DummyOutput):
    """Come la console di Windows: risponde subito con le righe sotto il cursore."""

    def get_rows_below_cursor_position(self) -> int:
        return 30


def test_menu_does_not_reserve_rows_below_cursor():
    seen = {}
    with create_pipe_input() as inp, create_app_session(input=inp, output=WindowsLikeOutput()):
        original = prompts._with_escape

        def spy(question):
            app = question.application

            def measure(_):
                if app.renderer._last_screen is not None:
                    seen["height"] = max(seen.get("height", 0), app.renderer._last_screen.height)

            app.after_render += measure
            return original(question)

        prompts._with_escape = spy
        try:
            inp.send_text("\r")
            assert prompts.select("Pick", [prompts.Item("A", "a"), prompts.Item("B", "b")]) == "a"
        finally:
            prompts._with_escape = original
    # Lista, due righe vuote e indicazione: niente righe vuote fino in fondo alla finestra
    assert seen["height"] < 30
