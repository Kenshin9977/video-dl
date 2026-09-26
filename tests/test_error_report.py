from __future__ import annotations

from core.error_report import ErrorReport, build_error_report
from core.exceptions import (
    DownloadCancelled,
    DownloadTimeout,
    FFmpegNoValidEncoderFound,
    PlaylistNotFound,
)


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

    def test_chrome_cookies_locked(self):
        try:
            raise RuntimeError(
                "Could not copy Chrome cookie database. See https://github.com/yt-dlp/yt-dlp/issues/7271"
            )
        except RuntimeError as e:
            report = build_error_report(e)
        assert report.color == "red"
        assert report.should_break is True
        assert report.has_detail is True
        assert "Chrome" in report.short_message

    def test_unable_to_extract(self):
        try:
            raise RuntimeError("ERROR: [SomeSite] abc123: Unable to extract title")
        except RuntimeError as e:
            report = build_error_report(e)
        assert report.color == "yellow"
        assert report.should_break is False
        assert report.has_detail is True
        assert "login" in report.short_message.lower() or "cookie" in report.short_message.lower()

    def test_report_is_frozen(self):
        report = build_error_report(DownloadCancelled())
        assert isinstance(report, ErrorReport)
        try:
            report.color = "green"  # type: ignore[misc]
            raise AssertionError("should have raised")
        except AttributeError:
            pass


# Other test files swap modules in sys.modules; go through the objects
# core.error_report actually uses, not whatever "runtime" or "i18n" is now.
import core.error_report as er  # noqa: E402


class TestAccountAndBotErrors:
    """yt-dlp's own words end with "Use --cookies-from-browser or --cookies": flags that
    mean nothing in the app, and on Android point at an option that is not there."""

    BOT = (
        "ERROR: [youtube] ch8J7uVEddc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or "
        "--cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ  for how to manually pass cookies"
    )
    AGE = (
        "ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users. "
        "Use --cookies-from-browser or --cookies for the authentication."
    )
    PRIVATE = (
        "ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video. "
        "Use --cookies-from-browser or --cookies for the authentication."
    )

    def test_a_bot_check_says_what_it_is_and_what_to_try(self, monkeypatch):
        monkeypatch.setattr(er.runtime, "is_android", lambda: False)
        report = build_error_report(Exception(self.BOT))

        assert report.short_message == er.gt(er.GF.error_bot_check) + er.gt(er.GF.error_bot_check_desktop_hint)
        assert "--cookies" not in report.short_message
        assert report.color == "yellow"
        assert report.has_detail is True

    def test_on_android_it_does_not_point_at_an_option_that_is_not_there(self, monkeypatch):
        monkeypatch.setattr(er.runtime, "is_android", lambda: True)

        assert build_error_report(Exception(self.BOT)).short_message == er.gt(er.GF.error_bot_check)

    def test_videos_that_need_an_account_say_so(self, monkeypatch):
        for android, field in ((False, er.GF.error_login_required), (True, er.GF.error_login_required_android)):
            monkeypatch.setattr(er.runtime, "is_android", lambda android=android: android)
            for message in (self.AGE, self.PRIVATE):
                assert build_error_report(Exception(message)).short_message == er.gt(field)
