import argparse
import logging
import warnings

from videodl_logger import videodl_logger

warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


def main():
    parser = argparse.ArgumentParser(description="video-dl")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs for video-dl only")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logs for all libraries (Flet, urllib3, etc.)"
    )
    args = parser.parse_args()

    videodl_logger(debug=args.debug or args.verbose, verbose=args.verbose)
    logger = logging.getLogger("videodl")
    logger.debug("Checking for updates")

    from updater.client import check_for_updates

    app_has_been_updated = check_for_updates()
    if not app_has_been_updated:
        logger.debug("GUI startup")
        from gui.app import videodl_gui

        videodl_gui()


if __name__ == "__main__":
    main()
