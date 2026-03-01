from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock heavy dependencies BEFORE importing core.download
# ---------------------------------------------------------------------------
_mock_lang = MagicMock()
_mock_lang.GuiField = MagicMock()
_mock_lang.get_text = MagicMock(side_effect=lambda field: f"text_{field}")

class _FakeYtdlpDownloadCancelled(Exception):
    pass

_mock_yt_utils = MagicMock()
_mock_yt_utils.DownloadCancelled = _FakeYtdlpDownloadCancelled

for _mod in [
    "yt_dlp",
    "yt_dlp.YoutubeDL",
    "yt_dlp.postprocessor",
    "yt_dlp.postprocessor.FFmpegPostProcessor",
    "yt_dlp.postprocessor.ffmpeg",
    "core.hwaccel",
    "i18n",
    "i18n.lang",
    "sys_vars",
]:
    sys.modules[_mod] = MagicMock()

sys.modules["yt_dlp.utils"] = _mock_yt_utils
sys.modules["i18n.lang"] = _mock_lang

# Force reimport so the module picks up our mocks
sys.modules.pop("core.download", None)

from core.download import (  # noqa: E402
    _STATUS_PATTERNS,
    _StallDetector,
    _YdlUiLogger,
    _finish_download,
    _get_child_pids,
    _kill_new_children,
    download,
    post_download,
    MAX_RETRIES,
)
from core.exceptions import DownloadCancelled, DownloadTimeout, PlaylistNotFound  # noqa: E402

# GF members are MagicMock attributes — build a lookup by identity
_GF = _mock_lang.GuiField
_FIELD_BY_MOCK = {
    _GF.extracting_cookies: "extracting_cookies",
    _GF.solving_js: "solving_js",
    _GF.fetching_info: "fetching_info",
}


def _make_config(audio_only=False, target_vcodec="NLE", ff_path=None):
    """Build a mock DownloadConfig-like object."""
    config = MagicMock()
    config.audio_only = audio_only
    config.target_vcodec = target_vcodec
    config.ff_path = ff_path or {}
    return config


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestStatusPatterns:
    """Validate _STATUS_PATTERNS regex matching."""

    @pytest.mark.parametrize(
        ("log_msg", "expected_name"),
        [
            ("Extracting cookies from Chrome", "extracting_cookies"),
            ("[cookies] Extracting Cookies from firefox", "extracting_cookies"),
            ("Solving JS challenge for player", "solving_js"),
            ("Extracting URL https://example.com", "fetching_info"),
            ("Downloading webpage", "fetching_info"),
            ("Downloading player API JSON", "fetching_info"),
        ],
    )
    def test_pattern_matches_expected_field(self, log_msg, expected_name):
        matched = False
        for pattern, gui_field in _STATUS_PATTERNS:
            if pattern.search(log_msg):
                assert _FIELD_BY_MOCK.get(gui_field) == expected_name
                matched = True
                break
        assert matched, f"No pattern matched: {log_msg!r}"

    @pytest.mark.parametrize(
        "log_msg",
        [
            "Starting download of video",
            "Merging formats into mkv",
            "[download] 50.0% of 100MiB",
            "Writing video metadata",
        ],
    )
    def test_no_false_positives(self, log_msg):
        for pattern, _ in _STATUS_PATTERNS:
            assert not pattern.search(log_msg), f"Unexpected match for: {log_msg!r}"

    def test_all_patterns_are_case_insensitive(self):
        import re

        for pattern, _ in _STATUS_PATTERNS:
            assert pattern.flags & re.IGNORECASE


class TestYdlUiLogger:
    """Test _YdlUiLogger bridges log messages to StatusCallback correctly."""

    def _make_logger(self):
        status_cb = MagicMock()
        return _YdlUiLogger(status_cb), status_cb

    def test_debug_matching_updates_status(self):
        logger, status_cb = self._make_logger()
        logger.debug("Extracting cookies from Chrome")
        status_cb.on_status.assert_called_once()

    def test_info_matching_updates_status(self):
        logger, status_cb = self._make_logger()
        logger.info("Downloading webpage")
        status_cb.on_status.assert_called_once()

    def test_debug_non_matching_no_update(self):
        logger, status_cb = self._make_logger()
        logger.debug("Some random debug message")
        status_cb.on_status.assert_not_called()

    def test_warning_does_not_update_status(self):
        logger, status_cb = self._make_logger()
        logger.warning("Extracting cookies from Chrome")
        status_cb.on_status.assert_not_called()

    def test_error_does_not_update_status(self):
        logger, status_cb = self._make_logger()
        logger.error("Extracting cookies from Chrome")
        status_cb.on_status.assert_not_called()


