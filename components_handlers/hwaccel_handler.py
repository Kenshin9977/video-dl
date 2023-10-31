import os
import subprocess

from sys_vars import FF_PATH
from utils.sys_utils import check_cmd_output
from videodl_exceptions import FFmpegNoValidEncoderFound, FileAlreadyInUse

ENCODERS = {
    "x264": {
        "QuickSync": (
            "h264_qsv", ["-global_quality", "20", "-look_ahead", "1"]
            ),
        "NVENC": (
            "h264_nvenc", [
                "-preset:v",
                "p7",
                "-tune:v",
                "hq",
                "-rc:v",
                "vbr",
                "-cq:v 19",
                "-b:v 0",
                ",-profile:v",
                "high"
                ]
            ),
        "AMF": ("h264_amf", ["-quality", "quality"]),
        "Apple": ("h264_videotoolbox", ["-q:v", "35"]),
        # doc lacking, might need to change the number
        # https://trac.ffmpeg.org/wiki/HWAccelIntro#VideoToolbox
        "Raspberry": ("h264_v4l2m2m", []),
        "CPU": ("libx264", ["-crf", "20"]),
    },
    "x265": {
        "QuickSync": (
            "hevc_qsv", ["-global_quality", "20", "-look_ahead", "1"]
            ),
        "NVENC": (
            "hevc_nvenc", [
                "-preset:v",
                "p7",
                "-tune:v",
                "hq",
                "-rc:v",
                "vbr",
                "-cq:v 19",
                "-b:v 0",
                ",-profile:v",
                "high"
                ]
            ),
        "AMF": ("hevc_amf", ["-quality", "quality"]),
        "Apple": ("hevc_videotoolbox", ["-q:v", "35"]),
        "Raspberry": ("hevc_v4l2m2m", []),
        "CPU": ("libx265", ["-crf", "20"]),
    },
    "ProRes": {
        "QuickSync": (None, []),
        "NVENC": (None, []),
        "AMF": (None, []),
        "Apple": (
            "prores_videotoolbox", ["-profile:v", "0", "-qscale:v", "4"]
            ),
        "Raspberry": (None, []),
        "CPU": ("prores_ks", ["-profile:v", "0", "-qscale:v", "4"]),
    },
    "AV1": {
        "QuickSync": ("av1_qsv", []),
        "NVENC": ("av1_nvenc", []),
        "AMF": (None, []),
        "Apple": (None, []),
        "CPU": ("libsvtav1", ["-crf", "23"]),
    },
}


def fastest_encoder(path: str, target_vcodec: str) -> tuple[str, str]:
    """
    Determine the fastest encoder by trying to encode 1 frame with each
    possible encoder for the targeted video codec. As soon as one works it is
    considered the fastest as it's pretty rare to have multiple hardware
    encoders and the difference in speed/quality is often negligible.
    The CPU is the fallback option as it's a universal solution altough the
    slowest.

    Args:
        path (str): path to the file used to test the codecs
        target_vcodec (str): Video codec to encode to

    Raises:
        ffmpeg.Error: If no compatible codec was found

    Returns:
        str: Fastest compatible codec
    """
    file_name_ext = os.path.splitext(path)
    new_ext = ".mp4" if target_vcodec != "ProRes" else ".mov"
    output_path = f"{file_name_ext[0]}.tmp{new_ext}"
    vcodecs = ENCODERS[target_vcodec].values()
    ffmpeg_output_args = [output_path, "-y", "-loglevel", "error"]
    for vcodec, ffmpeg_quality_options in vcodecs:
        if not vcodec:
            continue
        try:
            ffmpeg_basic_args = [
                FF_PATH.get("ffmpeg"),
                "-hide_banner",
                "-i",
                path,
                "-frames:v",
                "1",
                "-c:v",
                vcodec
            ]
            check_cmd_output(
                ffmpeg_basic_args + ffmpeg_quality_options + ffmpeg_output_args
            )
        except subprocess.CalledProcessError:
            continue
        try:
            if os.path.isfile(output_path):
                os.remove(path=output_path)
        except PermissionError:
            raise FileAlreadyInUse
        return vcodec, ffmpeg_quality_options
    raise FFmpegNoValidEncoderFound
