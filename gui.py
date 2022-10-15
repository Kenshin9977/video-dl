from __future__ import annotations

import logging
import os
import platform
import traceback

import PySimpleGUI as Sg
from environs import Env
from yt_dlp import utils

from components_handlers.ytdlp_handler import video_dl, DL_PROG_WIN
from icon_base64 import ICON_BASE64
from lang import (
    GuiField,
    get_available_languages_name,
    get_current_language_name,
    get_text,
    set_current_language,
)
from utils.sys_utils import APP_VERSION

env = Env()
logger = logging.getLogger()
default_playlist_items_value = "1,2,4-10,12"


def video_dl_gui() -> None:
    """
    Start the GUI and run the app.
    """
    download_path = _get_default_download_path()
    Sg.theme("DarkGrey13")
    layout = _gen_layout(download_path)
    window = Sg.Window("Video-dl", layout=layout, icon=ICON_BASE64)

    while True:
        event, values = window.Read()
        if event in (Sg.WIN_CLOSED, "Exit"):
            break
        window["error"].update(visible=False)
        _fill_timecode(values, window)
        if event == "Start" or event == "End":
            _trim_checkbox(values, window, event)
        elif event == "AudioOnly":
            _audio_only_checkbox(values, window)
        elif event == "Lang":
            _change_language(values, window)
        elif event == "IsPlaylist":
            _update_playlist_index_state(
                values["IsPlaylist"], values["PlaylistItems"], window
            )
        elif event == "PlaylistItemsCheckbox":
            _update_playlist_index_input_state(
                values["PlaylistItemsCheckbox"], window
            )
        elif event == "dl":
            _run_video_dl(window, values)


def _run_video_dl(window: dict, values: dict) -> None:
    """
    Run video_dl backend and handles exceptions

    Args:
        window (dict): GUI window's dict
        values (dict): GUI values' dict
    """
    if values["Start"] and values["End"] and _check_timecode(values):
        window["error"].update(
            get_text(GuiField.incorrect_timestamp),
            visible=True,
            text_color="yellow",
        )
    elif values["path"] == "":
        window["error"].update(get_text(GuiField.missing_output), visible=True)
    else:
        window["error"].update(visible=False)
        # noinspection PyBroadException
        try:
            logger.debug("GUI's options selected %s", values)
            video_dl(values)
        except ValueError:
            logging.error(traceback.format_exc())
            window["error"].update(
                f"{get_text(GuiField.dl_cancel)}",
                visible=True,
                text_color="yellow",
            )
        except FileExistsError:
            window["error"].update(
                get_text(GuiField.dl_finish),
                visible=True,
                text_color="green",
            )
        except utils.DownloadError as e:
            logging.error(traceback.format_exc())
            window["error"].update(
                get_text(GuiField.error) + str(e),
                visible=True,
                text_color="red",
            )
            if DL_PROG_WIN:
                DL_PROG_WIN.close()
        except Exception as e:
            logging.error(traceback.format_exc())
            window["error"].update(
                f"{get_text(GuiField.dl_error)}\n{str(e)}\n"
                f"{traceback.format_exc()}",
                visible=True,
                text_color="red",
            )
        else:
            window["error"].update(
                get_text(GuiField.dl_finish),
                visible=True,
                text_color="green",
            )


