from __future__ import annotations

import json
import os
import re
import subprocess
from subprocess import PIPE, STDOUT, run
from typing import List

from components_handlers.hwaccel_handler import fastest_encoder
from lang import GuiField, get_text
from sys_vars import FF_PATH
from utils.sys_utils import popen


def post_process_dl(full_name: str, target_vcodec: str, videodl_app) -> None:
    """
    Remux to ensure compatibility with NLEs or reencode to the target video
    codec the downloaded file through ffmpeg.

    Args:
        full_name (str): Full path of the file downloaded
        target_vcodec (str): Videoc codec to encode to if necessary
    """
    file_infos = ffprobe(full_name, cmd=FF_PATH.get("ffprobe"))["streams"]
    acodec, vcodec = "na", "na"
    for stream in file_infos:
        if stream["codec_type"] == "audio":
            acodec = stream["codec_name"]
        elif stream["codec_type"] == "video":
            vcodec = stream["codec_name"]
            big_dimension = 1080 < min(stream["width"], stream["height"])

    common_acodecs = ["aac", "mp3", "mp4a"]
    # Audio codecs NLE friendly
    acodec_nle_friendly = any(re.match(f"{c}", acodec) for c in common_acodecs)
    vcodec_equivalence = {
        "x264": "avc1", "x265": "hevc", "ProRes": "prores", "AV1": "av1"
        }
    vcodec_is_target = vcodec_equivalence[target_vcodec] == vcodec
    _ffmpeg_video(
        full_name,
        acodec_nle_friendly,
        vcodec_is_target,
        big_dimension,
        target_vcodec,
        videodl_app,
    )


def ffprobe(filename: str, cmd: str = "ffprobe") -> dict:
    """
    Run ffprobe on the specified file and return a JSON representation of the
    output.

    Args:
        filename (str): Path of the file to process
        cmd (str, optional): ffprobe path. Defaults to 'ffprobe'.

    Raises:
        ValueError: When the command errors out

    Returns:
        dict: File's infos
    """
    args = [cmd, "-show_format", "-show_streams", "-of", "json", filename]

    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise ValueError("ffprobe", out, err)
    return json.loads(out.decode("utf-8"))


def _ffmpeg_video(
    path: str,
    acodec_nle_friendly: bool,
    vcodec_is_target: bool,
    big_dimension: bool,
    target_vcodec: str,
    videodl_app,
) -> None:
    """
    Generate the ffmpeg command arguments and run it if the checkbox AudioOnly
    is unchecked.

    Args:
        path (str): Downloaded file's path
        acodec_nle_friendly (bool): Whether or not the audio codec is nle
            friendly
        vcodec_is_target (bool): Whether or not the video codec is the same
            as the targeted one
        smallest_dimension (int): Smallest video dimension
        target_vcodec (str): The video codec to convert to (if necessary)
        videodl_app (VideodlApp): GUIs object

    Raises:
        FileNotFoundError: If the resulted file doesn't exist because ffmpeg
            failed
    """
    ffmpeg_acodec = "aac" if not acodec_nle_friendly else "copy"
    new_ext = ".mov" if target_vcodec == "ProRes" else ".mp4"
    if vcodec_is_target:
        ffmpeg_vcodec, quality_options = "copy", []
    else:
        ffmpeg_vcodec, quality_options = fastest_encoder(path, target_vcodec)
    tmp_path = f"{os.path.splitext(path)[0]}.tmp{new_ext}"
    ffmpeg_command = [
        FF_PATH.get("ffmpeg"),
        "-hide_banner",
        "-i",
        path,
        "-c:a",
        ffmpeg_acodec,
        "-c:v",
        ffmpeg_vcodec,
    ]
    if big_dimension:
        ffmpeg_command.extend(quality_options)
    elif target_vcodec == "ProRes":
        ffmpeg_command.extend(["-profile:v", "0", "-qscale:v", "4"])
    ffmpeg_command.extend(["-y", tmp_path])
    action = (
        get_text(GuiField.ff_remux)
        if acodec_nle_friendly and vcodec_is_target
        else get_text(GuiField.ff_reencode)
    )
    _progress_ffmpeg(ffmpeg_command, action, path, videodl_app)
    if not os.path.isfile(tmp_path):
        raise FileNotFoundError(ffmpeg_command)
    os.remove(path)
    os.rename(src=tmp_path, dst=os.path.splitext(path)[0] + new_ext)


def _progress_ffmpeg(
    cmd: List[str], action: str, filepath: str, videodl_app
) -> None:
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
        progress_float = _get_progress_percent(items["time"], total_duration)
        progress_dict = {
            "speed": items["speed"],
            "processed_bytes": items["size"],
            "progress_float": progress_float,
            "action": action,
        }
        videodl_app._update_process_bar(progress_dict)


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


def _get_progress_percent(timestamp: str, total_duration: int) -> float:
    """
    Compute ffmpeg progress percentage. Using timestamp and not frame count as
    this value is slow to get through ffprobe.

    Args:
        timestamp (str): Converted file timestamp
        total_duration (int): Total duration of the file

    Returns:
        float: Progress float value
    """

    if timestamp == "N/A":
        return 0
    prog = [float(str_time) for str_time in timestamp.split(":")]
    timestamps_factors = [3600, 60, 1, 0.01]
    progress_seconds = sum(
        [factor * time for factor, time in zip(prog, timestamps_factors)]
    )
    progress_float = progress_seconds / total_duration
    return progress_float
