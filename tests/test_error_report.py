from __future__ import annotations

from core.error_report import ErrorReport, build_error_report
from core.exceptions import DownloadCancelled, DownloadTimeout, FFmpegNoValidEncoderFound, PlaylistNotFound


class TestBuildErrorReport:
    def test_download_cancelled(self):
        report = build_error_report(DownloadCancelled())
        assert report.color == "yellow"
        assert report.should_break is True
        assert report.has_detail is False
        assert report.detail == ""

    def test_playlist_not_found(self):
        report = build_error_report(PlaylistNotFound())
        assert report.color == "yellow"
        assert report.should_break is False
        assert report.has_detail is False

    def test_no_valid_encoder(self):
        report = build_error_report(FFmpegNoValidEncoderFound())
        assert report.color == "red"
        assert report.should_break is False
        assert report.has_detail is False

    def test_generic_exception(self):
        try:
            raise ValueError("something went wrong")
        except ValueError as e:
            report = build_error_report(e)
        assert report.color == "red"
        assert report.should_break is False
        assert report.has_detail is True
        assert "something went wrong" in report.short_message
        assert "ValueError" in report.detail
        assert "something went wrong" in report.detail

    def test_generic_exception_strips_error_prefix(self):
        try:
            raise RuntimeError("ERROR: video unavailable")
        except RuntimeError as e:
            report = build_error_report(e)
        assert "ERROR:" not in report.short_message
        assert "video unavailable" in report.short_message

    def test_generic_exception_has_traceback(self):
        try:
            raise TypeError("bad type")
        except TypeError as e:
            report = build_error_report(e)
        assert "Traceback" in report.detail
        assert "TypeError: bad type" in report.detail

    def test_download_timeout(self):
        report = build_error_report(DownloadTimeout("https://example.com/video"))
        assert report.color == "yellow"
        assert report.should_break is False
        assert report.has_detail is False
        assert "Timeout" in report.short_message
        assert "example.com" in report.short_message

    def test_report_is_frozen(self):
        report = build_error_report(DownloadCancelled())
        assert isinstance(report, ErrorReport)
        try:
            report.color = "green"  # type: ignore[misc]
            raise AssertionError("should have raised")
        except AttributeError:
            pass
