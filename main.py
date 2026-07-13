import argparse
import logging
import warnings

from videodl_logger import videodl_logger

warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


# yt-dlp imports these lazily, inside try/except ImportError, and degrades
# silently when they are absent: no audio tagging without mutagen, no AES without
# Cryptodome, no websocket transport without websockets. A frozen binary that
# dropped one of them looks perfectly healthy until a user hits the code path.
_REQUIRED_YT_DLP_DEPS = frozenset({"Cryptodome", "brotli", "certifi", "mutagen", "websockets", "yt_dlp_ejs"})


def selftest() -> None:
    """Import every heavy dependency, check yt-dlp is whole, and exit.

    The packaged binary is the only place a missing PyInstaller hiddenimport
    shows up, and it shows up at startup. CI runs this against the frozen
    executable so the failure lands on a pull request instead of in a published
    release. Paths are deliberately not initialized: that would try to download
    ffmpeg on a bare runner.
    """
    import flet  # noqa: F401
    import tufup  # noqa: F401
    from yt_dlp.dependencies import available_dependencies
    from yt_dlp.version import __version__ as yt_dlp_version

    from core.download import download  # noqa: F401
    from gui.app import videodl_gui  # noqa: F401
    from sys_vars import init_paths  # noqa: F401
    from updater.client import check_for_updates  # noqa: F401

    missing = _REQUIRED_YT_DLP_DEPS - set(available_dependencies)
    if missing:
        raise SystemExit(f"yt-dlp is missing dependencies: {', '.join(sorted(missing))}")

    print(f"selftest ok (yt-dlp {yt_dlp_version})")


def main():
    parser = argparse.ArgumentParser(description="video-dl")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs for video-dl only")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logs for all libraries (Flet, urllib3, etc.)"
    )
    parser.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    videodl_logger(debug=args.debug or args.verbose, verbose=args.verbose)
    logger = logging.getLogger("videodl")
    logger.debug("Checking for updates")

    from updater.client import check_for_updates

    app_has_been_updated = check_for_updates()
    if not app_has_been_updated:
        logger.debug("Initializing binary paths")
        from sys_vars import init_paths

        init_paths()

        logger.debug("GUI startup")
        from gui.app import videodl_gui

        videodl_gui()


if __name__ == "__main__":
    main()
