from __future__ import annotations

import re
import traceback
from dataclasses import dataclass

import runtime
from core.exceptions import (
    DownloadCancelled,
    DownloadTimeout,
    FFmpegNoValidEncoderFound,
    PlaylistNotFound,
)
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

_CHROME_COOKIE_LOCKED = "Could not copy Chrome cookie database"
_CHROME_DPAPI_FAILED = "Failed to decrypt with DPAPI"
_UNABLE_TO_EXTRACT = "Unable to extract"
# YouTube's own wording, often with a typographic apostrophe: "confirm you’re not a
# bot". It is a verdict on the connection (too many requests, a flagged IP or IPv6
# block), not a need for an account, and it usually lifts by itself.
BOT_CHECK = re.compile(r"confirm you.{0,3}re not a bot", re.IGNORECASE)
# yt-dlp ends every "this needs an account" error (age check, private or members-only
# video) with how to pass cookies on its command line: "Use --cookies-from-browser
# or --cookies ...". Those flags mean nothing to someone using the app.
_NEEDS_COOKIES = "--cookies"


def is_bot_check(exc: BaseException) -> bool:
    return bool(BOT_CHECK.search(str(exc)))


@dataclass(frozen=True, slots=True)
class ErrorReport:
    short_message: str
    detail: str
    color: str
    should_break: bool
    has_detail: bool


def build_error_report(exc: BaseException) -> ErrorReport:
    """Classify an exception into a structured report for the UI."""
    if isinstance(exc, DownloadCancelled):
        return ErrorReport(
            short_message=gt(GF.dl_cancel),
            detail="",
            color="yellow",
            should_break=True,
            has_detail=False,
        )
    if isinstance(exc, PlaylistNotFound):
        return ErrorReport(
            short_message=gt(GF.playlist_not_found),
            detail="",
            color="yellow",
            should_break=False,
            has_detail=False,
        )
    if isinstance(exc, DownloadTimeout):
        return ErrorReport(
            short_message=f"{gt(GF.dl_error)} Timeout: {exc.url}",
            detail="",
            color="yellow",
            should_break=False,
            has_detail=False,
        )
    if isinstance(exc, FFmpegNoValidEncoderFound):
        return ErrorReport(
            short_message=gt(GF.no_encoder),
            detail="",
            color="red",
            should_break=False,
            has_detail=False,
        )
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    detail = "".join(tb)
    raw = str(exc)
    if _CHROME_DPAPI_FAILED in raw:
        return ErrorReport(
            short_message=gt(GF.error_chrome_dpapi),
            detail=detail,
            color="red",
            should_break=True,
            has_detail=True,
        )
    if _CHROME_COOKIE_LOCKED in raw:
        return ErrorReport(
            short_message=gt(GF.error_chrome_cookies_locked),
            detail=detail,
            color="red",
            should_break=True,
            has_detail=True,
        )
    if BOT_CHECK.search(raw):
        # The desktop app can answer it with browser cookies; the Android app has none.
        hint = "" if runtime.is_android() else gt(GF.error_bot_check_desktop_hint)
        return ErrorReport(
            short_message=gt(GF.error_bot_check) + hint,
            detail=detail,
            color="yellow",
            should_break=False,
            has_detail=True,
        )
    if _UNABLE_TO_EXTRACT in raw or _NEEDS_COOKIES in raw:
        return ErrorReport(
            short_message=gt(GF.error_login_required_android if runtime.is_android() else GF.error_login_required),
            detail=detail,
            color="yellow",
            should_break=False,
            has_detail=True,
        )
    err_msg = raw.removeprefix("ERROR: ")
    first_line = err_msg.splitlines()[0] if err_msg else err_msg
    short = f"{gt(GF.dl_error)} {first_line}"
    return ErrorReport(
        short_message=short,
        detail=detail,
        color="red",
        should_break=False,
        has_detail=True,
    )
