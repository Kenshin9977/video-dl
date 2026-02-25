import logging
import sys

APP_LOGGER_NAME = "videodl"


def videodl_logger(debug: bool = False, verbose: bool = False) -> None:
    """
    Handle the app's logger.

    Args:
        debug: If true, set the app logger to DEBUG (libraries stay at WARNING).
        verbose: If true, set ALL loggers to DEBUG (including Flet, urllib3, etc.).
    """
    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    # Root logger: only ERROR by default, WARNING in debug, DEBUG only in verbose
    root_logger = logging.getLogger()
    if verbose:
        root_logger.setLevel(logging.DEBUG)
    elif debug:
        root_logger.setLevel(logging.WARNING)
    else:
        root_logger.setLevel(logging.ERROR)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # App logger: DEBUG when --debug or --verbose
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    if debug or verbose:
        app_logger.setLevel(logging.DEBUG)

    if not (debug or verbose):
        return

    file_handler = logging.FileHandler("video_dl.log")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
