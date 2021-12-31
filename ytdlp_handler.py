import datetime
import PySimpleGUI as Sg
import yt_dlp

from os import path
from typing import Any, Dict
from quantiphy import Quantity
from ffmpeg_handler import post_process_dl
from yt_dlp.postprocessor.ffmpeg import EXT_TO_OUT_FORMATS

from lang import (
    GuiField,
    get_text,
)

EXT_TO_OUT_FORMATS["vtt"] = "webvtt"

CANCELED = False
DL_PROGRESS_WINDOW = Sg.Window(
    get_text(GuiField.download), no_titlebar=True, grab_anywhere=True
)
TIME_LAST_UPDATE = datetime.datetime.now()


def video_dl(values: Dict) -> None:
    global CANCELED, DL_PROGRESS_WINDOW
    CANCELED = False
    trim_start = f"{values['sH']}:{values['sM']}:{values['sS']}"
    trim_end = f"{values['eH']}:{values['eM']}:{values['eS']}"
    ydl_opts = _gen_query(
        values["MaxHeight"][:-1],
        values["Browser"],
        values["AudioOnly"],
        values["path"],
        values["Subtitles"],
        trim_start,
        trim_end,
    )
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(values["url"])
    DL_PROGRESS_WINDOW.close()
    ext = "mp3" if values["AudioOnly"] else infos_ydl["ext"]
    full_path = path.splitext(ydl.prepare_filename(infos_ydl))[0] + "." + ext
    if not values["AudioOnly"]:
        post_process_dl(full_path, values["TargetCodec"])


def _gen_query(
    h: int,
    browser: str,
    audio_only: bool,
    path: str,
    subtitles: bool,
    start: str,
    end: str,
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
        "noplaylist": True,
        "overwrites": True,
        "trim_file_name": 250,
        "outtmpl": os.path.join(path, "%(title).100s - %(uploader)s.%(ext)s"),
        "progress_hooks": [download_progress_bar],
        # 'verbose': True,
    }
    options["compat_opts"] = ["no-direct-merge"]
    video_format = ""
    acodecs = ["aac", "mp3"] if audio_only else ["aac", "mp3", "mp4a"]
    for acodec in acodecs:
        video_format += (
            f"bestvideo[vcodec*=avc1][height={h}]+bestaudio[acodec*={acodec}]/"
        )
    video_format += f"bestvideo[height={h}]+bestaudio/"
    for acodec in acodecs:
        video_format += (
            f"bestvideo[vcodec*=avc1][height<=?{h}]+bestaudio[acodec*={acodec}]/"
        )
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
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ]
    if subtitles:
        options["subtitleslangs"] = ["all"]
        options["writesubtitles"] = True
    if start != "00:00:00" or end != "99:59:59":
        options["external_downloader"] = "ffmpeg"
        options["concurrent_fragments"] = 20
        if start == "00:00:00":
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
    speed = (
        "-"
        if "speed" not in d.keys() or d["speed"] is None
        else Quantity(d["speed"], "B/s").render(prec=2)
    )
    downloaded = (
        "-"
        if "downloaded_bytes" not in d.keys() or d["downloaded_bytes"] is None
        else Quantity(d["downloaded_bytes"], "B")
    )
    total = (
        Quantity(d["total_bytes"], "B")
        if "total_bytes" in d.keys()
        else Quantity(d["total_bytes_estimate"], "B")
    )
    event, _ = DL_PROGRESS_WINDOW.read(timeout=20)
    if event == Sg.WIN_CLOSED:
        DL_PROGRESS_WINDOW.close()
        raise FileExistsError
    elif d["status"] == "downloading":
        if event == get_text(GuiField.cancel_button):
            DL_PROGRESS_WINDOW.close()
            raise ValueError
        progress_percent = (
            "-" if downloaded == "-" or total == 0 else int(downloaded / total * 100)
        )
        DL_PROGRESS_WINDOW["PROGINFOS1"].update(f"{progress_percent}%")
        DL_PROGRESS_WINDOW["-PROG-"].update(progress_percent)
        now = datetime.datetime.now()
        delta_ms = (now - TIME_LAST_UPDATE).seconds * 1000 + (
            now - TIME_LAST_UPDATE
        ).microseconds // 1000
        if delta_ms >= 200:
            DL_PROGRESS_WINDOW["PROGINFOS2"].update(
                f"{get_text(GuiField.ff_speed)}: {speed}"
            )
            TIME_LAST_UPDATE = now
    return
