import logging
import fire
from videodl_logger import videodl_logger

def main(debug=False):
    videodl_logger(debug=debug)
    logger = logging.getLogger()
    logger.debug("Updating the app")

    from gui_flet import videodl_gui
    from updater.updater import update_app

    app_has_been_updated = update_app()
    if not app_has_been_updated:
        logger.debug("GUI's startup")
        videodl_gui()


if __name__ == "__main__":
    fire.Fire(main)
