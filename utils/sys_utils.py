import logging
import os
import subprocess
import sys
from platform import system
from re import match
from subprocess import Popen, check_output
from typing import Any

import flet as ft

from utils.install_ffmpeg import (
    ffmpeg_missing_on_linux,
    ffmpeg_missing_on_mac,
    ffmpeg_missing_on_windows,
    ffmpeg_progress_page,
)
from utils.sys_architecture import ARCHITECTURE

APP_NAME = "video-dl"
APP_VERSION = "1.1.15"
PLATFORM = system()
VERSIONS_ARCHIVE_NAME = "versions.zip"
VERSIONS_JSON_NAME = "versions.json"
FFMPEG_WINGET_VERSION = "7.1"

logger = logging.getLogger()

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
    ff_bin_path = os.path.join(os.getenv("LOCALAPPDATA"), "video-dl")
    ffmpeg_path = os.path.join(ff_bin_path, ffmpeg_name)
    ffprobe_path = os.path.join(ff_bin_path, ffprobe_name)

    if not (ffmpeg_path.exists() and ffprobe_path.exists()):
        logger.info(f"FF components not found at {ff_bin_path}")
        ft.app(target=ffmpeg_progress_page, args=[ff_bin_path])

    try:
        ffmpeg_version_cmd = subprocess.run(
            [ffmpeg_path, "-version"], capture_output=True
        )
    except Exception:
        ft.app(ffmpeg_missing_on_windows)
        sys.exit(-1)

    if ffmpeg_version_cmd.returncode == 0:
        logger.info(f"FFmpeg found at {ffmpeg_path}")
        return {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}

    ft.app(ffmpeg_missing_on_windows)
    sys.exit(-1)


def get_ff(ffmpeg_name, ffprobe_name):
    if PLATFORM == "Linux":
        ff_missing_function = ffmpeg_missing_on_linux
    elif PLATFORM == "Darwin":
        ff_missing_function = ffmpeg_missing_on_mac

    try:
        ffmpeg_version_cmd = subprocess.run(
            [ffmpeg_name, "-version"], capture_output=True
        )
    except Exception:
        ft.app(ff_missing_function)
        sys.exit(-1)

    if ffmpeg_version_cmd.returncode == 0:
        logger.info(f"FFmpeg found at {ffmpeg_name}")
        return {"ffmpeg": ffmpeg_name, "ffprobe": ffprobe_name}

    ft.app(ff_missing_function)
    sys.exit(-1)


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
    architecture = ARCHITECTURE
    return f"{APP_NAME}-{PLATFORM}-{architecture}-{APP_VERSION}.zip"


def get_startup_info() -> Any:
    startupinfo = None
    if PLATFORM == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return startupinfo


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
