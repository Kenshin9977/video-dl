import contextlib
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import runtime

APP_LOGGER_NAME = "videodl"


def get_log_dir() -> Path:
    if runtime.is_android():
        return Path("/sdcard/Download")
    return Path.home() / ".videodl" / "logs"


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

    if sys.stdout is not None:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False)  # noqa: SIM115
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

    # App logger: DEBUG when --debug or --verbose, INFO otherwise
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    if debug or verbose:
        app_logger.setLevel(logging.DEBUG)
    else:
        app_logger.setLevel(logging.INFO)

    # Always write to a rotating log file (skip if no storage permission)
    with contextlib.suppress(OSError):
        get_log_dir().mkdir(parents=True, exist_ok=True)
    add_log_file(
        get_log_dir() / "videodl.log",
        root_logger,
        level=logging.DEBUG if (debug or verbose) else logging.INFO,
        formatter=formatter,
        max_bytes=5 * 1024 * 1024,
        backup_count=2,
    )


def add_log_file(
    path: str | Path,
    logger: logging.Logger,
    *,
    level: int = logging.NOTSET,
    formatter: logging.Formatter | None = None,
    max_bytes: int = 1_000_000,
    backup_count: int = 1,
) -> bool:
    """Also log to `path`, if it can be written. Never raises.

    A log is not worth failing over. On Android a file in shared storage belongs to
    the install that created it: after a reinstall, or next to a debug build, the
    app is refused its own old log. v2.4.1 opened one unguarded at startup and the
    app would not start at all: PermissionError: '/sdcard/Download/video-dl-debug.log'.
    """
    try:
        handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    except OSError:
        return False
    handler.setLevel(level)
    if formatter:
        handler.setFormatter(formatter)
    logger.addHandler(handler)
    return True
