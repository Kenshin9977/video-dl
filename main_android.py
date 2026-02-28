"""Android entry point — no updater, no argparse, no desktop binary auto-install."""

from __future__ import annotations

import logging
import warnings

from videodl_logger import videodl_logger

warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


def main():
    videodl_logger(debug=False, verbose=False)
    logger = logging.getLogger("videodl")

    logger.debug("Initializing Android paths")
    from runtime.android import AndroidPaths
    from sys_vars import init_paths_android

    init_paths_android(AndroidPaths())

    logger.debug("GUI startup (Android)")
    from gui.app import videodl_gui_android

    videodl_gui_android()


if __name__ == "__main__":
    main()
