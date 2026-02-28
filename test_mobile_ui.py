"""
Test the mobile UI layout on desktop.

Run with: python test_mobile_ui.py

This launches the app in mobile mode (scrollable, responsive widgets,
no window sizing) but uses desktop paths and subprocess — no pyjnius needed.
"""

from __future__ import annotations

import logging
import warnings

from videodl_logger import videodl_logger

warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


def main():
    videodl_logger(debug=True, verbose=False)
    logger = logging.getLogger("videodl")

    logger.debug("Initializing paths (desktop)")
    from sys_vars import init_paths

    init_paths()

    logger.debug("GUI startup (mobile simulation)")
    import flet as ft

    from gui.app import VideodlApp

    def _mobile_gui(page):
        page.window.width = 390  # iPhone 14 / Pixel 6a width
        page.window.height = 844
        app = VideodlApp(page, mobile=True)
        app.build_gui()
        app.load_config()

    ft.run(_mobile_gui, assets_dir="assets")


if __name__ == "__main__":
    main()
