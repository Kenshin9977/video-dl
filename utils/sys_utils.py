import logging
import os
import subprocess
import sys
from asyncio.windows_utils import Popen
from pathlib import Path
from platform import system
from subprocess import check_output

log = logging.getLogger(__name__)


def get_ff_components_path():
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


def check_cmd_output(cmd):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return check_output(cmd, startupinfo=startupinfo)
