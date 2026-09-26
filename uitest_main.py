"""Entry point for `flet test`: the real window, built by the real Flet.

No updater, no binary installs, and no user config, so every run starts from the
same state, in English whatever the machine's locale. Downloads land where the
tests say, not in the user's Downloads folder.
"""

import os

import flet as ft

import gui.config
import sys_vars
from gui.app import VideodlApp
from i18n.lang import get_available_languages_name, set_current_language

# The real app finds (or installs) ffmpeg in init_paths(). Here the tests hand over
# the ones on their own PATH instead, so nothing gets downloaded mid-run.
sys_vars.FF_PATH = {
    "ffmpeg": os.environ.get("VIDEODL_UITEST_FFMPEG", "ffmpeg"),
    "ffprobe": os.environ.get("VIDEODL_UITEST_FFPROBE", "ffprobe"),
}


# Toggling an option saves it to the user's config file. Point that somewhere the
# tests own, or every run rewrites the settings of whoever runs it.
if config_dir := os.environ.get("VIDEODL_UITEST_CONFIG_DIR"):
    gui.config._config_filename = os.path.join(config_dir, "videodl-config.toml")


def main(page: ft.Page):
    set_current_language(get_available_languages_name()[0])
    app = VideodlApp(page)
    app.build_gui()
    if download_dir := os.environ.get("VIDEODL_UITEST_DOWNLOAD_DIR"):
        app.download_path_text.value = download_dir
        page.update()


ft.run(main, assets_dir="assets")
