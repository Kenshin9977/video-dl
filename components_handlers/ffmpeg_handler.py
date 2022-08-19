from __future__ import annotations

import os
import re
import sys
from subprocess import PIPE, STDOUT, run
from typing import List

import ffmpeg
import PySimpleGUI as Sg
from lang import GuiField, get_text
from sys_vars import FF_PATH
from utils.gui_utils import create_progress_bar
from utils.sys_utils import popen

from components_handlers.hwaccel_handler import fastest_encoder


def post_process_dl(full_name: str, target_vcodec: str) -> None:
    """
    Remux to ensure compatibility with NLEs or reencode to the target video
    codec the downloaded file through ffmpeg.

    Args:
        full_name (str): Full path of the file downloaded
        target_vcodec (str): Videoc codec to encode to if necessary
    """
    file_infos = ffmpeg.probe(full_name, cmd=FF_PATH.get("ffprobe"))["streams"]
    acodec, vcodec = "na", "na"
    for i in range(0, min(2, len(file_infos))):
        if file_infos[i]["codec_type"] == "audio":
            acodec = file_infos[i]["codec_tag_string"]
        elif file_infos[i]["codec_type"] == "video":
            vcodec = file_infos[i]["codec_tag_string"]
    common_acodecs = ["aac", "mp3", "mp4a"]
    # Audio codecs NLE friendly
    acodec_nle_friendly = any(re.match(f"{c}", acodec) for c in common_acodecs)
    vcodec_nle_friendly = bool(
        re.match("avc1", vcodec) and target_vcodec == "x264"
    )
    _ffmpeg_video(
        full_name, acodec_nle_friendly, vcodec_nle_friendly, target_vcodec
    )


def _ffmpeg_video(
    path: str,
    acodec_nle_friendly: bool,
    vcodec_nle_friendly: bool,
    target_vcodec: str,
) -> None:
    """
    Generate the ffmpeg command arguments and run it if the checkbox AudioOnly
    is unchecked.

    Args:
        path (str): Downloaded file's path
        acodec_nle_friendly (bool): Whether or not the audio codec is nle
            friendly
        vcodec_nle_friendly (bool): Whether or not the audio codec is nle
            friendly
        target_vcodec (str): The video codec to convert to (if necessary)

    Raises:
        ffmpeg.Error: If the resulted file doesn't exist because ffmpeg failed
    """
    ffmpeg_acodec = "aac" if not acodec_nle_friendly else "copy"
    new_ext = ".mov" if target_vcodec == "ProRes" else ".mp4"
    ffmpeg_vcodec = (
        "copy" if vcodec_nle_friendly else fastest_encoder(path, target_vcodec)
    )
    tmp_path = f"{os.path.splitext(path)[0]}.tmp{new_ext}"
    ffmpegCommand = [
        FF_PATH.get("ffmpeg"),
        "-hide_banner",
        "-i",
        path,
        "-c:a",
        ffmpeg_acodec,
        "-c:v",
        ffmpeg_vcodec,
    ]
    if target_vcodec == "ProRes":
        ffmpegCommand.extend(["-profile:v", "0", "-qscale:v", "4"])
    ffmpegCommand.extend(["-y", tmp_path])
    action = (
        get_text(GuiField.ff_remux)
        if acodec_nle_friendly and vcodec_nle_friendly
        else get_text(GuiField.ff_reencode)
    )
    _progress_ffmpeg(ffmpegCommand, action, path)
    if not os.path.isfile(tmp_path):
        raise ffmpeg.Error(ffmpegCommand, sys.stdout, sys.stderr)
    os.remove(path)
    os.rename(src=tmp_path, dst=os.path.splitext(path)[0] + new_ext)


def _progress_ffmpeg(cmd: List[str], action: str, filepath: str) -> None:
    """
    Run the actual ffmpeg command and track its progress.

    Args:
        cmd (List[str]): Command's arguments
        action (str): Remuxing or reecoding
        filepath (str): Downloaded file's path

    Raises:
        ValueError: If the user cancel the download
    """
    total_duration = _get_accurate_file_duration(filepath)
    progress_window = create_progress_bar(action, False)
    progress_pattern = re.compile(
        r"(frame|fps|size|time|bitrate|speed)\s*=\s*(\S+)"
    )
    p = popen(cmd)

    while p.poll() is None:
        output = p.stderr.readline().rstrip(os.linesep) if p.stderr else ""
        print(output)
        progress_match = progress_pattern.findall(output)
        if not progress_match:
            continue
        items = {key: value for key, value in progress_match}
        event, _ = progress_window.read(timeout=10)
        if event == get_text(GuiField.cancel_button) or event == Sg.WIN_CLOSED:
            progress_window.close()
            raise ValueError
        progress_percent = _get_progress_percent(items["time"], total_duration)
        progress_window["PROGINFOS1"].update(f"{progress_percent}%")
        progress_window["PROGINFOS2"].update(
            f"{get_text(GuiField.ff_speed)}: {items['speed']}"
        )
        progress_window["-PROG-"].update(progress_percent)
    progress_window.close()


def _get_accurate_file_duration(filepath: str) -> int:
    """
    Get the real file (video or audio) duration using ffprobe.

    Args:
        filepath (str): File's path

    Returns
        int: File's duration in seconds
    """
    result = run(
        [
            FF_PATH.get("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filepath,
            "-loglevel",
            "quiet",
        ],
        stdout=PIPE,
        stderr=STDOUT,
    )
    return int(float(result.stdout))


def _get_progress_percent(timestamp: str, total_duration: int) -> int:
    """
    Compute ffmpeg progress percentage. Using timestamp and not frame count as
    this value is slow to get through ffprobe.

    Args:
        timestamp (str): Converted file timestamp
        total_duration (int): Total duration of the file

    Returns:
        int: _description_
    """
    prog = [float(str_time) for str_time in timestamp.split(":")]
    timestamps_factors = [3600, 60, 1, 0.01]
    progress_seconds = sum(
        [factor * time for factor, time in zip(prog, timestamps_factors)]
    )
    progress_percent = int(progress_seconds / total_duration * 100)
    return 99 if progress_percent > 100 else progress_percent
