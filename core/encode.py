from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import TYPE_CHECKING

from yt_dlp.postprocessor.ffmpeg import FFmpegProgressTracker

from core.hwaccel import fastest_encoder
from i18n.lang import GuiField, get_text

if TYPE_CHECKING:
    from core.callbacks import CancelToken, ProgressCallback
    from runtime.base import ProcessRunner

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


def post_process_dl(
    full_name: str,
    target_vcodec: str,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
    ff_path: dict[str, str] | None = None,
) -> None:
    """
    Remux to ensure compatibility with NLEs or reencode to the target video
    codec the downloaded file through ffmpeg.

    Args:
        full_name: Full path of the file downloaded
        target_vcodec: Video codec target ("Best", "NLE", "x264", etc.)
        cancel: Cancellation token
        progress_cb: Progress callback
        ff_path: FFmpeg/FFprobe paths (lazy-loaded from sys_vars if None)
    """
    if target_vcodec == "Best":
        return

    if ff_path is None:
        from sys_vars import FF_PATH

        ff_path = FF_PATH

    probe_data = ffprobe(full_name, cmd=ff_path.get("ffprobe"))  # type: ignore[arg-type]
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
        cancel,
        progress_cb,
        duration,
        ff_path,
    )


def ffprobe(
    filename: str,
    cmd: str = "ffprobe",
    process_runner: ProcessRunner | None = None,
) -> dict:
    """
    Run ffprobe on the specified file and return a JSON representation of the
    output.

    Args:
        filename: Path of the file to process
        cmd: ffprobe path. Defaults to 'ffprobe'.
        process_runner: Optional ProcessRunner (falls back to subprocess)

    Raises:
        ValueError: When the command errors out

    Returns:
        File's infos
    """
    args = [cmd, "-show_format", "-show_streams", "-of", "json", filename]

    if process_runner is not None:
        result = process_runner.popen_communicate(args)
        if result.returncode != 0:
            raise ValueError("ffprobe", result.stdout, result.stderr)
        return json.loads(result.stdout)

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
    cancel: CancelToken,
    progress_cb: ProgressCallback,
    duration: int,
    ff_path: dict[str, str] | None = None,
) -> None:
    """
    Generate the ffmpeg command arguments and run it.

    Args:
        path: Downloaded file's path
        acodec_nle_friendly: Whether the audio codec is NLE friendly
        vcodec_is_target: Whether the video codec matches the target
        big_dimension: Whether the video is larger than 1080p
        target_vcodec: The video codec to convert to (if necessary)
        cancel: Cancellation token
        progress_cb: Progress callback
        duration: File duration in seconds (from ffprobe)
        ff_path: FFmpeg/FFprobe paths

    Raises:
        FileNotFoundError: If the output file doesn't exist because ffmpeg failed
    """
    if ff_path is None:
        from sys_vars import FF_PATH

        ff_path = FF_PATH

    ffmpeg_acodec = "aac" if not acodec_nle_friendly else "copy"
    new_ext = ".mov" if target_vcodec == "ProRes" else ".mp4"
    if vcodec_is_target:
        ffmpeg_vcodec, quality_options = "copy", []
    else:
        ffmpeg_vcodec, quality_options = fastest_encoder(path, target_vcodec)
    tmp_path = f"{os.path.splitext(path)[0]}.tmp{new_ext}"
    ffmpeg_command = [
        ff_path.get("ffmpeg"),
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
    _progress_ffmpeg(ffmpeg_command, action, path, cancel, progress_cb, duration)
    if cancel.is_cancelled():
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


def _progress_ffmpeg(
    cmd: list,
    action: str,
    filepath: str,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
    duration: int,
) -> None:
    """
    Run ffmpeg with progress tracking using FFmpegProgressTracker.

    Args:
        cmd: FFmpeg command arguments (must include -progress pipe:1)
        action: Display label (e.g. "Remuxing" or "Re-encoding")
        filepath: Input file path (for filesize lookup)
        cancel: Cancellation token
        progress_cb: Progress callback
        duration: File duration in seconds (already probed)
    """
    filesize = os.path.getsize(filepath)
    info_dict = {
        "duration": duration,
        "filesize": filesize,
    }

    def hook(status, info):
        if cancel.is_cancelled():
            if tracker.ffmpeg_proc and tracker.ffmpeg_proc.poll() is None:
                tracker.ffmpeg_proc.kill()
            return
        status["processed_bytes"] = status.get("outputted", 0)
        status["action"] = action
        progress_cb.on_process_progress(status)

    tracker = FFmpegProgressTracker(
        info_dict,
        cmd,
        hook,
        ydl=_MinimalYDL(),
        output_filename=cmd[-1],
    )
    _, stderr, retcode = tracker.run_ffmpeg_subprocess()
    if cancel.is_cancelled():
        return
    if retcode != 0:
        raise ValueError(f"FFmpeg failed with return code {retcode}: {stderr}")
