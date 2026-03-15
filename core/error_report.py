from __future__ import annotations

import traceback
from dataclasses import dataclass

from core.exceptions import (
    DownloadCancelled,
    DownloadTimeout,
    FFmpegNoValidEncoderFound,
    PlaylistNotFound,
    v20_was_blocked,
)
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

_CHROME_COOKIE_LOCKED = "Could not copy Chrome cookie database"
_CHROME_DPAPI_FAILED = "Failed to decrypt with DPAPI"
_UNABLE_TO_EXTRACT = "Unable to extract"


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
    if _UNABLE_TO_EXTRACT in raw:
        # If Chrome v20 cookies were blocked, the real cause is App-Bound Encryption
        msg = gt(GF.error_chrome_dpapi) if v20_was_blocked() else gt(GF.error_login_required)
        return ErrorReport(
            short_message=msg,
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
