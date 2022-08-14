from __future__ import annotations

import datetime
import os
from typing import Optional

import PySimpleGUI as Sg
import quantiphy
from quantiphy import Quantity
from yt_dlp import YoutubeDL
from yt_dlp.utils import traverse_obj

from ffmpeg_handler import post_process_dl
from lang import GuiField, get_text

CANCELED = False
DL_PROGRESS_WINDOW = Sg.Window(
    get_text(GuiField.download), no_titlebar=True, grab_anywhere=True
)
TIME_LAST_UPDATE = datetime.datetime.now()


def video_dl(opts: dict) -> None:
    global CANCELED, DL_PROGRESS_WINDOW
    CANCELED = False

    ydl_opts = _gen_ydl_opts(opts)
    with YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(opts["url"])
        DL_PROGRESS_WINDOW.close()
        if infos_ydl.get("_type") == "playlist":
            for infos_ydl_entry in infos_ydl["entries"]:
                _post_download(opts, ydl, infos_ydl_entry)
        else:
            _post_download(opts, ydl, infos_ydl)


def _post_download(opts: dict, ydl, infos_ydl) -> None:
    """
    Execute all needed processes after a youtube video download :
    - Execute not AudioOnly process
    """

    target_acodec = opts["TargetACodec"].lower()
    ext = target_acodec if opts["AudioOnly"] else infos_ydl["ext"]
    full_path = (
        os.path.splitext(ydl.prepare_filename(infos_ydl))[0] + "." + ext
    )
    if not opts["AudioOnly"]:
        post_process_dl(full_path, opts["TargetVCodec"])


def _create_progress_bar() -> None:
    global DL_PROGRESS_WINDOW
    layout = [
        [Sg.Text(get_text(GuiField.download))],
        [Sg.ProgressBar(100, orientation="h", size=(20, 20), key="-PROG-")],
        [Sg.Text(get_text(GuiField.ff_starting), key="PROGINFOS1")],
        [Sg.Text("", key="PROGINFOS2")],
        [Sg.Cancel(button_text=get_text(GuiField.cancel_button))],
    ]
    DL_PROGRESS_WINDOW = Sg.Window(
        get_text(GuiField.download),
        layout,
        no_titlebar=True,
        grab_anywhere=True,
        keep_on_top=True,
    )


def _gen_ydl_opts(opts: dict) -> dict:
    _create_progress_bar()

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
            opts["PlaylistItems"],
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
    opts = {
        "noplaylist": not playlist,
        "overwrites": True,
        "trim_file_name": 250,
        "outtmpl": os.path.join(
            f"{path}", "%(title).100s - %(uploader)s.%(ext)s"
        ),
        "progress_hooks": [download_progress_bar],
        "playlist_items": playlist_items if playlist_items_selected else 1,
        "compat_opts": ["no-direct-merge"],
        "verbose": True,
    }
    return opts


def _gen_av_opts(h: int, audio_only: bool, target_acodec: str) -> dict:
    opts = {}
    if audio_only:
        format_opt = "ba/ba*"
        if target_acodec != "best":
            format_opt = f"ba[acodec*={target_acodec}]/{format_opt}"
        # Either the target audio codec, the best without video or the best one
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
        acodec_re_str = "acodec~='aac|mp3|mp4a'"
        # Audio codecs compatible with mp4 container
        format_opt = f"((bv[{vcodec_re_str}]/bv)+(ba[{acodec_re_str}]/ba))/b"
        opts.update({"format_sort": {"res": h}, "merge-output-format": "mp4"})
    opts.update({"format": format_opt})
    return opts


def _gen_ffmpeg_opts(start: Optional[str], end: Optional[str]) -> dict:
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
    opts = {}
    if subtitles:
        opts.update({"subtitleslangs": ["all"], "writesubtitles": True})
    return opts


def _gen_browser_opts(browser: str) -> dict:
    opts = {}
    if browser != "None":
        opts["cookiesfrombrowser"] = [browser.lower()]
    return opts


def download_progress_bar(d):
    global CANCELED, DL_PROGRESS_WINDOW, TIME_LAST_UPDATE
    event, _ = DL_PROGRESS_WINDOW.read(timeout=20)

    if d.get("status") == "finished":
        DL_PROGRESS_WINDOW.close()
    elif event == get_text(GuiField.cancel_button):
        DL_PROGRESS_WINDOW.close()
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
        if progress_percent >= 100:
            progress_percent = 99
    except (ZeroDivisionError, TypeError):
        progress_percent = "-"

    playlist_index = traverse_obj(d, ("info_dict", "playlist_index"))
    n_entries = traverse_obj(d, ("info_dict", "n_entries"))
    if not playlist_index or n_entries == 1:
        percent_str = f"{progress_percent}%"
    else:
        percent_str = f"{progress_percent}% ({playlist_index}/{n_entries})"

    DL_PROGRESS_WINDOW["PROGINFOS1"].update(percent_str)
    DL_PROGRESS_WINDOW["-PROG-"].update(progress_percent)
    now = datetime.datetime.now()
    delta_ms = (now - TIME_LAST_UPDATE).seconds * 1000 + (
        now - TIME_LAST_UPDATE
    ).microseconds // 1000
    if delta_ms >= 500:
        DL_PROGRESS_WINDOW["PROGINFOS2"].update(
            f"{get_text(GuiField.ff_speed)} : {speed}"
        )
        TIME_LAST_UPDATE = now
    return
