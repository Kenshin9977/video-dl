from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

import runtime
from core.exceptions import FFmpegNoValidEncoderFound

if TYPE_CHECKING:
    from runtime.base import ProcessRunner

logger = logging.getLogger("videodl")

ENCODERS = {
    "x264": {
        "NVENC": (
            "h264_nvenc",
            ["-preset:v", "p7", "-tune:v", "hq", "-rc:v", "vbr", "-cq:v", "23", "-b:v", "0", "-profile:v", "high"],
        ),
        "AMF": ("h264_amf", ["-quality", "quality"]),
        "QuickSync": ("h264_qsv", ["-global_quality", "23", "-look_ahead", "1"]),
        "Apple": ("h264_videotoolbox", ["-q:v", "35"]),
        "Raspberry": ("h264_v4l2m2m", []),
        "MediaCodec": ("h264_mediacodec", ["-b:v", "8M"]),
        "CPU": ("libx264", ["-crf", "23"]),
    },
    "x265": {
        "NVENC": (
            "hevc_nvenc",
            ["-preset:v", "p7", "-tune:v", "hq", "-rc:v", "vbr", "-cq:v", "26", "-b:v", "0"],
        ),
        "AMF": ("hevc_amf", ["-quality", "quality"]),
        "QuickSync": ("hevc_qsv", ["-global_quality", "26", "-look_ahead", "1"]),
        "Apple": ("hevc_videotoolbox", ["-q:v", "40"]),
        "Raspberry": ("hevc_v4l2m2m", []),
        "MediaCodec": ("hevc_mediacodec", ["-b:v", "6M"]),
        "CPU": ("libx265", ["-crf", "26"]),
    },
    "ProRes": {
        "NVENC": (None, []),
        "AMF": (None, []),
        "QuickSync": (None, []),
        "Apple": ("prores_videotoolbox", ["-profile:v", "0", "-qscale:v", "9"]),
        "Raspberry": (None, []),
        "MediaCodec": (None, []),
        "CPU": ("prores_ks", ["-profile:v", "0", "-qscale:v", "9"]),
    },
    "AV1": {
        "NVENC": ("av1_nvenc", ["-preset", "p7", "-cq:v", "37"]),
        "AMF": (None, []),
        "QuickSync": ("av1_qsv", ["-preset", "quality", "-global_quality", "32"]),
        "Apple": (None, []),
        "MediaCodec": (None, []),
        "CPU": ("libsvtav1", ["-crf", "32", "-preset", "6"]),
    },
}

# Cache: set of encoder names available in this ffmpeg build, populated once
_available_encoders = None
# Cache: set of encoder names that passed the functional test
_working_encoders: dict[str, bool] = {}


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


def _test_encoder(encoder: str, ff_path: dict[str, str] | None = None) -> bool:
    """Run a 1-frame test encode to verify the encoder actually works at runtime."""
    if encoder in _working_encoders:
        return _working_encoders[encoder]
    if ff_path is None:
        try:
            from sys_vars import FF_PATH

            ff_path = FF_PATH
        except Exception:
            ff_path = {}
    ffmpeg_path = (ff_path or {}).get("ffmpeg", "ffmpeg")
    try:
        r = subprocess.run(
            [
                ffmpeg_path,
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x240:rate=25:duration=3",
                "-vf",
                "format=nv12",
                "-c:v",
                encoder,
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            timeout=20,
        )
        result = r.returncode == 0
        if not result:
            logger.debug(f"Encoder {encoder} test stderr:\n{r.stderr.decode('utf-8', errors='replace')}")
    except Exception as ex:
        result = False
        logger.debug(f"Encoder {encoder} test exception: {ex}")
    _working_encoders[encoder] = result
    if not result:
        logger.info(f"Encoder {encoder} failed functional test, skipping")
    return result


def fastest_encoder(target_vcodec: str) -> tuple[str, list[str]]:
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
    skip_platforms = {"Raspberry"} if runtime.is_android() else set()
    for platform_name, (vcodec, quality_options) in ENCODERS[target_vcodec].items():  # type: ignore[attr-defined]
        if not vcodec:
            continue
        if platform_name in skip_platforms:
            continue
        if vcodec in available and _test_encoder(vcodec):
            logger.info(f"Selected encoder: {vcodec} ({platform_name}) for {target_vcodec}")
            return vcodec, quality_options
    raise FFmpegNoValidEncoderFound
