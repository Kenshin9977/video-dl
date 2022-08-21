import logging
import os
import subprocess
import sys
from asyncio.windows_utils import Popen
from pathlib import Path
from platform import machine, system
from re import IGNORECASE, search
from subprocess import check_output

log = logging.getLogger(__name__)


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
        if ffmpeg_version_cmd is not None:
            return {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
    except FileNotFoundError:
        raise FileNotFoundError("ffmpeg is not installed")


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
    Popen handler for Windows. Avoid opening a console when running commands.

    Args:
        cmd (list): Commands list

    Returns:
        Popen: Popen object
    """
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = subprocess.Popen(
        cmd,
        startupinfo=startupinfo,
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
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return check_output(cmd, startupinfo=startupinfo)


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