def _gen_layout(default_download_path: str) -> list:
    """
    Generate the GUI's layout.

    Args:
        default_download_path (str): The default path to download to

    Returns:
        list: The GUI's layout
    """
    width_start = len(get_text(GuiField.start))
    width_end = len(get_text(GuiField.end))
    width_start_end = max(width_start, width_end) + 3
    layout = [
        [
            Sg.Combo(
                get_available_languages_name(),
                default_value=get_current_language_name(),
                enable_events=True,
                readonly=True,
                key="Lang",
            ),
            Sg.Text(f"v{APP_VERSION}", justification="right", expand_x=True),
        ],
        [Sg.Text(get_text(GuiField.link), key="TextLink")],
        [Sg.Input(key="url")],
        [
            Sg.Checkbox(
                get_text(GuiField.is_playlist),
                default=False,
                checkbox_color="black",
                enable_events=True,
                key="IsPlaylist",
            )
        ],
        [
            Sg.Checkbox(
                get_text(GuiField.playlist_items),
                default=False,
                checkbox_color="black",
                disabled=True,
                enable_events=True,
                key="PlaylistItemsCheckbox",
            ),
            Sg.Input(
                default_playlist_items_value,
                size=(24, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="PlaylistItems",
            ),
        ],
        [Sg.Text(get_text(GuiField.destination), key="TextDestination")],
        [
            Sg.Input(default_download_path, key="path"),
            Sg.FolderBrowse(button_text="..."),
        ],
        [
            Sg.Checkbox(
                get_text(GuiField.start),
                default=False,
                checkbox_color="black",
                enable_events=True,
                key="Start",
                size=(width_start_end, 1),
            ),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="sH",
                enable_events=True,
                default_text="00",
            ),
            Sg.Text(":", size=(1, 1), pad=(0, 0)),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="sM",
                enable_events=True,
                default_text="00",
            ),
            Sg.Text(":", size=(1, 1), pad=(0, 0)),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="sS",
                enable_events=True,
                default_text="00",
            ),
        ],
        [
            Sg.Checkbox(
                get_text(GuiField.end),
                default=False,
                checkbox_color="black",
                enable_events=True,
                key="End",
                size=(width_start_end, 1),
            ),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="eH",
                enable_events=True,
                default_text="00",
            ),
            Sg.Text(":", size=(1, 1), pad=(0, 0)),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="eM",
                enable_events=True,
                default_text="00",
            ),
            Sg.Text(":", size=(1, 1), pad=(0, 0)),
            Sg.Input(
                size=(4, 1),
                disabled=True,
                disabled_readonly_background_color="gray",
                key="eS",
                enable_events=True,
                default_text="00",
            ),
        ],
        [
            Sg.Checkbox(
                get_text(GuiField.audio_only),
                default=False,
                checkbox_color="black",
                enable_events=True,
                key="AudioOnly",
            ),
            Sg.Checkbox(
                get_text(GuiField.song_only),
                default=False,
                checkbox_color="black",
                disabled=True,
                tooltip=get_text(GuiField.song_only_tooltip),
                enable_events=True,
                key="SongOnly",
            ),
        ],
        [
            Sg.Combo(
                [
                    "AAC",
                    "ALAC",
                    "BEST",
                    "FLAC",
                    "OPUS",
                    "MP3",
                    "VORBIS",
                    "WAV",
                ],
                default_value="MP3",
                readonly=True,
                key="TargetACodec",
                size=(8, 1),
                disabled=True,
            ),
            Sg.Text(get_text(GuiField.acodec), key="TextACodec"),
        ],
        [
            Sg.Checkbox(
                get_text(GuiField.subtitles),
                default=False,
                checkbox_color="black",
                enable_events=True,
                key="Subtitles",
            )
        ],
        [
            Sg.Combo(
                [
                    "4320p",
                    "2160p",
                    "1440p",
                    "1080p",
                    "720p",
                    "480p",
                    "360p",
                    "240p",
                    "144p",
                ],
                default_value="1080p",
                readonly=True,
                key="MaxHeight",
                size=(8, 1),
            ),
            Sg.Text(get_text(GuiField.quality), key="TextQuality"),
        ],
        [
            Sg.Combo(
                ["x264", "x265", "ProRes"],
                default_value="x264",
                readonly=True,
                key="TargetVCodec",
                size=(8, 1),
            ),
            Sg.Text(get_text(GuiField.vcodec), key="TextVCodec"),
        ],
        [
            Sg.Combo(
                ["60", "30"],
                default_value="60",
                readonly=True,
                key="MaxFPS",
                size=(8, 1),
            ),
            Sg.Text(get_text(GuiField.framerate), key="TextFramerate"),
        ],
        [
            Sg.Combo(
                [
                    "None",
                    "Brave",
                    "Chrome",
                    "Chromium",
                    "Edge",
                    "Firefox",
                    "Opera",
                    "Safari",
                    "Vivaldi",
                ],
                default_value="None",
                readonly=True,
                key="Browser",
                size=(8, 1),
            ),
            Sg.Text(get_text(GuiField.cookies), key="TextCookies"),
        ],
        [
            Sg.Button(
                get_text(GuiField.dl_button), enable_events=True, key="dl"
            ),
            Sg.Text(key="error", text_color="red", visible=False),
        ],
    ]
    return layout


def _audio_only_checkbox(values: dict, window: Sg.Window) -> None:
    """
    Handles the GUI depending of the audio_only's checkbox state.

    Args:
        values (dict): Values entered in the GUI
        window (Sg.Window): GUI's window
    """
    audio_checkbox = values["AudioOnly"]
    window["MaxHeight"].update(disabled=audio_checkbox)
    window["MaxFPS"].update(disabled=audio_checkbox)
    window["TargetVCodec"].update(disabled=audio_checkbox)
    window["TargetACodec"].update(disabled=not audio_checkbox)
    window["SongOnly"].update(disabled=not audio_checkbox)


def _fill_timecode(values: dict, window: Sg.Window) -> None:
    """
    Handles the start and end's content.

    Args:
        values (dict): Values entered in the GUI
        window (Sg.Window): GUI's window
    """
    values2check = ["sH", "sM", "sS", "eH", "eM", "eS"]
    for value in values2check:
        for char in values[value]:
            if char not in "0123456789":
                window[value].update(values[value].replace(char, ""))
                values[value] = values[value].replace(char, "")
        if len(values[value]) > 2:
            window[value].update(values[value][1:])
            values[value] = values[value][1:]
        elif len(values[value]) == 1:
            window[value].update("0" + values[value][0])
            values[value] = "0" + values[value][0]
        elif len(values[value]) == 0:
            window[value].update("00")
            values[value] = "00"
        if (
            value != "sH"
            and value != "eH"
            and len(values[value]) > 0
            and values[value] != " "
            and int(values[value]) > 59
        ):
            window[value].update("0" + values[value][-1])
            values[value] = "0" + values[value][-1]


