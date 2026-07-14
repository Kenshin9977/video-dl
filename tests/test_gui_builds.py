"""Build the real window, with the real Flet, and no display.

Every other test in this suite replaces flet with a MagicMock, which means a Flet
release can rename half its API and the suite stays green. That is not theoretical:
flet 0.85 removed `ft.padding.only`, the app died at startup on a red error screen,
and 463 tests passed anyway. So did `--selftest`, because importing flet still works.
Only opening the window showed it.

This constructs the whole control tree against the installed Flet, with a stand-in
for Page. It needs no display and takes milliseconds, and it fails on exactly that
kind of break.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Other test modules put MagicMocks in sys.modules in place of flet. Dropping those is
# not enough: gui.app may already have been imported while flet was a mock, and its
# module level `import flet as ft` stays bound to it. Drop gui.* too, so it is imported
# again, against the real Flet.
for _name in [
    name
    for name in list(sys.modules)
    if name.startswith(("flet", "gui")) or name in {"darkdetect", "sys_vars", "i18n", "i18n.lang"}
]:
    del sys.modules[_name]

import flet as ft  # noqa: E402

from gui.app import VideodlApp  # noqa: E402


@pytest.fixture
def page():
    """A stand-in for Page: the app talks to it, nothing is drawn.

    Not `spec=ft.Page`. The app reaches for things a Page only grows once a window
    exists behind it. What keeps this test honest is not the fake page, it is that
    every control the app builds is a real Flet control, asserted below.
    """
    page = MagicMock()
    page.services = []
    page.overlay = []
    page.controls = []
    return page


class TestTheWindowStillBuilds:
    def test_the_control_tree_builds_against_the_installed_flet(self, page):
        app = VideodlApp(page)

        assert app.media_link is not None
        assert app.download_button is not None
        assert app.quality is not None

    def test_the_widgets_are_real_flet_controls(self, page):
        """Guard the guard: if flet were mocked here, everything below would pass hollow."""
        app = VideodlApp(page)

        assert isinstance(app.media_link, ft.Control)
        assert isinstance(app.download_progress_bar, ft.Control)
        assert not isinstance(ft.Text, MagicMock)

    def test_switching_language_touches_every_translated_label(self, page):
        """The refresh path runs against real controls, so a renamed property raises here."""
        app = VideodlApp(page)

        app._current_language_name = "🇬🇧"
        app._refresh_labels()
        english = app.download_button.content

        app._current_language_name = "🇫🇷"
        app._refresh_labels()

        assert app.download_button.content != english
