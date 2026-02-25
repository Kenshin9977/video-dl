from __future__ import annotations

import logging
import os
import re

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegPostProcessor

from core.encode import post_process_dl
from core.exceptions import PlaylistNotFound
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

    def __init__(self, status_text, ui_dirty_event):
        self._status_text = status_text
        self._ui_dirty = ui_dirty_event

    def _update_status(self, msg):
        for pattern, gui_field in _STATUS_PATTERNS:
            if pattern.search(msg):
                self._status_text.value = gt(gui_field)
                self._status_text.visible = True
                self._ui_dirty.set()
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
    ydl_opts["logger"] = _YdlUiLogger(videodl_app.download_status_text, videodl_app._ui_dirty)
    FFmpegPostProcessor._ffmpeg_location.set(FF_PATH.get("ffmpeg"))
    return YoutubeDL(ydl_opts)


def download(videodl_app, ydl, url=None):
    target_url = url or videodl_app.media_link.value
    infos_ydl = ydl.extract_info(target_url)
    _finish_download(videodl_app, ydl, infos_ydl)


def get_download_info(ydl, url):
    """Extract info without downloading, return expected size and temp path."""
    info = ydl.extract_info(url, download=False)
    if info is None:
        return None, None, None
    if info.get("_type") == "playlist":
        total_size = sum((e.get("filesize") or e.get("filesize_approx") or 0) for e in (info.get("entries") or []))
    else:
        total_size = info.get("filesize") or info.get("filesize_approx") or 0
        if not total_size and info.get("requested_formats"):
            total_size = sum((f.get("filesize") or f.get("filesize_approx") or 0) for f in info["requested_formats"])
    tmpfile = ydl.prepare_filename(info)
    return info, total_size, tmpfile


def download_from_info(videodl_app, ydl, info):
    """Download from a pre-extracted info dict (no double extract)."""
    ydl.process_ie_result(info, download=True)
    _finish_download(videodl_app, ydl, info)


def _finish_download(videodl_app, ydl, infos_ydl):
    if infos_ydl is None:
        raise PlaylistNotFound
    if videodl_app.audio_only.value:
        return
    videodl_app.download_progress.controls[0].value = f"{gt(GF.download)} 100%"
    videodl_app._ui_dirty.set()
    if infos_ydl.get("_type") == "playlist":
        for infos_ydl_entry in infos_ydl["entries"]:
            post_download(
                videodl_app._get_effective_vcodec(),
                ydl,
                infos_ydl_entry,
                videodl_app,
            )
    else:
        post_download(videodl_app._get_effective_vcodec(), ydl, infos_ydl, videodl_app)


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
