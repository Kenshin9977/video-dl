import logging

import fire

from gui_flet import videodl_gui
from updater.updater import update_app
from videodl_logger import videodl_logger

logger = logging.getLogger()

def main():
    fire.Fire(videodl_logger)
    logger.debug("Updating the app")
    app_has_been_updated = update_app()
    if not app_has_been_updated:
        logger.debug("GUI's startup")
        videodl_gui()

if __name__ == "__main__":
    main()
        
# TODO: Sign updates
# TODO: Autoinstall ffmpeg if missing on MacOS and Linux
