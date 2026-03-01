from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from core.exceptions import FFmpegNoValidEncoderFound

if TYPE_CHECKING:
    from runtime.base import ProcessRunner

logger = logging.getLogger("videodl")

ENCODERS = {
    "x264": {
        "QuickSync": ("h264_qsv", ["-global_quality", "20", "-look_ahead", "1"]),
        "NVENC": (
            "h264_nvenc",
            [
                "-preset:v",
                "p7",
                "-tune:v",
                "hq",
                "-rc:v",
                "vbr",
                "-cq:v",
                "19",
                "-b:v",
                "0",
                "-profile:v",
                "high",
            ],
        ),
        "AMF": ("h264_amf", ["-quality", "quality"]),
        "Apple": ("h264_videotoolbox", ["-q:v", "35"]),
        "Raspberry": ("h264_v4l2m2m", []),
        "MediaCodec": ("h264_mediacodec", ["-b:v", "8M"]),
        "CPU": ("libx264", ["-crf", "20"]),
    },
    "x265": {
        "QuickSync": ("hevc_qsv", ["-global_quality", "20", "-look_ahead", "1"]),
        "NVENC": (
            "hevc_nvenc",
            [
                "-preset:v",
                "p7",
                "-tune:v",
                "hq",
                "-rc:v",
                "vbr",
                "-cq:v",
                "19",
                "-b:v",
                "0",
                "-profile:v",
                "high",
            ],
        ),
        "AMF": ("hevc_amf", ["-quality", "quality"]),
        "Apple": ("hevc_videotoolbox", ["-q:v", "35"]),
        "Raspberry": ("hevc_v4l2m2m", []),
        "MediaCodec": ("hevc_mediacodec", ["-b:v", "6M"]),
        "CPU": ("libx265", ["-crf", "20"]),
    },
    "ProRes": {
        "QuickSync": (None, []),
        "NVENC": (None, []),
        "AMF": (None, []),
        "Apple": ("prores_videotoolbox", ["-profile:v", "0", "-qscale:v", "4"]),
        "Raspberry": (None, []),
        "MediaCodec": (None, []),
        "CPU": ("prores_ks", ["-profile:v", "0", "-qscale:v", "4"]),
    },
    "AV1": {
        "QuickSync": ("av1_qsv", []),
        "NVENC": ("av1_nvenc", []),
        "AMF": (None, []),
        "Apple": (None, []),
        "MediaCodec": (None, []),
        "CPU": ("libsvtav1", ["-crf", "23"]),
    },
}

# Cache: set of encoder names available in this ffmpeg build, populated once
_available_encoders = None


def _get_available_encoders(
    ff_path: dict[str, str] | None = None,
    process_runner: ProcessRunner | None = None,
) -> set[str]:
    """Parse `ffmpeg -encoders` once and cache the set of available encoder names."""
    global _available_encoders
    if _available_encoders is not None:
        return _available_encoders

    _available_encoders = set()
    try:
        if ff_path is None:
            from sys_vars import FF_PATH

            ff_path = FF_PATH
        ffmpeg_path = ff_path.get("ffmpeg", "ffmpeg")
        args = [ffmpeg_path, "-encoders", "-hide_banner"]

        if process_runner is not None:
            result = process_runner.run(args, capture_output=True, text=True, timeout=10)
            stdout = result.stdout
        else:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
            stdout = r.stdout

        for line in stdout.splitlines():
            # Format: " V....D h264_nvenc  NVIDIA NVENC ..."
            # 6 flag chars, then space, then encoder name
            parts = line.strip().split()
            if len(parts) >= 2 and len(parts[0]) == 6:
                _available_encoders.add(parts[1])
    except Exception as e:
        logger.warning(f"Could not query ffmpeg encoders: {e}")

    logger.info(f"Available encoders: {sorted(_available_encoders)}")
    return _available_encoders


def fastest_encoder(path: str, target_vcodec: str) -> tuple[str, list[str]]:
    """
    Determine the best hardware encoder for the target codec by checking
    which encoders are available in the current ffmpeg build.

    Falls back to CPU (software) encoding if no hardware encoder is found.

    Args:
        path: Path to the input file (unused, kept for API compat)
        target_vcodec: Target video codec ("x264", "x265", "ProRes", "AV1")

    Returns:
        Tuple of (encoder_name, quality_options)

    Raises:
        FFmpegNoValidEncoderFound: If no encoder is available for the target
    """
    available = _get_available_encoders()
    for platform_name, (vcodec, quality_options) in ENCODERS[target_vcodec].items():  # type: ignore[attr-defined]
        if not vcodec:
            continue
        if vcodec in available:
            logger.info(f"Selected encoder: {vcodec} ({platform_name}) for {target_vcodec}")
            return vcodec, quality_options
    raise FFmpegNoValidEncoderFound