def _check_timecode(values: dict) -> bool:
    """
    Check the validity of the start and end's content.

    Args:
        values (dict): Values entered in the GUI

    Returns:
        bool: Whether or not the values entered are correct
    """
    sh, sm, ss = int(values["sH"]), int(values["sM"]), int(values["sS"])
    eh, em, es = int(values["eH"]), int(values["eM"]), int(values["eS"])
    return (
        sh > eh
        or (sh == eh and sm > em)
        or (sh == eh and sm == em and ss >= es)
    )


def _trim_checkbox(values: dict, window: Sg.Window, start_or_end: str) -> None:
    """
    Handles the start and end timecode availability depending of the start and
    end checkbox.

    Args:
        values (dict): Values entered in the GUI
        window (Sg.Window): GUI's window
        start_or_end (str): The value of the line to update
    """
    disabled = not values[start_or_end]
    if start_or_end == "Start":
        window["sH"].update(disabled=disabled, value="00")
        window["sM"].update(disabled=disabled, value="00")
        window["sS"].update(disabled=disabled, value="00")
    elif start_or_end == "End":
        window["eH"].update(disabled=disabled)
        window["eM"].update(disabled=disabled)
        window["eS"].update(disabled=disabled)


def _get_default_download_path() -> str:
    """
    Get the default download folder path.

    Returns:
        str: Default download folder path
    """
    if platform.system() == "Windows":
        import winreg

        sub_key = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:  # type: ignore  # noqa
            location = winreg.QueryValueEx(key, downloads_guid)[0]  # type: ignore  # noqa
        return location
    download_path = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(download_path):
        return download_path
    else:
        return ""


def _change_language(values: dict, window: Sg.Window) -> None:
    """
    Updates current language and update the window's text fields.

    Args:
        values (dict): Values selected in the GUI
        window (Sg.Window): GUI's window
    """
    set_current_language(values["Lang"])
    _update_text_lang(window)


def _update_playlist_index_state(
    checked: bool, playlist_items: str, window: Sg.Window
) -> None:
    """
    Update the GUI depending of the playlist option checkbox state.

    Args:
        checked (bool): Whether the playlist option is checked or not
        playlist_items (str): The playlist items listed
        window (Sg.Window): GUI's window
    """

    window["PlaylistItemsCheckbox"].update(disabled=not checked)

    window["Start"].update(disabled=checked)
    window["End"].update(disabled=checked)

    if checked:
        # Set start and end check to false values
        window["Start"].update(value=False)
        window["End"].update(value=False)

        # Reset start and end timers values
        window["sH"].update(disabled=True, value="00")
        window["sM"].update(disabled=True, value="00")
        window["sS"].update(disabled=True, value="00")
        window["eH"].update(disabled=True, value="00")
        window["eM"].update(disabled=True, value="00")
        window["eS"].update(disabled=True, value="00")
    elif not checked:
        window["PlaylistItems"].update(disabled=True)
        window["PlaylistItemsCheckbox"].update(value=False, disabled=True)
    elif playlist_items == "":
        window["PlaylistItems"].update(
            value=default_playlist_items_value if not checked else ""
        )


def _update_playlist_index_input_state(
    checked: bool, window: Sg.Window
) -> None:
    """
    Update playlist index state depending of the playlist checkbox state.

    Args:
        checked (bool): Whether or not Playlist is checked
        window (Sg.Window): GUI's window
    """
    window["PlaylistItems"].update(
        value="" if checked else default_playlist_items_value,
        disabled=not checked,
    )


def _update_text_lang(window: Sg.Window) -> None:
    """
    Update the text of each element on the layout.
    Note: Checkboxes elements need "text=" to be specified.

    Args:
        window (Sg.Window): GUI's window
    """
    window["TextLink"].update(get_text(GuiField.link))
    window["IsPlaylist"].update(text=get_text(GuiField.is_playlist))
    window["PlaylistItemsCheckbox"].update(
        text=get_text(GuiField.playlist_items)
    )
    window["TextDestination"].update(get_text(GuiField.destination))
    width_start = len(get_text(GuiField.start))
    width_end = len(get_text(GuiField.end))
    width_start_end = (max(width_start, width_end) + 3, 1)
    window["Start"].update(text=get_text(GuiField.start))
    window["End"].update(text=get_text(GuiField.end))
    window["Start"].set_size(width_start_end)
    window["End"].set_size(width_start_end)
    window["TextQuality"].update(get_text(GuiField.quality))
    window["TextFramerate"].update(get_text(GuiField.framerate))
    window["AudioOnly"].update(text=get_text(GuiField.audio_only))
    window["SongOnly"].update(text=get_text(GuiField.song_only))
    window["SongOnly"].set_tooltip(get_text(GuiField.song_only_tooltip))
    window["Subtitles"].update(text=get_text(GuiField.subtitles))
    window["TextACodec"].update(get_text(GuiField.acodec))
    window["TextCookies"].update(get_text(GuiField.cookies))
    window["dl"].update(get_text(GuiField.dl_button))
