from __future__ import annotations

import traceback
from dataclasses import dataclass

from core.exceptions import DownloadCancelled, FFmpegNoValidEncoderFound, PlaylistNotFound
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt


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
    err_msg = str(exc).removeprefix("ERROR: ")
    short = f"{gt(GF.dl_error)} {err_msg}"
    return ErrorReport(
        short_message=short,
        detail=detail,
        color="red",
        should_break=False,
        has_detail=True,
    )
