import pytest

from suiteav.core import i18n


def _no_locale():
    return (None, None)


@pytest.mark.parametrize("environ, expected", [
    ({"LANG": "it_IT.UTF-8"}, "it"),
    ({"LANG": "en_US.UTF-8"}, "en"),
    ({"LANG": "it"}, "it"),
    ({"LANG": "C"}, "en"),
    ({"LC_ALL": "en_GB.UTF-8", "LANG": "it_IT.UTF-8"}, "en"),
    ({"LANGUAGE": "it:en", "LANG": "en_US.UTF-8"}, "it"),
    ({"LC_MESSAGES": "it_CH.UTF-8"}, "it"),
    ({"LANG": "italian"}, "it"),
    ({"LANG": "id_ID.UTF-8"}, "en"),  # indonesiano: non deve passare come 'i...'
])
def test_auto_from_env(environ, expected):
    assert i18n.resolve_language("auto", environ, _no_locale) == expected


@pytest.mark.parametrize("loc, expected", [
    (("Italian_Italy", "1252"), "it"),  # Windows
    (("it_IT", "UTF-8"), "it"),
    (("English_United States", "1252"), "en"),
    ((None, None), "en"),
])
def test_auto_from_getlocale(loc, expected):
    assert i18n.resolve_language("auto", {}, lambda: loc) == expected


def test_explicit_setting_wins():
    assert i18n.resolve_language("en", {"LANG": "it_IT.UTF-8"}, _no_locale) == "en"
    assert i18n.resolve_language("it", {"LANG": "en_US.UTF-8"}, _no_locale) == "it"


def test_missing_catalog_falls_back(monkeypatch):
    monkeypatch.setattr(i18n.resources, "files",
                        lambda pkg: __import__("pathlib").Path("/nonexistent"))
    assert i18n.setup("it") == "it"
    assert i18n._("Quit") == "Quit"
