import logging
import sys


def videodl_logger(debug: bool = False) -> None:
    """
    Handle the app's logger

    Args:
        debug (bool, optional): If true, dump log Defaults to False.
    """
    log_level = logging.DEBUG if debug else logging.ERROR
    logger = logging.getLogger()
    logger.setLevel(log_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    if not debug:
        return

    file_handler = logging.FileHandler("video_dl.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
