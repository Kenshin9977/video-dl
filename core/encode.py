from __future__ import annotations

import json
import logging
import os
import subprocess

from yt_dlp.postprocessor.ffmpeg import FFmpegProgressTracker

from core.hwaccel import fastest_encoder
from i18n.lang import GuiField, get_text
from sys_vars import FF_PATH

NLE_COMPATIBLE_VCODECS = {"avc1", "h264", "hevc", "h265", "prores"}
NLE_COMPATIBLE_ACODECS = {"aac", "mp3", "mp4a", "pcm_s16le", "pcm_s24le"}

_VCODEC_NAME_TO_TARGET = {
    "avc1": "x264",
    "h264": "x264",
    "hevc": "x265",
    "h265": "x265",
    "prores": "ProRes",
}
# Inverse mapping: target codec → canonical ffprobe name (first match wins)
_TARGET_TO_VCODEC_NAME = {"x264": "avc1", "x265": "hevc", "ProRes": "prores", "AV1": "av1"}


def needs_reencode(vcodec: str, acodec: str) -> tuple[bool, bool]:
    """Return (video_needs_reencode, audio_needs_reencode)."""
    v_needs = vcodec.lower() not in NLE_COMPATIBLE_VCODECS
    a_needs = acodec.lower() not in NLE_COMPATIBLE_ACODECS
    return v_needs, a_needs


def post_process_dl(full_name: str, target_vcodec: str, videodl_app) -> None:
    """
    Remux to ensure compatibility with NLEs or reencode to the target video
    codec the downloaded file through ffmpeg.

    Args:
        full_name (str): Full path of the file downloaded
        target_vcodec (str): Video codec target ("Best", "NLE", "x264", etc.)
    """
    if target_vcodec == "Best":
        return

    probe_data = ffprobe(full_name, cmd=FF_PATH.get("ffprobe"))  # type: ignore[arg-type]
    file_infos = probe_data["streams"]
    duration = int(float(probe_data["format"]["duration"]))
    acodec, vcodec = "na", "na"
    big_dimension = False
    for stream in file_infos:
        if stream["codec_type"] == "audio":
            acodec = stream["codec_name"]
        elif stream["codec_type"] == "video":
            vcodec = stream["codec_name"]
            big_dimension = min(stream["width"], stream["height"]) > 1080

    if target_vcodec == "Original":
        # Remux only — copy both streams into mp4 container
        acodec_nle_friendly = True
        vcodec_is_target = True
        target_vcodec = _VCODEC_NAME_TO_TARGET.get(vcodec.lower(), "x264")
    elif target_vcodec == "NLE":
        v_needs, a_needs = needs_reencode(vcodec, acodec)
        resolved = _VCODEC_NAME_TO_TARGET.get(vcodec.lower(), "x264")
        acodec_nle_friendly = not a_needs
        if not v_needs:
            # Video already NLE-compatible — remux (copy video)
            vcodec_is_target = True
            target_vcodec = resolved
        else:
            # Video incompatible — re-encode to x264
            vcodec_is_target = False
            target_vcodec = "x264"
    else:
        acodec_nle_friendly = acodec.lower() in NLE_COMPATIBLE_ACODECS
        vcodec_is_target = _TARGET_TO_VCODEC_NAME.get(target_vcodec) == vcodec

    _ffmpeg_video(
        full_name,
        acodec_nle_friendly,
        vcodec_is_target,
        big_dimension,
        target_vcodec,
        videodl_app,
        duration,
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
    duration: int,
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
        big_dimension (bool): Whether the video is larger than 1080p
        target_vcodec (str): The video codec to convert to (if necessary)
        videodl_app (VideodlApp): GUIs object
        duration (int): File duration in seconds (from ffprobe)

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
        "-metadata",
        "creation_time=now",
    ]
    if big_dimension:
        ffmpeg_command.extend(quality_options)
    elif target_vcodec == "ProRes":
        ffmpeg_command.extend(["-profile:v", "0", "-qscale:v", "4"])
    ffmpeg_command.extend(["-progress", "pipe:1", "-y", tmp_path])
    action = get_text(GuiField.ff_remux) if acodec_nle_friendly and vcodec_is_target else get_text(GuiField.ff_reencode)
    _progress_ffmpeg(ffmpeg_command, action, path, videodl_app, duration)
    if videodl_app._cancel_requested.is_set():
        if os.path.isfile(tmp_path):
            os.remove(tmp_path)
        return
    if not os.path.isfile(tmp_path):
        raise FileNotFoundError(ffmpeg_command)
    os.remove(path)
    os.rename(src=tmp_path, dst=os.path.splitext(path)[0] + new_ext)


class _MinimalYDL:
    """Minimal ydl stub so FFmpegProgressTracker enables progress tracking."""

    @staticmethod
    def write_debug(msg):
        logging.debug(msg)


def _progress_ffmpeg(cmd, action, filepath, videodl_app, duration):
    """
    Run ffmpeg with progress tracking using FFmpegProgressTracker.

    Args:
        cmd (list): FFmpeg command arguments (must include -progress pipe:1)
        action (str): Display label (e.g. "Remuxing" or "Re-encoding")
        filepath (str): Input file path (for filesize lookup)
        videodl_app: GUI app instance with _update_process_bar method
        duration (int): File duration in seconds (already probed)
    """
    filesize = os.path.getsize(filepath)
    info_dict = {
        "duration": duration,
        "filesize": filesize,
    }

    def hook(status, info):
        if videodl_app._cancel_requested.is_set():
            if tracker.ffmpeg_proc and tracker.ffmpeg_proc.poll() is None:
                tracker.ffmpeg_proc.kill()
            return
        status["processed_bytes"] = status.get("outputted", 0)
        status["action"] = action
        videodl_app._update_process_bar(status)

    tracker = FFmpegProgressTracker(
        info_dict,
        cmd,
        hook,
        ydl=_MinimalYDL(),
        output_filename=cmd[-1],
    )
    _, stderr, retcode = tracker.run_ffmpeg_subprocess()
    if videodl_app._cancel_requested.is_set():
        return
    if retcode != 0:
        raise ValueError(f"FFmpeg failed with return code {retcode}: {stderr}")
