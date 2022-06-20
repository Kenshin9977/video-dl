from __future__ import annotations

import datetime
import os
from typing import Any, Dict, Optional

import PySimpleGUI as Sg
import quantiphy
from quantiphy import Quantity
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor.ffmpeg import EXT_TO_OUT_FORMATS
from yt_dlp.utils import traverse_obj

from ffmpeg_handler import post_process_dl
from lang import GuiField, get_text

EXT_TO_OUT_FORMATS["vtt"] = "webvtt"

CANCELED = False
DL_PROGRESS_WINDOW = Sg.Window(
    get_text(GuiField.download), no_titlebar=True, grab_anywhere=True
)
TIME_LAST_UPDATE = datetime.datetime.now()


def video_dl(values: Dict) -> None:
    global CANCELED, DL_PROGRESS_WINDOW
    CANCELED = False

    trim_start = (
        None
        if not values["Start"]
        else f"{values['sH']}:{values['sM']}:{values['sS']}"
    )
    trim_end = (
        None
        if not values["End"]
        else f"{values['eH']}:{values['eM']}:{values['eS']}"
    )
    ydl_opts = _gen_query(
        values["MaxHeight"][:-1],
        values["Browser"],
        values["AudioOnly"],
        values["TargetACodec"],
        values["path"],
        values["Subtitles"],
        values["IsPlaylist"],
        trim_start,
        trim_end,
        values["PlaylistItems"],
        values["PlaylistItemsCheckbox"],
    )

    with YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(values["url"])
        DL_PROGRESS_WINDOW.close()

    if "_type" in infos_ydl.keys() and infos_ydl["_type"] == "playlist":
        for video_index, infos_ydl_entry in enumerate(infos_ydl["entries"]):
            _post_download(values, ydl, infos_ydl_entry)
    else:
        _post_download(values, ydl, infos_ydl)


def _post_download(values: Dict, ydl, infos_ydl):
    """
    Execute all needed processes after a youtube video download :
    - Execute not AudioOnly process
    """

    ext = "mp3" if values["AudioOnly"] else infos_ydl["ext"]
    full_path = (
        os.path.splitext(ydl.prepare_filename(infos_ydl))[0] + "." + ext
    )
    if not values["AudioOnly"]:
        post_process_dl(full_path, values["TargetCodec"])


def _gen_query(
    h: int,
    browser: str,
    audio_only: bool,
    TargetACodec: str,
    path: str,
    subtitles: bool,
    playlist: bool,
    start: Optional[str],
    end: Optional[str],
    playlist_items: str,
    playlist_items_selected: bool,
) -> Dict[str, Any]:
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
    options = {
        "noplaylist": not playlist,
        "overwrites": True,
        "trim_file_name": 250,
        "outtmpl": os.path.join(
            f"{path}", "%(title).100s - %(uploader)s.%(ext)s"
        ),
        "progress_hooks": [download_progress_bar],
        # "compat_opts": ["no-direct-merge"],
        # 'verbose': True,
    }

    if playlist and playlist_items_selected:
        options["playlist_items"] = playlist_items
    elif not playlist:
        options["playlist_items"] = "1"

    video_format = ""
    acodecs = ["aac", "mp3"] if audio_only else ["aac", "mp3", "mp4a"]
    for acodec in acodecs:
        video_format += (
            f"bestvideo[vcodec*=avc1][height={h}]+bestaudio[acodec*={acodec}]/"
        )
    video_format += f"bestvideo[height={h}]+bestaudio/"
    for acodec in acodecs:
        video_format += f"bestvideo[vcodec*=avc1][height<=?{h}]+bestaudio[acodec*={acodec}]/"  # noqa
    video_format += f"bestvideo[vcodec*=avc1][height<=?{h}]+bestaudio/"
    for acodec in ["aac", "mp3", "mp4a"]:
        video_format += f"bestvideo[height<=?{h}]+bestaudio[acodec={acodec}]/"
    video_format += f"bestvideo[height<=?{h}]+bestaudio/best"
    audio_format = "bestaudio[acodec*=mp3]/bestaudio/best"
    options["format"] = audio_format if audio_only else video_format
    if audio_only:
        options["extract_audio"] = True
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": TargetACodec,
                "preferredquality": None,
            }
        ]
    if subtitles:
        options["subtitleslangs"] = ["all"]
        options["writesubtitles"] = True
    if start or end:
        options["external_downloader"] = "ffmpeg"
        if not start and end:
            options["external_downloader_args"] = {
                "ffmpeg_i": ["-ss", "00:00:00", "-to", end]
            }
        elif start and end:
            options["external_downloader_args"] = {
                "ffmpeg_i": ["-ss", start, "-to", end]
            }
        else:
            options["external_downloader_args"] = {"ffmpeg_i": ["-ss", start]}
    elif not audio_only:
        options["merge-output-format"] = "mp4"
    if browser != "None":
        options["cookiesfrombrowser"] = [browser.lower()]
    return options


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
