import logging
import os
import subprocess
import sys
from pathlib import Path
from platform import machine, system
from re import IGNORECASE, match, search
from subprocess import Popen, check_output
from typing import Any

import flet as ft

APP_NAME = "video-dl"
APP_VERSION = "1.1.14"
PLATFORM = system()
VERSIONS_ARCHIVE_NAME = "versions.zip"
VERSIONS_JSON_NAME = "versions.json"
FFMPEG_WINGET_VERSION = "7.1"

logger = logging.getLogger()

logger.info(f"Platform is '{PLATFORM}'")

def add_ffmpeg_to_path():
    username = os.getlogin()
    ffmpeg_bin_path = Path(
        f"C:/Users/{username}/AppData/Local/Microsoft/WinGet/Packages/"
        "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
        f"ffmpeg-{FFMPEG_WINGET_VERSION}-full_build/bin"
    )

    if not ffmpeg_bin_path.exists():
        logger.error(f"FFmpeg path not found at {ffmpeg_bin_path}")
        sys.exit(1)

    path_env = os.environ.get("PATH", "")
    if str(ffmpeg_bin_path) not in path_env:
        logger.info(f"Adding {ffmpeg_bin_path} to PATH")        
        subprocess.run(
            ["setx", "PATH", f"{path_env};{ffmpeg_bin_path}"],
            shell=True, capture_output=True
        )
        logger.info("FFmpeg path added. Please restart the terminal for changes to take effect.")
    else:
        logger.info("FFmpeg is already in the PATH")


def install_ffmpeg_on_windows():
    """Install ffmpeg using winget."""
    try:
        subprocess.run(
            ["winget", "install", "--id=Gyan.FFmpeg", "-e", "--version", FFMPEG_WINGET_VERSION],
            check=True,
        )
        add_ffmpeg_to_path()
        logger.info("FFmpeg installation completed.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install ffmpeg: {e}")
        sys.exit(-1)


def get_ff_components_path() -> dict:
    """
    Get the path of ffmpeg and ffprobe if it exists on the system.

    Returns:
        dict: The path for ffmpeg and ffprobe
    """
    ext = _get_extension_for_platform()
    ffmpeg_name, ffprobe_name = f"ffmpeg{ext}", f"ffprobe{ext}"
    username = os.getlogin()
    ff_bin_path = Path(
        f"C:/Users/{username}/AppData/Local/Microsoft/WinGet/Packages/"
        "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/"
        f"ffmpeg-{FFMPEG_WINGET_VERSION}-full_build/bin"
    )
    if not ff_bin_path.exists():
        logger.info(f"FFmpeg path not found at {ff_bin_path}")
        install_ffmpeg_on_windows()

    ffmpeg_path = os.path.join(ff_bin_path, ffmpeg_name)
    ffprobe_path = os.path.join(ff_bin_path, ffprobe_name)

    try:
        ffmpeg_version_cmd = subprocess.run(
            [ffmpeg_path, "-version"], capture_output=True
        )
    except Exception:
        ft.app(ffmpeg_missing)
        sys.exit(-1)

    if ffmpeg_version_cmd.returncode == 0:
        logger.info(f"FFmpeg found at {ffmpeg_path}")
        return {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}
    raise SystemError("FFmpeg is missing")




def _get_extension_for_platform() -> str:
    """
    Get the extension for binaries on the current platform.

    Returns:
        str: binary extension for the current platform
    """
    return ".exe" if PLATFORM == "Windows" else ""


def popen(cmd: list) -> Popen:
    """
    Popen handler for OSs. Avoid opening a console when running commands.

    Args:
        cmd (list): Commands list

    Returns:
        Popen: Popen object
    """
    process = Popen(
        cmd,
        startupinfo=get_startup_info(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf8",
    )
    return process


def check_cmd_output(cmd: list[str]) -> str:
    """
    Check the output of the cmd executed by the system.

    Args:
        cmd (list[str]): Command line to be executed

    Returns:
        str: The output of the command line
    """
    return check_output(cmd, startupinfo=get_startup_info())


def get_system_architecture() -> str:
    """
    Get the streamlined name of the current system architecture.

    Returns:
        str: The streamlined name of the current system architecture.
    """
    architecture = machine()
    if search("arm64|aarch64", architecture, IGNORECASE):
        return "arm64"
    elif search("arm", architecture, IGNORECASE):
        return "arm"
    elif search("86", architecture, IGNORECASE):
        return "x86"
    elif search("64", architecture, IGNORECASE):
        return "x86_64"


def get_bin_ext_for_platform() -> str:
    ext = None
    if PLATFORM == "Windows":
        ext = ".exe"
    elif PLATFORM == "Linux":
        ext = ""
    elif PLATFORM == "Darwin":
        ext = ".app"
    if ext is None:
        logger.error("Platform isn't supported")
        raise RuntimeError
    return f"{APP_NAME}{ext}"


def gen_archive_name() -> str:
    correct_format = match(
        r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)", APP_VERSION
    )
    if not correct_format:
        logger.error("Version number isn't formatted correctly")
        raise ValueError
    architecture = get_system_architecture()
    return f"{APP_NAME}-{PLATFORM}-{architecture}-{APP_VERSION}.zip"


def get_startup_info() -> Any:
    startupinfo = None
    if PLATFORM == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


def ffmpeg_missing(page: ft.Page) -> None:
    message = "FFmpeg is missing. "
    url = ""
    if PLATFORM == "Windows":
        message += (
            "On Windows, it should be installed if missing.\n"
            "This error shouldn't happen. Please open an issue on the following link:"
        ) 
        url = "[https://github.com/Kenshin9977/video-dl/issues](https://github.com/Kenshin9977/video-dl/issues)"
    elif PLATFORM == "Darwin":
        message = "On MacOS you can follow this guide to install it:"
        url = "[Install FFmpeg](https://macappstore.org/ffmpeg/)"
    elif PLATFORM == "Linux":
        message = (
            "On Linux you can install FFmpeg through your \n"
            'package manager using the package name "ffmpeg"'
        )
    page.title = "FFmpeg required"
    error_message = "Video-dl needs FFmpeg and FFprobe to work. "
    page.add(
        ft.Text(error_message, color="red"),
        ft.Text(message),
        ft.Markdown(url, on_tap_link=lambda e: page.launch_url(e.data)),
    )
    page.update()


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
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as sub_key:
        location = winreg.QueryValueEx(sub_key, downloads_guid)[0]
    return location
