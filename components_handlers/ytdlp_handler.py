from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

import quantiphy
from lang import GuiField, get_text
from quantiphy import Quantity
from sys_vars import FF_PATH
from utils.gui_utils import create_progress_bar
from yt_dlp import YoutubeDL
from yt_dlp.utils import traverse_obj

from components_handlers.ffmpeg_handler import post_process_dl

log = logging.getLogger(__name__)
LAST_SPEED = "-"
DL_PROG_WIN = None
PP_PROG_WIN = None
TIME_LAST_UPDATE = datetime.now()


def video_dl(opts: dict) -> None:
    """
    Download and process the media if necessary using the user inputs.

    Args:
        opts (dict): Options entered by the user
    """
    global DL_PROG_WIN, PP_PROG_WIN
    ydl_opts = _gen_ydl_opts(opts)
    DL_PROG_WIN = create_progress_bar(get_text(GuiField.download), False)
    PP_PROG_WIN = create_progress_bar(get_text(GuiField.process), False)
    with YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(opts["url"])
        DL_PROG_WIN.close()
        PP_PROG_WIN.close()
        if not opts["AudioOnly"]:
            if infos_ydl.get("_type") == "playlist":
                for infos_ydl_entry in infos_ydl["entries"]:
                    _post_download(opts, ydl, infos_ydl_entry)
            else:
                _post_download(opts, ydl, infos_ydl)


def _post_download(opts: dict, ydl: YoutubeDL, infos_ydl: dict) -> None:
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
    post_process_dl(full_path, opts["TargetVCodec"])


def _gen_ydl_opts(opts: dict) -> dict:
    """
    Generate yt-dlp options' dictionnary.

    Args:
        opts (dict): Options selected in the GUI

    Returns:
        dict: yt-dlp options
    """

    trim_start = (
        f"{opts['sH']}:{opts['sM']}:{opts['sS']}" if opts["Start"] else None
    )
    trim_end = (
        f"{opts['eH']}:{opts['eM']}:{opts['eS']}" if opts["End"] else None
    )
    ydl_opts = {}
    ydl_opts.update(
        _gen_file_opts(
            opts["path"],
            opts["IsPlaylist"],
            str(opts["PlaylistItems"]),
            opts["PlaylistItemsCheckbox"],
        )
    )
    max_height = opts["MaxHeight"][:-1]
    target_acodec = opts["TargetACodec"]
    ydl_opts.update(_gen_av_opts(max_height, opts["AudioOnly"], target_acodec))
    ydl_opts.update(_gen_ffmpeg_opts(trim_start, trim_end))
    ydl_opts.update(_gen_subtitles_opts(opts["Subtitles"]))
    ydl_opts.update(_gen_browser_opts(opts["Browser"]))

    return ydl_opts


def _gen_file_opts(
    path: str,
    playlist: bool,
    playlist_items: str,
    playlist_items_selected: bool,
) -> dict:
    """
    Generate yt-dlp file's options

    Args:
        path (str): Path to download to
        playlist (bool): Whether or not Playlist is checked
        playlist_items (str): The indices to fetch from the playlist
        playlist_items_selected (bool): Whether or not indices is checked

    Returns:
        dict: yt-dlp file's options
    """
    opts = {
        "noplaylist": not playlist,
        "overwrites": True,
        "trim_file_name": 250,
        "outtmpl": os.path.join(
            f"{path}", "%(title).100s - %(uploader)s.%(ext)s"
        ),
        "progress_hooks": [download_progress_bar],
        "postprocessor_hooks": [postprocess_progress_bar],
    }
    if playlist_items_selected:
        opts["playlist_items"] = playlist_items or 1

    if FF_PATH.get("ffmpeg") != "ffmpeg":
        opts["ffmpeg_location"] = FF_PATH.get("ffmpeg")

    return opts


def _gen_av_opts(h: int, audio_only: bool, target_acodec: str) -> dict:
    """
    Generate yt-dlp options for the audio and the video both for their search
    filters, their downloader and their post process.

    Args:
        h (int): Resolution of the video to look for
        audio_only (bool): Whether or not Audio only is checked
        target_acodec (str): The video codec target

    Returns:
        dict: yt-dlp filters, downloader and post process options
    """
    opts = {}
    if audio_only:
        format_opt = "ba/ba*"
        if target_acodec != "best":
            format_opt = f"ba[acodec*={target_acodec}]/{format_opt}"
        # Either the target audio codec, the best without video so the download
        # is faster or the best one even if there is a video with it
        opts.update(
            {
                "extract_audio": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": target_acodec,
                    }
                ],
            }
        )
    else:
        vcodec_re_str = "vcodec~='avc1|h264'"
        # Either the target vcodec or the most common and easiest to convert
        # (h264)
        acodec_re_str = "acodec~='aac|mp3|mp4a'"
        # Audio codecs compatible with mp4 containers
        format_opt = f"((bv[{vcodec_re_str}]/bv)+(ba[{acodec_re_str}]/ba))/b"
        # The best video preferably with the target codec merged with the best
        # audio without video preferably with a codec compatible with mp4
        # containers or the overall best
        opts.update({"format_sort": {"res": h}, "merge-output-format": "mp4"})
        # In order looks for the exact resolution, lower if not found, higher
        # if not found
    opts.update({"format": format_opt})
    return opts


