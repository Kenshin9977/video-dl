import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from platform import machine, system
from re import IGNORECASE, match, search
from subprocess import Popen, check_output
from typing import Any

import PySimpleGUI as Sg

APP_NAME = "video-dl"
APP_VERSION = "0.10.28"
PLATFORM = system()
VERSIONS_ARCHIVE_NAME = "versions.zip"
VERSIONS_JSON_NAME = "versions.json"

logger = logging.getLogger()


def get_ff_components_path() -> dict:
    """
    Get the path of ffmpeg and ffprobe if it exists on the system.

    Raises:
        FileNotFoundError: If ffmpeg can't be found on the system

    Returns:
        dict: The path for ffmpeg and ffprobe
    """
    ext = _get_extension_for_platform()
    ffmpeg_name, ffprobe_name = f"ffmpeg{ext}", f"ffprobe{ext}"
    ff_components = set([ffmpeg_name, ffprobe_name])
    cwd = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    cwd_files = os.listdir(cwd)
    if ff_components.issubset(set(cwd_files)):
        ffmpeg_path = os.path.join(cwd, ffmpeg_name)
        ffprobe_path = os.path.join(cwd, ffprobe_name)
        return {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}
    try:
        ffmpeg_version_cmd = check_output(["ffmpeg", "-version"])
        logger.debug("ffmpeg version: %s", ffmpeg_version_cmd)
        if ffmpeg_version_cmd is not None:
            return {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
    except FileNotFoundError:
        ffmpeg_missing()
        raise FileNotFoundError("ffmpeg is missing")


def _get_extension_for_platform() -> str:
    """
    Get the extension for binaries on the current platform.

    Returns:
        str: binary extension for the current platform
    """
    ext = ""
    platform = system()
    if platform == "Windows":
        ext = ".exe"
    return ext


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
        ext = "_amd64.deb"
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


def ffmpeg_missing() -> None:
    error_message = "Video-dl needs FFmpeg and FFprobe to work. "
    message = ""
    url = ""
    if PLATFORM == "Windows":
        message = (
            "On Windows, FFmpeg should be embedded with the app."
            "This error shouldn't happen. Please open an issue at "
        )
        url = "https://github.com/Kenshin9977/video-dl/issues"
    elif PLATFORM == "Darwin":
        message = "On MacOS you can follow this guide to install it: "
        url = "https://macappstore.org/ffmpeg/"
    elif PLATFORM == "Linux":
        message = (
            "On Linux you can install FFmpeg through your package manager "
            'using the package name "ffmpeg"'
        )

    Sg.theme("DarkBrown4")
    layout = [
        [Sg.Text(error_message, font=("Arial", 16, ""))],
        [Sg.Text(message, font=("Arial", 16, ""), text_color="white")],
        [
            Sg.Text(
                text=url,
                enable_events=True,
                font=("Courier New", 16, "underline"),
                key=url,
                text_color="white",
            )
        ],
    ]
    window = Sg.Window(
        "FFmpeg is missing",
        layout,
        finalize=True,
        element_justification="center",
    )

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED:
            break
        elif event.startswith("http"):
            webbrowser.open(event)
        print(event, values)
    window.close()
