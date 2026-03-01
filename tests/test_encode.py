import json
import os
import signal
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock heavy dependencies before importing
_mock_lang = MagicMock()
_mock_lang.GuiField = MagicMock()
_mock_lang.get_text = MagicMock(side_effect=lambda field: f"text_{field}")

for mod in ["sys_vars", "i18n", "i18n.lang", "yt_dlp.postprocessor.ffmpeg", "core.hwaccel"]:
    sys.modules[mod] = MagicMock()
sys.modules["i18n.lang"] = _mock_lang

# Force reimport in case another test mocked the module
sys.modules.pop("core.encode", None)

from core.encode import (  # noqa: E402, I001
    NLE_COMPATIBLE_ACODECS,
    NLE_COMPATIBLE_VCODECS,
    _TARGET_TO_VCODEC_NAME,
    _VCODEC_NAME_TO_TARGET,
    _adapt_crf,
    _ffmpeg_video,
    _progress_ffmpeg,
    ffprobe,
    needs_reencode,
    post_process_dl,
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


# ---------------------------------------------------------------------------
# Phase 1 — _adapt_crf (pure function)
# ---------------------------------------------------------------------------
class TestAdaptCrf:
    def test_no_crf_flag_returns_unchanged(self):
        opts = ["-preset", "fast", "-b:v", "0"]
        assert _adapt_crf(opts, 1080) == opts

    def test_high_res_decreases_crf(self):
        result = _adapt_crf(["-crf", "20"], 1440)
        assert result == ["-crf", "18"]

    def test_high_res_clamps_at_15(self):
        result = _adapt_crf(["-crf", "16"], 2160)
        assert result == ["-crf", "15"]

    def test_low_res_increases_crf(self):
        result = _adapt_crf(["-crf", "20"], 720)
        assert result == ["-crf", "23"]

    def test_low_res_clamps_at_30(self):
        result = _adapt_crf(["-crf", "28"], 480)
        assert result == ["-crf", "30"]

    def test_mid_res_unchanged(self):
        result = _adapt_crf(["-crf", "20"], 1080)
        assert result == ["-crf", "20"]

    def test_boundary_721_is_mid(self):
        result = _adapt_crf(["-crf", "20"], 721)
        assert result == ["-crf", "20"]

    def test_boundary_1081_is_high(self):
        result = _adapt_crf(["-crf", "20"], 1081)
        assert result == ["-crf", "18"]

    def test_crf_not_first(self):
        result = _adapt_crf(["-preset", "slow", "-crf", "20"], 480)
        assert result == ["-preset", "slow", "-crf", "23"]

    def test_returns_copy_not_mutation(self):
        original = ["-crf", "20"]
        result = _adapt_crf(original, 1080)
        assert result is not original


# ---------------------------------------------------------------------------
# Phase 2 — ffprobe
# ---------------------------------------------------------------------------
class TestFfprobe:
    def test_success_parses_json(self):
        probe_json = json.dumps({
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
            "format": {"duration": "120.5"},
        })
        with patch("core.encode.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = (probe_json.encode("utf-8"), b"")
            proc.returncode = 0
            mock_popen.return_value = proc
            result = ffprobe("/tmp/test.mp4")
        assert result["streams"][0]["codec_name"] == "h264"
        assert result["format"]["duration"] == "120.5"

    def test_failure_raises_value_error(self):
        with patch("core.encode.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = (b"", b"error msg")
            proc.returncode = 1
            mock_popen.return_value = proc
            with pytest.raises(ValueError):
                ffprobe("/tmp/test.mp4")

    def test_custom_cmd_path(self):
        probe_json = json.dumps({"streams": [], "format": {}})
        with patch("core.encode.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = (probe_json.encode("utf-8"), b"")
            proc.returncode = 0
            mock_popen.return_value = proc
            ffprobe("/tmp/test.mp4", cmd="/usr/local/bin/ffprobe")
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/local/bin/ffprobe"

    def test_with_process_runner_success(self):
        probe_json = json.dumps({"streams": [], "format": {}})
        runner = MagicMock()
        runner.popen_communicate.return_value = MagicMock(
            returncode=0, stdout=probe_json, stderr=""
        )
        result = ffprobe("/tmp/test.mp4", process_runner=runner)
        assert result == {"streams": [], "format": {}}

    def test_with_process_runner_failure(self):
        runner = MagicMock()
        runner.popen_communicate.return_value = MagicMock(
            returncode=1, stdout="", stderr="error"
        )
        with pytest.raises(ValueError):
            ffprobe("/tmp/test.mp4", process_runner=runner)


# ---------------------------------------------------------------------------
# Phase 3 — _ffmpeg_video command construction
# ---------------------------------------------------------------------------
class TestFfmpegVideoCommand:
    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    @patch("core.encode.fastest_encoder", return_value=("libx264", ["-crf", "20"]))
    def test_reencode_basic(self, mock_enc, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.webm", False, False, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        cmd = mock_prog.call_args[0][0]
        assert "-c:v" in cmd
        idx = cmd.index("-c:v")
        assert cmd[idx + 1] == "libx264"
        assert "-c:a" in cmd
        idx_a = cmd.index("-c:a")
        assert cmd[idx_a + 1] == "aac"
        assert "-movflags" in cmd
        assert cmd[-1].endswith(".tmp.mp4")

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    def test_remux_copy(self, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.mp4", True, True, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        cmd = mock_prog.call_args[0][0]
        idx_v = cmd.index("-c:v")
        assert cmd[idx_v + 1] == "copy"
        idx_a = cmd.index("-c:a")
        assert cmd[idx_a + 1] == "copy"

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    def test_prores_mov_extension(self, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.mp4", True, True, 1080, "ProRes",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        cmd = mock_prog.call_args[0][0]
        assert cmd[-1].endswith(".tmp.mov")
        assert "-movflags" not in cmd
        assert "-profile:v" in cmd

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    @patch("core.encode.fastest_encoder", return_value=("h264_mediacodec", ["-b:v", "8M"]))
    def test_mediacodec_hwaccel(self, mock_enc, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.webm", True, False, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        cmd = mock_prog.call_args[0][0]
        assert "-hwaccel" in cmd
        idx = cmd.index("-hwaccel")
        assert cmd[idx + 1] == "mediacodec"

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    def test_cancel_removes_tmp(self, mock_isfile, mock_rm, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = True
        _ffmpeg_video(
            "/tmp/video.mp4", True, True, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        mock_rm.assert_called_once()
        assert mock_rm.call_args[0][0].endswith(".tmp.mp4")

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.path.isfile", return_value=False)
    def test_output_missing_raises(self, mock_isfile, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        with pytest.raises(FileNotFoundError):
            _ffmpeg_video(
                "/tmp/video.mp4", True, True, 1080, "x264",
                cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
            )

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    def test_success_removes_original_and_renames(self, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.mp4", True, True, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        mock_rm.assert_called_once_with("/tmp/video.mp4")
        mock_rename.assert_called_once()
        assert mock_rename.call_args[1]["dst"] == "/tmp/video.mp4"

    @patch("core.encode._progress_ffmpeg")
    @patch("core.encode.os.rename")
    @patch("core.encode.os.remove")
    @patch("core.encode.os.path.isfile", return_value=True)
    def test_stream_mapping(self, mock_isfile, mock_rm, mock_rename, mock_prog):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _ffmpeg_video(
            "/tmp/video.mp4", True, True, 1080, "x264",
            cancel, MagicMock(), 120, {"ffmpeg": "ffmpeg"},
        )
        cmd = mock_prog.call_args[0][0]
        map_indices = [i for i, v in enumerate(cmd) if v == "-map"]
        assert len(map_indices) == 2
        assert cmd[map_indices[0] + 1] == "0:v:0"
        assert cmd[map_indices[1] + 1] == "0:a:0"


# ---------------------------------------------------------------------------
# Phase 4 — post_process_dl orchestration
# ---------------------------------------------------------------------------
def _fake_probe(vcodec="h264", acodec="aac", width=1920, height=1080, duration=120):
    return {
        "streams": [
            {"codec_type": "video", "codec_name": vcodec, "width": width, "height": height},
            {"codec_type": "audio", "codec_name": acodec},
        ],
        "format": {"duration": str(duration)},
    }


class TestPostProcessDl:
    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe")
    def test_best_returns_immediately(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "Best", cancel, MagicMock())
        mock_probe.assert_not_called()
        mock_ffmpeg.assert_not_called()

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe())
    def test_original_remux_only(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "Original", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        _, kwargs = mock_ffmpeg.call_args
        # vcodec_is_target=True, acodec_nle_friendly=True (copy both)
        assert mock_ffmpeg.call_args[0][1] is True   # acodec_nle_friendly
        assert mock_ffmpeg.call_args[0][2] is True   # vcodec_is_target

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe(vcodec="h264", acodec="aac"))
    def test_nle_compatible_video_remux(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "NLE", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        assert mock_ffmpeg.call_args[0][2] is True   # vcodec_is_target (remux)

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe(vcodec="vp9", acodec="aac"))
    def test_nle_incompatible_video_reencodes(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "NLE", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        assert mock_ffmpeg.call_args[0][2] is False   # vcodec_is_target (reencode)
        assert mock_ffmpeg.call_args[0][4] == "x264"  # target_vcodec

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe(vcodec="h264", acodec="opus"))
    def test_nle_incompatible_audio(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "NLE", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        assert mock_ffmpeg.call_args[0][1] is False   # acodec_nle_friendly

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe(vcodec="h264", acodec="aac"))
    def test_direct_target_different_codec(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "x265", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        assert mock_ffmpeg.call_args[0][2] is False   # vcodec_is_target (h264 != x265)
        assert mock_ffmpeg.call_args[0][4] == "x265"

    @patch("core.encode._ffmpeg_video")
    @patch("core.encode.ffprobe", return_value=_fake_probe(vcodec="hevc", acodec="aac"))
    def test_direct_target_same_codec(self, mock_probe, mock_ffmpeg):
        cancel = MagicMock()
        post_process_dl("/tmp/video.mp4", "x265", cancel, MagicMock(), {"ffprobe": "ffprobe"})
        assert mock_ffmpeg.call_args[0][2] is True   # vcodec_is_target (hevc == x265)


# ---------------------------------------------------------------------------
# Phase 6 — _progress_ffmpeg
# ---------------------------------------------------------------------------
class TestProgressFfmpeg:
    @patch("core.encode.FFmpegProgressTracker")
    @patch("core.encode.os.path.getsize", return_value=1000000)
    def test_tracker_called(self, mock_getsize, mock_tracker_cls):
        tracker = MagicMock()
        tracker.run_ffmpeg_subprocess.return_value = ("", "", 0)
        mock_tracker_cls.return_value = tracker
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        _progress_ffmpeg(
            ["ffmpeg", "-i", "in.mp4", "-progress", "pipe:1", "-y", "out.mp4"],
            "Remuxing", "/tmp/in.mp4", cancel, MagicMock(), 120,
        )
        mock_tracker_cls.assert_called_once()
        tracker.run_ffmpeg_subprocess.assert_called_once()

    @patch("core.encode.FFmpegProgressTracker")
    @patch("core.encode.os.path.getsize", return_value=1000000)
    def test_nonzero_retcode_raises(self, mock_getsize, mock_tracker_cls):
        tracker = MagicMock()
        tracker.run_ffmpeg_subprocess.return_value = ("", "error output", 1)
        mock_tracker_cls.return_value = tracker
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        with pytest.raises(ValueError, match="FFmpeg failed"):
            _progress_ffmpeg(
                ["ffmpeg", "-i", "in.mp4", "-progress", "pipe:1", "-y", "out.mp4"],
                "Remuxing", "/tmp/in.mp4", cancel, MagicMock(), 120,
            )
