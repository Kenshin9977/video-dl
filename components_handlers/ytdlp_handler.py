from __future__ import annotations

import logging
import os

from yt_dlp import YoutubeDL

from components_handlers.ffmpeg_handler import _post_process_dl
from videodl_exceptions import PlaylistNotFound

logger = logging.getLogger()


def download(videodl_app):
    ydl_opts = videodl_app._gen_ydl_opts()
    logger.debug("ydl options %s", ydl_opts)
    with YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(videodl_app.media_link.value)
        if infos_ydl is None:
            raise PlaylistNotFound
        if videodl_app.audio_only.value:
            return
        if infos_ydl.get("_type") == "playlist":
            for infos_ydl_entry in infos_ydl["entries"]:
                post_download(
                    videodl_app.video_codec.value,
                    ydl,
                    infos_ydl_entry,
                    videodl_app,
                )
        else:
            post_download(
                videodl_app.video_codec.value, ydl, infos_ydl, videodl_app
            )


def post_download(
    target_vcodec: str, ydl: YoutubeDL, infos_ydl: dict, videodl_app
) -> None:
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
    _post_process_dl(full_path, target_vcodec, videodl_app)
