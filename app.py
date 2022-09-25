import logging

import fire

from gui import video_dl_gui
from updater.updater import Updater
from videodl_logger import videodl_logger

logger = logging.getLogger()

if __name__ == "__main__":
    fire.Fire(videodl_logger)
    Updater().update_app()
    logger.debug("GUI's startup")
    video_dl_gui()

# TODO: Write tests
# TODO: Sign updates
# TODO: Handle MacOS and Linux updater
# TODO: Autoinstall ffmpeg if missing os MacOS and Linux
# TODO: Investigate pyinstaller crosscompilation to generate new versions
