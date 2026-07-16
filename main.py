import argparse
import logging
import platform
import sys
import warnings

from videodl_logger import videodl_logger

warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")


def _patch_mac_ver() -> None:
    """Give platform.mac_ver() a real version string on macOS.

    Python 3.14's mac_ver() returns '' on macOS 26, and darkdetect (and anything
    else that parses the version) then does int('') and crashes the whole GUI at
    import. sw_vers reports the real version regardless of the interpreter bug, so
    fill the gap from it. A no-op when mac_ver() already works.
    """
    if sys.platform != "darwin" or platform.mac_ver()[0]:
        return
    import subprocess

    try:
        version = subprocess.run(
            ["sw_vers", "-productVersion"], capture_output=True, text=True, timeout=5
        ).stdout.strip()
    except Exception:
        return
    if version:
        platform.mac_ver = lambda: (version, ("", "", ""), platform.machine())


_patch_mac_ver()


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
    # Loads the C extension behind XML/plist parsing. On macOS it links libexpat,
    # which the build repoints at a bundled copy; import it here so a broken repoint
    # fails CI instead of crashing a user the first time the app reads a plist.
    import plistlib  # noqa: F401

    import flet  # noqa: F401
    import tufup  # noqa: F401
    from yt_dlp.dependencies import available_dependencies
    from yt_dlp.version import __version__ as yt_dlp_version

    from core import aria2c_progress, ffmpegfd_progress, ytdlp_patch
    from core.download import download  # noqa: F401
    from gui.app import videodl_gui  # noqa: F401
    from sys_vars import init_paths  # noqa: F401
    from updater.client import check_for_updates  # noqa: F401

    missing = _REQUIRED_YT_DLP_DEPS - set(available_dependencies)
    if missing:
        raise SystemExit(f"yt-dlp is missing dependencies: {', '.join(sorted(missing))}")

    # All three reach into yt-dlp's internals to report progress, and all three fail
    # soft at runtime. This is the place that makes a yt-dlp bump that broke one loud.
    if not ytdlp_patch.install():
        raise SystemExit("the ffmpeg progress patch no longer applies to this yt-dlp")
    if not ffmpegfd_progress.install():
        raise SystemExit("the ffmpeg download progress patch no longer applies to this yt-dlp")
    if not aria2c_progress.install():
        raise SystemExit("the aria2c progress patch no longer applies to this yt-dlp")

    # Our VK extractor only reaches VK by taking the built-in one's place, and it can
    # only do that while they share a key. In a frozen binary this also proves
    # yt_dlp.extractor.vk got bundled, which lazy extractor loading makes easy to miss.
    from core.vk_extractor import VKIE

    if VKIE.ie_key() != "VK":
        raise SystemExit("the VK extractor no longer replaces the built-in one")

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