def _gen_ffmpeg_opts(start: Optional[str], end: Optional[str]) -> dict:
    """
    Generate the dictionnary for yt-dlp ffmpeg options

    Args:
        start (Optional[str]): Start timestamp
        end (Optional[str]): End timestamp

    Returns:
        dict: yt-dlp ffmpeg options
    """
    opts = {}
    if start or end:
        opts.update(
            {
                "external_downloader": "ffmpeg",
                "external_downloader_args": {
                    "ffmpeg_i": [
                        "-ss",
                        start or "00:00:00",
                        "-to",
                        end or "99:99:99",
                    ]
                },
            }
        )
    return opts


def _gen_subtitles_opts(subtitles: bool) -> dict:
    """
    Generate the dictionnary for yt-dlp subtitles options

    Args:
        subtitles (bool): Whether or not the subtitles option is checked

    Returns:
        dict: yt-dlp options
    """
    opts = {}
    if subtitles:
        opts.update({"subtitleslangs": ["all"], "writesubtitles": True})
    return opts


def _gen_browser_opts(browser: str) -> dict:
    """
    Generate the dictionnary for yt-dlp cookies option

    Args:
        browser (str): Browser selected from the GUI

    Returns:
        dict: yt-dlp cookies option
    """
    opts = {}
    if browser != "None":
        opts["cookiesfrombrowser"] = [browser.lower()]
    return opts


def download_progress_bar(d: dict) -> None:
    """
    Handles the download's progress bar

    Args:
        d (dict): yt-dlp download progress' infos

    Raises:
        ValueError: If the user cancel the download
    """
    global DL_PROG_WIN, TIME_LAST_UPDATE, LAST_SPEED
    event, _ = DL_PROG_WIN.read(timeout=20)
    dl_status = d.get("status")
    n_current_entry = traverse_obj(d, ("info_dict", "playlist_autonumber"))
    n_entries = traverse_obj(d, ("info_dict", "n_entries"))

    if dl_status == "finished":
        if n_current_entry is not None and n_current_entry == n_entries:
            DL_PROG_WIN.close()
        elif n_current_entry is None:
            DL_PROG_WIN.close()
    elif event == get_text(GuiField.cancel_button):
        DL_PROG_WIN.close()
        raise ValueError
    try:
        speed = Quantity(d.get("speed"), "B/s").render(prec=2)
    except quantiphy.InvalidNumber:
        speed = "-"
    try:
        downloaded = Quantity(d.get("downloaded_bytes"), "B")
    except quantiphy.InvalidNumber:
        downloaded = "-"
    try:
        total = Quantity(d.get("total_bytes"), "B")
    except quantiphy.InvalidNumber:
        try:
            total = Quantity(d.get("total_bytes_estimate"), "B")
        except quantiphy.InvalidNumber:
            total = 0
    try:
        progress_percent = int(downloaded / total * 100)
        # Necessary for when the total size is inaccurate
        if progress_percent >= 100:
            progress_percent = 99
    except (ZeroDivisionError, TypeError):
        progress_percent = "-"

    n_current_entry = traverse_obj(d, ("info_dict", "playlist_autonumber"))
    n_entries = traverse_obj(d, ("info_dict", "n_entries"))
    if n_current_entry is None or n_entries == 1:
        percent_str = f"{progress_percent}%"
    else:
        percent_str = f"{progress_percent}% ({n_current_entry}/{n_entries})"

    DL_PROG_WIN["PROGINFOS1"].update(percent_str)
    DL_PROG_WIN["-PROG-"].update(progress_percent)
    time_elapsed = datetime.now() - TIME_LAST_UPDATE
    delta_ms = time_elapsed.seconds * 1000 + time_elapsed.microseconds // 1000
    if delta_ms >= 500:
        DL_PROG_WIN["PROGINFOS2"].update(
            f"{get_text(GuiField.ff_speed)} : {speed}"
        )
        LAST_SPEED = speed
        TIME_LAST_UPDATE = datetime.now()


def postprocess_progress_bar(d):
    global PP_PROG_WIN
    event, _ = PP_PROG_WIN.read(timeout=20)
    pp_status = d.get("status", "")
    n_current_entry = traverse_obj(d, ("info_dict", "playlist_autonumber"))
    n_entries = traverse_obj(d, ("info_dict", "n_entries"))

    if pp_status == "finished":
        if n_current_entry is not None and n_current_entry == n_entries:
            PP_PROG_WIN.close()
        elif n_current_entry is None:
            PP_PROG_WIN.close()
    elif event == get_text(GuiField.cancel_button):
        PP_PROG_WIN.close()
        raise ValueError
    try:
        speed = Quantity(d.get("speed"), "B/s").render(prec=2)
    except quantiphy.InvalidNumber:
        speed = "-"
    try:
        downloaded = Quantity(d.get("processed_bytes"), "B")
    except quantiphy.InvalidNumber:
        downloaded = "-"
    try:
        total = Quantity(d.get("total_bytes"), "B")
    except quantiphy.InvalidNumber:
        total = 0
    try:
        progress_percent = int(downloaded / total * 100)
        # Necessary for when the total size is inaccurate
        if progress_percent >= 100:
            progress_percent = 99
    except (ZeroDivisionError, TypeError):
        progress_percent = "-"

    n_current_entry = traverse_obj(d, ("info_dict", "playlist_autonumber"))
    n_entries = traverse_obj(d, ("info_dict", "n_entries"))
    if n_current_entry is None or n_entries == 1:
        percent_str = f"{progress_percent}%"
    else:
        percent_str = f"{progress_percent}% ({n_current_entry}/{n_entries})"

    PP_PROG_WIN["PROGINFOS1"].update(percent_str)
    PP_PROG_WIN["-PROG-"].update(progress_percent)
    DL_PROG_WIN["PROGINFOS2"].update(f"{get_text(GuiField.ff_speed)}: {speed}")