class TestFinishDownload:
    """Test _finish_download branching logic."""

    def test_none_raises_playlist_not_found(self):
        cancel = MagicMock()
        progress_cb = MagicMock()
        config = _make_config()
        with pytest.raises(PlaylistNotFound):
            _finish_download(MagicMock(), None, config, cancel, progress_cb)

    def test_audio_only_returns_early(self):
        cancel = MagicMock()
        progress_cb = MagicMock()
        config = _make_config(audio_only=True)
        _finish_download(MagicMock(), {"_type": "video"}, config, cancel, progress_cb)
        progress_cb.on_download_progress.assert_not_called()

    @patch("core.download.post_download")
    def test_single_video_updates_progress(self, mock_pd):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        progress_cb = MagicMock()
        config = _make_config()
        _finish_download(MagicMock(), {"_type": "video", "ext": "mp4"}, config, cancel, progress_cb)
        progress_cb.on_download_progress.assert_called()

    @patch("core.download.post_download")
    def test_playlist_iterates_entries(self, mock_pd):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        progress_cb = MagicMock()
        config = _make_config()
        entries = [{"ext": "mp4"}, {"ext": "webm"}]
        _finish_download(MagicMock(), {"_type": "playlist", "entries": entries}, config, cancel, progress_cb)
        progress_cb.on_download_progress.assert_called()

    @patch("core.download.post_download")
    def test_cancel_during_playlist_raises(self, mock_pd):
        cancel = MagicMock()
        cancel.is_cancelled.side_effect = [False, True]
        progress_cb = MagicMock()
        config = _make_config()
        entries = [{"ext": "mp4"}, {"ext": "webm"}]
        with pytest.raises(DownloadCancelled):
            _finish_download(MagicMock(), {"_type": "playlist", "entries": entries}, config, cancel, progress_cb)


# ---------------------------------------------------------------------------
# Phase 1 — _StallDetector
# ---------------------------------------------------------------------------
class TestStallDetector:
    def test_not_stalled_just_after_creation(self):
        sd = _StallDetector(stall_timeout=10)
        assert sd.is_stalled() is False

    @patch("core.download.time")
    def test_stalled_after_timeout(self, mock_time):
        mock_time.monotonic.return_value = 0.0
        sd = _StallDetector(stall_timeout=10)
        mock_time.monotonic.return_value = 11.0
        assert sd.is_stalled() is True

    @patch("core.download.time")
    def test_not_stalled_at_exact_boundary(self, mock_time):
        mock_time.monotonic.return_value = 0.0
        sd = _StallDetector(stall_timeout=10)
        mock_time.monotonic.return_value = 10.0
        assert sd.is_stalled() is False

    @patch("core.download.time")
    def test_tick_resets_timer(self, mock_time):
        mock_time.monotonic.return_value = 0.0
        sd = _StallDetector(stall_timeout=10)
        mock_time.monotonic.return_value = 9.0
        sd.tick()  # reset at t=9
        mock_time.monotonic.return_value = 18.0
        assert sd.is_stalled() is False  # only 9s since tick
        mock_time.monotonic.return_value = 20.0
        assert sd.is_stalled() is True   # 11s since tick

    @patch("core.download.time")
    def test_custom_timeout(self, mock_time):
        mock_time.monotonic.return_value = 0.0
        sd = _StallDetector(stall_timeout=5)
        mock_time.monotonic.return_value = 6.0
        assert sd.is_stalled() is True

    @patch("core.download.time")
    def test_tick_then_stall(self, mock_time):
        mock_time.monotonic.return_value = 0.0
        sd = _StallDetector(stall_timeout=10)
        mock_time.monotonic.return_value = 5.0
        sd.tick()
        mock_time.monotonic.return_value = 5.0
        assert sd.is_stalled() is False


