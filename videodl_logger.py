import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_LOGGER_NAME = "videodl"
LOG_DIR = Path.home() / ".videodl" / "logs"
LOG_FILE = LOG_DIR / "videodl.log"


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

    # App logger: DEBUG when --debug or --verbose, INFO otherwise
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    if debug or verbose:
        app_logger.setLevel(logging.DEBUG)
    else:
        app_logger.setLevel(logging.INFO)

    # Always write to a rotating log file
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_level = logging.DEBUG if (debug or verbose) else logging.INFO
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=2)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
