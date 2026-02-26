import sys
from unittest.mock import MagicMock

import pytest

# Mock heavy dependencies before importing
for mod in ["sys_vars", "i18n", "i18n.lang", "yt_dlp.postprocessor.ffmpeg", "core.hwaccel"]:
    sys.modules[mod] = MagicMock()

# Force reimport in case another test mocked the module
sys.modules.pop("core.encode", None)

from core.encode import (  # noqa: E402, I001
    NLE_COMPATIBLE_ACODECS,
    NLE_COMPATIBLE_VCODECS,
    _TARGET_TO_VCODEC_NAME,
    _VCODEC_NAME_TO_TARGET,
    needs_reencode,
)


class TestNeedsReencode:
    @pytest.mark.parametrize(
        ("vcodec", "acodec", "expected"),
        [
            ("h264", "aac", (False, False)),
            ("avc1", "mp3", (False, False)),
            ("hevc", "pcm_s16le", (False, False)),
            ("h265", "pcm_s24le", (False, False)),
            ("prores", "aac", (False, False)),
            ("vp9", "aac", (True, False)),
            ("av1", "aac", (True, False)),
            ("h264", "opus", (False, True)),
            ("h264", "vorbis", (False, True)),
            ("av1", "opus", (True, True)),
            ("vp9", "vorbis", (True, True)),
        ],
    )
    def test_codec_combinations(self, vcodec, acodec, expected):
        assert needs_reencode(vcodec, acodec) == expected

    def test_case_insensitive(self):
        assert needs_reencode("H264", "AAC") == (False, False)
        assert needs_reencode("HEVC", "MP3") == (False, False)
        assert needs_reencode("ProRes", "PCM_S16LE") == (False, False)


class TestCodecMappings:
    def test_vcodec_name_to_target_covers_all_compatible(self):
        """Every NLE-compatible video codec has a target mapping."""
        for codec in NLE_COMPATIBLE_VCODECS:
            assert codec in _VCODEC_NAME_TO_TARGET, f"{codec} missing from _VCODEC_NAME_TO_TARGET"

    def test_target_to_vcodec_name_nle_entries_consistent(self):
        """NLE-compatible entries in the inverse map are consistent with the forward map."""
        for target, vcodec_name in _TARGET_TO_VCODEC_NAME.items():
            if vcodec_name in _VCODEC_NAME_TO_TARGET:
                assert _VCODEC_NAME_TO_TARGET[vcodec_name] == target

    def test_target_to_vcodec_name_all_values_are_strings(self):
        for target, vcodec_name in _TARGET_TO_VCODEC_NAME.items():
            assert isinstance(target, str)
            assert isinstance(vcodec_name, str)

    def test_nle_compatible_vcodecs_are_lowercase(self):
        for codec in NLE_COMPATIBLE_VCODECS:
            assert codec == codec.lower()

    def test_nle_compatible_acodecs_are_lowercase(self):
        for codec in NLE_COMPATIBLE_ACODECS:
            assert codec == codec.lower()