# ---------------------------------------------------------------------------
# Phase 2 — _get_child_pids
# ---------------------------------------------------------------------------
class TestGetChildPids:
    @patch("core.download.subprocess.check_output", return_value="1234\n5678\n")
    def test_parses_normal_output(self, mock_check):
        result = _get_child_pids()
        assert result == {1234, 5678}

    @patch("core.download.subprocess.check_output", return_value="\n")
    def test_empty_output(self, mock_check):
        assert _get_child_pids() == set()

    @patch("core.download.subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "pgrep"))
    def test_called_process_error(self, mock_check):
        assert _get_child_pids() == set()

    @patch("core.download.subprocess.check_output", side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_check):
        assert _get_child_pids() == set()

    @patch("core.download.subprocess.check_output", side_effect=subprocess.TimeoutExpired("pgrep", 5))
    def test_timeout_expired(self, mock_check):
        assert _get_child_pids() == set()


# ---------------------------------------------------------------------------
# Phase 2 — _kill_new_children
# ---------------------------------------------------------------------------
class TestKillNewChildren:
    @patch("core.download.os.kill")
    @patch("core.download._get_child_pids", return_value={100, 200, 300})
    def test_kills_only_new_pids(self, mock_get, mock_kill):
        _kill_new_children({100})
        killed_pids = {call[0][0] for call in mock_kill.call_args_list}
        assert killed_pids == {200, 300}
        for call in mock_kill.call_args_list:
            assert call[0][1] == signal.SIGTERM

    @patch("core.download.os.kill")
    @patch("core.download._get_child_pids", return_value={100})
    def test_no_new_pids_no_kill(self, mock_get, mock_kill):
        _kill_new_children({100})
        mock_kill.assert_not_called()

    @patch("core.download.os.kill", side_effect=OSError("No such process"))
    @patch("core.download._get_child_pids", return_value={200})
    def test_oserror_silently_ignored(self, mock_get, mock_kill):
        _kill_new_children(set())  # should not raise


# ---------------------------------------------------------------------------
# Phase 4 — post_download
# ---------------------------------------------------------------------------
class TestPostDownload:
    @patch("core.download.post_process_dl")
    def test_constructs_correct_path(self, mock_ppdl):
        ydl = MagicMock()
        ydl.prepare_filename.return_value = "/tmp/My Video.webm"
        infos = {"ext": "mp4"}
        cancel = MagicMock()
        progress_cb = MagicMock()
        post_download("x264", ydl, infos, cancel, progress_cb, {"ffmpeg": "ffmpeg"})
        expected_path = "/tmp/My Video.mp4"
        mock_ppdl.assert_called_once_with(expected_path, "x264", cancel, progress_cb, {"ffmpeg": "ffmpeg"})

    @patch("core.download.post_process_dl")
    def test_ext_from_infos_dict(self, mock_ppdl):
        ydl = MagicMock()
        ydl.prepare_filename.return_value = "/tmp/vid.mkv"
        infos = {"ext": "webm"}
        cancel = MagicMock()
        post_download("NLE", ydl, infos, cancel, MagicMock())
        called_path = mock_ppdl.call_args[0][0]
        assert called_path == "/tmp/vid.webm"


# ---------------------------------------------------------------------------
# Phase 5 — download() with threading and retry
# ---------------------------------------------------------------------------
def _make_ydl(extract_result=None, extract_error=None):
    ydl = MagicMock()
    ydl.params = {"progress_hooks": [], "logger": MagicMock()}
    if extract_error:
        ydl.extract_info.side_effect = extract_error
    else:
        ydl.extract_info.return_value = extract_result
    return ydl


class TestDownload:
    @patch("core.download._finish_download")
    @patch("core.download._get_child_pids", return_value=set())
    def test_success(self, mock_pids, mock_finish):
        ydl = _make_ydl(extract_result={"_type": "video", "ext": "mp4"})
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = _make_config()
        config.url = "https://example.com/video"
        download(ydl, config, cancel, MagicMock())
        mock_finish.assert_called_once()

    @patch("core.download._get_child_pids", return_value=set())
    def test_cancel_before_start(self, mock_pids):
        ydl = _make_ydl(extract_result={})
        cancel = MagicMock()
        cancel.is_cancelled.return_value = True
        config = _make_config()
        config.url = "https://example.com/video"
        with pytest.raises(DownloadCancelled):
            download(ydl, config, cancel, MagicMock())

    @patch("core.download._finish_download")
    @patch("core.download._get_child_pids", return_value=set())
    def test_ytdlp_cancelled_converted(self, mock_pids, mock_finish):
        ydl = _make_ydl(extract_error=_FakeYtdlpDownloadCancelled("cancelled"))
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = _make_config()
        config.url = "https://example.com/video"
        with pytest.raises(DownloadCancelled):
            download(ydl, config, cancel, MagicMock())

    @patch("core.download._get_child_pids", return_value=set())
    def test_extract_error_propagated(self, mock_pids):
        ydl = _make_ydl(extract_error=RuntimeError("network error"))
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = _make_config()
        config.url = "https://example.com/video"
        with pytest.raises(RuntimeError, match="network error"):
            download(ydl, config, cancel, MagicMock())

    @patch("core.download.time.sleep")
    @patch("core.download._kill_new_children")
    @patch("core.download._get_child_pids", return_value=set())
    def test_stall_retry_then_timeout(self, mock_pids, mock_kill, mock_sleep):
        ydl = MagicMock()
        ydl.params = {"progress_hooks": [], "logger": MagicMock()}

        call_count = [0]
        stall_detector_ref = [None]

        original_init = _StallDetector.__init__

        def patched_init(self_sd, *args, **kwargs):
            original_init(self_sd, *args, **kwargs)
            stall_detector_ref[0] = self_sd

        def fake_extract(url):
            call_count[0] += 1
            # Force the stall detector to report stalled
            if stall_detector_ref[0]:
                stall_detector_ref[0]._last_activity = 0.0
            raise TimeoutError("connection timed out")

        ydl.extract_info.side_effect = fake_extract

        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = _make_config()
        config.url = "https://example.com/video"

        with patch.object(_StallDetector, "__init__", patched_init):
            with pytest.raises(DownloadTimeout):
                download(ydl, config, cancel, MagicMock())

        assert call_count[0] == MAX_RETRIES

    @patch("core.download._finish_download")
    @patch("core.download._get_child_pids", return_value=set())
    def test_hooks_restored_after_success(self, mock_pids, mock_finish):
        original_hook = MagicMock()
        ydl = _make_ydl(extract_result={"_type": "video"})
        ydl.params["progress_hooks"] = [original_hook]
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = _make_config()
        config.url = "https://example.com/video"
        download(ydl, config, cancel, MagicMock())
        assert ydl.params["progress_hooks"] == [original_hook]
