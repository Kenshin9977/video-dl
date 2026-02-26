from __future__ import annotations

import logging
import os
import re

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegPostProcessor
from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

from core.encode import post_process_dl
from core.exceptions import DownloadCancelled, PlaylistNotFound
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt
from sys_vars import FF_PATH

logger = logging.getLogger("videodl")

_STATUS_PATTERNS = [
    (re.compile(r"Extracting cookies from", re.IGNORECASE), GF.extracting_cookies),
    (re.compile(r"Solving JS challenge", re.IGNORECASE), GF.solving_js),
    (re.compile(r"Extracting URL|Downloading webpage|Downloading player", re.IGNORECASE), GF.fetching_info),
]


class _YdlUiLogger:
    """Bridges yt-dlp log messages to a Flet status text widget."""

    def __init__(self, status_text, mark_dirty):
        self._status_text = status_text
        self._mark_dirty = mark_dirty

    def _update_status(self, msg):
        for pattern, gui_field in _STATUS_PATTERNS:
            if pattern.search(msg):
                self._status_text.value = gt(gui_field)
                self._status_text.visible = True
                self._mark_dirty()
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


def create_ydl(videodl_app):
    """Create a reusable YoutubeDL instance (cookies extracted once)."""
    ydl_opts = videodl_app._gen_ydl_opts()
    logger.debug("ydl options %s", ydl_opts)
    ydl_opts["logger"] = _YdlUiLogger(videodl_app.download_status_text, videodl_app._mark_ui_dirty)
    FFmpegPostProcessor._ffmpeg_location.set(FF_PATH.get("ffmpeg"))
    return YoutubeDL(ydl_opts)


def download(videodl_app, ydl, url=None):
    target_url = url or videodl_app.media_link.value
    try:
        infos_ydl = ydl.extract_info(target_url)
    except YtdlpDownloadCancelled:
        raise DownloadCancelled from None
    if videodl_app._cancel_requested.is_set():
        raise DownloadCancelled
    _finish_download(videodl_app, ydl, infos_ydl)


def _finish_download(videodl_app, ydl, infos_ydl):
    if infos_ydl is None:
        raise PlaylistNotFound
    if videodl_app.audio_only.value:
        return
    videodl_app.download_progress.controls[0].value = f"{gt(GF.download)} 100%"
    videodl_app._mark_ui_dirty()
    if infos_ydl.get("_type") == "playlist":
        for infos_ydl_entry in infos_ydl["entries"]:
            if videodl_app._cancel_requested.is_set():
                raise DownloadCancelled
            post_download(
                videodl_app._get_effective_vcodec(),
                ydl,
                infos_ydl_entry,
                videodl_app,
            )
    else:
        post_download(videodl_app._get_effective_vcodec(), ydl, infos_ydl, videodl_app)
    if videodl_app._cancel_requested.is_set():
        raise DownloadCancelled


def post_download(target_vcodec: str, ydl: YoutubeDL, infos_ydl: dict, videodl_app) -> None:
    """
    Execute all needed processes after a youtube video download

    Args:
        opts (dict): Options entered by the user
        ydl (YoutubeDL): YoutubeDL instance
        infos_ydl (dict): Video's infos fetched by yt-dlp
    """
    ext = infos_ydl["ext"]
    media_filename_formated = ydl.prepare_filename(infos_ydl)
    full_path = f"{os.path.splitext(media_filename_formated)[0]}.{ext}"
    post_process_dl(full_path, target_vcodec, videodl_app)
