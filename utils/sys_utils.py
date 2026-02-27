import logging
import os
import subprocess
import sys
from pathlib import Path
from platform import system

import flet as ft

from utils.aria2_install import (
    aria2c_brew_install_page,
    aria2c_info_linux,
    aria2c_progress_page,
    get_aria2c_install_folder,
)
from utils.ffmpeg_install import (
    ffmpeg_missing_on_linux,
    ffmpeg_missing_on_mac,
    ffmpeg_missing_on_windows,
    ffmpeg_progress_page,
)
from utils.quickjs_install import (
    get_quickjs_install_folder,
    quickjs_missing,
    quickjs_progress_page,
)

APP_NAME = "video-dl"
APP_VERSION = "2.1.0"
PLATFORM = system()

_PLATFORM_SUFFIX_MAP = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}
PLATFORM_APP_NAME = f"{APP_NAME}-{_PLATFORM_SUFFIX_MAP.get(PLATFORM, PLATFORM.lower())}"

logger = logging.getLogger("videodl")

logger.info(f"Platform is '{PLATFORM}'")


def get_ff_components_path() -> dict:
    """
    Get the path of ffmpeg and ffprobe if it exists on the system.

    Returns:
        dict: The path for ffmpeg and ffprobe
    """
    ext = _get_extension_for_platform()
    ffmpeg_name, ffprobe_name = f"ffmpeg{ext}", f"ffprobe{ext}"
    if PLATFORM == "Windows":
        return get_ff_windows(ffmpeg_name, ffprobe_name)
    elif PLATFORM in ["Darwin", "Linux"]:
        return get_ff(ffmpeg_name, ffprobe_name)
    else:
        sys.exit(-1)


def get_ff_windows(ffmpeg_name, ffprobe_name):
    ff_bin_path = os.path.join(os.getenv("LOCALAPPDATA", ""), "video-dl")
    ffmpeg_path = os.path.join(ff_bin_path, ffmpeg_name)
    ffprobe_path = os.path.join(ff_bin_path, ffprobe_name)

    if not (Path(ffmpeg_path).exists() and Path(ffprobe_path).exists()):
        logger.info(f"FF components not found at {ff_bin_path}")
        ft.run(ffmpeg_progress_page)

    try:
        ffmpeg_version_cmd = subprocess.run([ffmpeg_path, "-version"], capture_output=True)
    except Exception:
        ft.run(ffmpeg_missing_on_windows)
        sys.exit(-1)

    if ffmpeg_version_cmd.returncode == 0:
        logger.info(f"FFmpeg found at {ffmpeg_path}")
        return {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}

    ft.run(ffmpeg_missing_on_windows)
    sys.exit(-1)


def get_ff(ffmpeg_name, ffprobe_name):
    if PLATFORM == "Linux":
        ff_missing_function = ffmpeg_missing_on_linux
    elif PLATFORM == "Darwin":
        ff_missing_function = ffmpeg_missing_on_mac

    ffmpeg_path = _find_executable(ffmpeg_name)
    if ffmpeg_path:
        ffprobe_path = _find_executable(ffprobe_name) or ffprobe_name
        logger.info(f"FFmpeg found at {ffmpeg_path}")
        return {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}

    ft.run(ff_missing_function)
    sys.exit(-1)


def _find_executable(name):
    """Find an executable by name, checking PATH and common install locations."""
    import shutil

    found = shutil.which(name)
    if found:
        return found

    # Common locations not always in PATH (e.g. Homebrew on Apple Silicon/Intel)
    extra_dirs = ["/opt/homebrew/bin", "/usr/local/bin"]
    for d in extra_dirs:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def get_quickjs_path() -> str | None:
    """
    Get the path of QuickJS binary if it exists on the system.

    Returns:
        str | None: The path for QuickJS binary, or None if not found
    """
    ext = _get_extension_for_platform()
    qjs_name = f"qjs{ext}"
    if PLATFORM == "Windows":
        return _get_quickjs_windows(qjs_name)
    elif PLATFORM in ["Darwin", "Linux"]:
        return _get_quickjs_unix(qjs_name)
    return None


def _get_quickjs_windows(qjs_name):
    qjs_bin_path = get_quickjs_install_folder()
    qjs_path = os.path.join(qjs_bin_path, qjs_name)

    if not Path(qjs_path).exists():
        logger.info(f"QuickJS not found at {qjs_bin_path}")
        ft.run(quickjs_progress_page)

    if Path(qjs_path).exists():
        logger.info(f"QuickJS found at {qjs_path}")
        return qjs_path

    ft.run(quickjs_missing)
    sys.exit(-1)


def _get_quickjs_unix(qjs_name):
    # Check system PATH first
    qjs_path = _find_executable(qjs_name)
    if qjs_path:
        logger.info(f"QuickJS found at {qjs_path}")
        return qjs_path

    # Check our install folder
    qjs_bin_path = get_quickjs_install_folder()
    qjs_path = os.path.join(qjs_bin_path, qjs_name)
    if Path(qjs_path).exists():
        logger.info(f"QuickJS found at {qjs_path}")
        return qjs_path

    # Auto-download
    logger.info("QuickJS not found, downloading...")
    ft.run(quickjs_progress_page)

    if Path(qjs_path).exists():
        logger.info(f"QuickJS installed at {qjs_path}")
        return qjs_path

    ft.run(quickjs_missing)
    sys.exit(-1)


