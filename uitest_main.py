"""Entry point for `flet test`: the real window, built by the real Flet.

No updater, no binary installs, and no user config, so every run starts from the
same state, in English whatever the machine's locale.
"""

import flet as ft

from gui.app import VideodlApp
from i18n.lang import get_available_languages_name, set_current_language


def main(page: ft.Page):
    set_current_language(get_available_languages_name()[0])
    VideodlApp(page).build_gui()


ft.run(main, assets_dir="assets")
