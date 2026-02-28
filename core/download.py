from __future__ import annotations

import logging
import os
import re

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegPostProcessor
from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

from core.callbacks import CancelToken, ProgressCallback, StatusCallback
from core.config_types import DownloadConfig
from core.encode import post_process_dl
from core.exceptions import DownloadCancelled, PlaylistNotFound
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

logger = logging.getLogger("videodl")

_STATUS_PATTERNS = [
    (re.compile(r"Extracting cookies from", re.IGNORECASE), GF.extracting_cookies),
    (re.compile(r"Solving JS challenge", re.IGNORECASE), GF.solving_js),
    (re.compile(r"Extracting URL|Downloading webpage|Downloading player", re.IGNORECASE), GF.fetching_info),
]


class _YdlUiLogger:
    """Bridges yt-dlp log messages to a StatusCallback."""

    def __init__(self, status_cb: StatusCallback):
        self._status_cb = status_cb

    def _update_status(self, msg):
        for pattern, gui_field in _STATUS_PATTERNS:
            if pattern.search(msg):
                self._status_cb.on_status(gt(gui_field))
                return

    def debug(self, msg):
        logger.debug(msg)
        self._update_status(msg)

    def info(self, msg):
        logger.info(msg)
        self._update_status(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def create_ydl(
    ydl_opts: dict,
    status_cb: StatusCallback,
    ff_path: dict[str, str],
) -> YoutubeDL:
    """Create a reusable YoutubeDL instance (cookies extracted once)."""
    logger.debug("ydl options %s", ydl_opts)
    ydl_opts["logger"] = _YdlUiLogger(status_cb)
    FFmpegPostProcessor._ffmpeg_location.set(ff_path.get("ffmpeg"))
    return YoutubeDL(ydl_opts)


def download(
    ydl: YoutubeDL,
    config: DownloadConfig,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
) -> None:
    try:
        infos_ydl = ydl.extract_info(config.url)
    except YtdlpDownloadCancelled:
        raise DownloadCancelled from None
    if cancel.is_cancelled():
        raise DownloadCancelled
    _finish_download(ydl, infos_ydl, config, cancel, progress_cb)


def _finish_download(
    ydl: YoutubeDL,
    infos_ydl: dict | None,
    config: DownloadConfig,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
) -> None:
    if infos_ydl is None:
        raise PlaylistNotFound
    if config.audio_only:
        return
    progress_cb.on_download_progress({"status": "finished", "progress_float": 1.0})
    if infos_ydl.get("_type") == "playlist":
        for infos_ydl_entry in infos_ydl["entries"]:
            if cancel.is_cancelled():
                raise DownloadCancelled
            post_download(
                config.target_vcodec,
                ydl,
                infos_ydl_entry,
                cancel,
                progress_cb,
                config.ff_path,
            )
    else:
        post_download(config.target_vcodec, ydl, infos_ydl, cancel, progress_cb, config.ff_path)
    if cancel.is_cancelled():
        raise DownloadCancelled


def post_download(
    target_vcodec: str,
    ydl: YoutubeDL,
    infos_ydl: dict,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
    ff_path: dict[str, str] | None = None,
) -> None:
    """
    Execute all needed processes after a youtube video download.

    Args:
        target_vcodec: Video codec target ("Best", "NLE", "x264", etc.)
        ydl: YoutubeDL instance
        infos_ydl: Video's infos fetched by yt-dlp
        cancel: Cancellation token
        progress_cb: Progress callback
        ff_path: FFmpeg/FFprobe paths
    """
    ext = infos_ydl["ext"]
    media_filename_formated = ydl.prepare_filename(infos_ydl)
    full_path = f"{os.path.splitext(media_filename_formated)[0]}.{ext}"
    post_process_dl(full_path, target_vcodec, cancel, progress_cb, ff_path)