def get_aria2c_path() -> str | None:
    """
    Get the path of aria2c binary if it exists on the system.
    Auto-installs on Windows (zip) and macOS (brew). On Linux, shows info page.

    Returns:
        str | None: The path for aria2c binary, or None if not found
    """
    ext = _get_extension_for_platform()
    aria2c_name = f"aria2c{ext}"
    if PLATFORM == "Windows":
        return _get_aria2c_windows(aria2c_name)
    elif PLATFORM == "Darwin":
        return _get_aria2c_macos(aria2c_name)
    elif PLATFORM == "Linux":
        return _get_aria2c_linux(aria2c_name)
    return None


def _get_aria2c_windows(aria2c_name):
    install_folder = get_aria2c_install_folder()
    aria2c_path = os.path.join(install_folder, aria2c_name)

    if Path(aria2c_path).exists():
        logger.info(f"aria2c found at {aria2c_path}")
        return aria2c_path

    # Auto-install
    logger.info("aria2c not found on Windows, downloading...")
    ft.run(aria2c_progress_page)

    if Path(aria2c_path).exists():
        logger.info(f"aria2c installed at {aria2c_path}")
        return aria2c_path

    logger.warning("aria2c installation failed, continuing without it")
    return None


def _get_aria2c_macos(aria2c_name):
    # Check system PATH first
    aria2c_path = _find_executable(aria2c_name)
    if aria2c_path:
        logger.info(f"aria2c found at {aria2c_path}")
        return aria2c_path

    # Try brew install
    import shutil

    if shutil.which("brew"):
        logger.info("aria2c not found, attempting brew install...")
        ft.run(aria2c_brew_install_page)

        aria2c_path = _find_executable(aria2c_name)
        if aria2c_path:
            logger.info(f"aria2c installed at {aria2c_path}")
            return aria2c_path

    # No brew or install failed — show info page like Linux
    logger.info("aria2c not available on macOS (no brew or install failed)")
    ft.run(aria2c_info_linux)
    return None


def _get_aria2c_linux(aria2c_name):
    aria2c_path = _find_executable(aria2c_name)
    if aria2c_path:
        logger.info(f"aria2c found at {aria2c_path}")
        return aria2c_path

    # Show info page
    logger.info("aria2c not found on Linux, showing info page")
    ft.run(aria2c_info_linux)
    return None


def _get_extension_for_platform() -> str:
    """
    Get the extension for binaries on the current platform.

    Returns:
        str: binary extension for the current platform
    """
    return ".exe" if PLATFORM == "Windows" else ""


_BUNDLE_ID_TO_BROWSER = {
    "com.apple.safari": "Safari",
    "com.google.chrome": "Chrome",
    "org.mozilla.firefox": "Firefox",
    "com.brave.browser": "Brave",
    "com.microsoft.edgemac": "Edge",
    "com.operasoftware.opera": "Opera",
    "com.vivaldi.vivaldi": "Vivaldi",
    "org.chromium.chromium": "Chromium",
}

_DESKTOP_FILE_TO_BROWSER = {
    "firefox": "Firefox",
    "google-chrome": "Chrome",
    "chromium": "Chromium",
    "chromium-browser": "Chromium",
    "brave-browser": "Brave",
    "microsoft-edge": "Edge",
    "opera": "Opera",
    "vivaldi-stable": "Vivaldi",
}

_PROGID_TO_BROWSER = {
    "chromehtml": "Chrome",
    "firefoxurl": "Firefox",
    "bravehtml": "Brave",
    "msedgehtm": "Edge",
    "operastable": "Opera",
    "vivaldihtm": "Vivaldi",
    "safarihtml": "Safari",
}


def get_default_browser() -> str | None:
    """Detect the system's default browser. Returns a browser name or None."""
    try:
        if PLATFORM == "Darwin":
            return _detect_browser_macos()
        elif PLATFORM == "Linux":
            return _detect_browser_linux()
        elif PLATFORM == "Windows":
            return _detect_browser_windows()
    except Exception:
        pass
    return None


def _detect_browser_macos() -> str | None:
    import plistlib

    plist_path = os.path.expanduser(
        "~/Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist"
    )
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)
    for handler in data.get("LSHandlers", []):
        if handler.get("LSHandlerURLScheme") in ("https", "http"):
            bundle_id = handler.get("LSHandlerRoleAll", "").lower()
            return _BUNDLE_ID_TO_BROWSER.get(bundle_id)
    return None


def _detect_browser_linux() -> str | None:
    result = subprocess.run(["xdg-settings", "get", "default-web-browser"], capture_output=True, text=True)
    desktop_file = result.stdout.strip().lower().removesuffix(".desktop")
    return _DESKTOP_FILE_TO_BROWSER.get(desktop_file)


def _detect_browser_windows() -> str | None:
    import winreg

    key_path = (
        r"Software\Microsoft\Windows\Shell\Associations"
        r"\UrlAssociations\http\UserChoice"
    )
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:  # type: ignore[attr-defined]
        prog_id = winreg.QueryValueEx(key, "ProgId")[0]  # type: ignore[attr-defined]
    return _PROGID_TO_BROWSER.get(prog_id.lower())


def get_default_download_path() -> str:
    """
    Get the default download folder path.

    Returns:
        str: Default download folder path
    """
    if system() != "Windows":
        download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(download_path):
            return download_path
        return ""

    import winreg

    key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as sub_key:  # type: ignore[attr-defined]
        location = winreg.QueryValueEx(sub_key, downloads_guid)[0]  # type: ignore[attr-defined]
    return location
