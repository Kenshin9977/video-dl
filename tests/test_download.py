from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock heavy dependencies BEFORE importing core.download
# ---------------------------------------------------------------------------
_mock_lang = MagicMock()
_mock_lang.GuiField = MagicMock()
_mock_lang.get_text = MagicMock(side_effect=lambda field: f"text_{field}")

for _mod in [
    "yt_dlp",
    "yt_dlp.YoutubeDL",
    "yt_dlp.postprocessor",
    "yt_dlp.postprocessor.FFmpegPostProcessor",
    "yt_dlp.utils",
    "core.encode",
    "i18n",
    "i18n.lang",
    "sys_vars",
]:
    sys.modules[_mod] = MagicMock()

sys.modules["i18n.lang"] = _mock_lang

# Force reimport so the module picks up our mocks
sys.modules.pop("core.download", None)

from core.download import _STATUS_PATTERNS, _finish_download, _YdlUiLogger  # noqa: E402
from core.exceptions import DownloadCancelled, PlaylistNotFound  # noqa: E402

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

    def test_single_video_updates_progress(self):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        progress_cb = MagicMock()
        config = _make_config()
        _finish_download(MagicMock(), {"_type": "video", "ext": "mp4"}, config, cancel, progress_cb)
        progress_cb.on_download_progress.assert_called()

    def test_playlist_iterates_entries(self):
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        progress_cb = MagicMock()
        config = _make_config()
        entries = [{"ext": "mp4"}, {"ext": "webm"}]
        _finish_download(MagicMock(), {"_type": "playlist", "entries": entries}, config, cancel, progress_cb)
        progress_cb.on_download_progress.assert_called()

    def test_cancel_during_playlist_raises(self):
        cancel = MagicMock()
        cancel.is_cancelled.side_effect = [False, True]
        progress_cb = MagicMock()
        config = _make_config()
        entries = [{"ext": "mp4"}, {"ext": "webm"}]
        with pytest.raises(DownloadCancelled):
            _finish_download(MagicMock(), {"_type": "playlist", "entries": entries}, config, cancel, progress_cb)
