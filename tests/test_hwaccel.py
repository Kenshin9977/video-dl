import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock heavy dependencies before importing
for mod in ["sys_vars", "i18n", "i18n.lang"]:
    sys.modules[mod] = MagicMock()

# Provide FF_PATH so the module can import
sys.modules["sys_vars"].FF_PATH = {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}  # type: ignore[attr-defined]

# Force reimport in case another test mocked the module
for mod in ["core.exceptions", "core.hwaccel"]:
    sys.modules.pop(mod, None)

from typing import Any  # noqa: E402

import core.hwaccel as hwaccel  # noqa: E402
from core.exceptions import FFmpegNoValidEncoderFound  # noqa: E402
from core.hwaccel import ENCODERS as _ENCODERS  # noqa: E402
from core.hwaccel import _get_available_encoders, fastest_encoder  # noqa: E402

ENCODERS: dict[str, dict[str, Any]] = _ENCODERS  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def reset_encoder_cache():
    """Reset the global encoder cache before each test."""
    hwaccel._available_encoders = None  # type: ignore[assignment]
    yield
    hwaccel._available_encoders = None  # type: ignore[assignment]


SAMPLE_FFMPEG_OUTPUT = """\
Encoders:
 V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
 V..... libx265              libx265 H.265 / HEVC
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder
 V..... hevc_nvenc           NVIDIA NVENC H.265 encoder
 V..... libsvtav1            SVT-AV1 encoder
 V..... prores_ks            Apple ProRes (iCodec Pro)
"""


class TestGetAvailableEncoders:
    def test_parses_ffmpeg_output(self):
        mock_result = MagicMock()
        mock_result.stdout = SAMPLE_FFMPEG_OUTPUT
        with patch("core.hwaccel.subprocess.run", return_value=mock_result):
            result = _get_available_encoders()
        assert "libx264" in result
        assert "h264_nvenc" in result
        assert "libx265" in result
        assert "hevc_nvenc" in result
        assert "libsvtav1" in result
        assert "prores_ks" in result

    def test_caches_result(self):
        mock_result = MagicMock()
        mock_result.stdout = SAMPLE_FFMPEG_OUTPUT
        with patch("core.hwaccel.subprocess.run", return_value=mock_result) as mock_run:
            _get_available_encoders()
            _get_available_encoders()
        mock_run.assert_called_once()

    def test_returns_empty_on_failure(self):
        with patch("core.hwaccel.subprocess.run", side_effect=Exception("ffmpeg not found")):
            result = _get_available_encoders()
        assert result == set()


class TestFastestEncoder:
    def test_selects_hw_encoder_over_cpu(self):
        hwaccel._available_encoders = {"h264_nvenc", "libx264"}
        encoder, opts = fastest_encoder("dummy.mp4", "x264")
        assert encoder == "h264_nvenc"

    def test_falls_back_to_cpu(self):
        hwaccel._available_encoders = {"libx264"}
        encoder, opts = fastest_encoder("dummy.mp4", "x264")
        assert encoder == "libx264"

    def test_raises_when_no_encoder(self):
        hwaccel._available_encoders = set()
        with pytest.raises(FFmpegNoValidEncoderFound):
            fastest_encoder("dummy.mp4", "x264")

    def test_skips_none_entries(self):
        """ProRes has None for QuickSync/NVENC/AMF — should skip them."""
        hwaccel._available_encoders = {"prores_ks"}
        encoder, opts = fastest_encoder("dummy.mp4", "ProRes")
        assert encoder == "prores_ks"

    def test_prores_no_hw_raises(self):
        hwaccel._available_encoders = set()
        with pytest.raises(FFmpegNoValidEncoderFound):
            fastest_encoder("dummy.mp4", "ProRes")


class TestEncodersStructure:
    def test_every_target_has_cpu_fallback(self):
        for target, platforms in ENCODERS.items():
            assert "CPU" in platforms, f"{target} missing CPU fallback"
            cpu_encoder, _ = platforms["CPU"]
            assert cpu_encoder is not None, f"{target} CPU encoder is None"

    def test_all_entries_are_tuples(self):
        for target, platforms in ENCODERS.items():
            for platform_name, entry in platforms.items():
                assert isinstance(entry, tuple), f"ENCODERS[{target!r}][{platform_name!r}] is not a tuple"
                assert len(entry) == 2, f"ENCODERS[{target!r}][{platform_name!r}] should be (encoder, options)"
                encoder, options = entry
                assert encoder is None or isinstance(encoder, str)
                assert isinstance(options, list)
