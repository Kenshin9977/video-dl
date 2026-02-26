from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
import traceback
from datetime import datetime
from typing import TYPE_CHECKING

import flet as ft
from darkdetect import isDark
from flet import (
    Button,
    Checkbox,
    Colors,
    Column,
    Dropdown,
    ExpansionTile,
    FilePicker,
    FontWeight,
    Icon,
    Icons,
    MainAxisAlignment,
    PopupMenuButton,
    PopupMenuItem,
    ProgressBar,
    Row,
    Switch,
    Text,
    TextAlign,
    TextField,
    TextStyle,
    dropdown,
)
from quantiphy import InvalidNumber, Quantity

from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

from core.download import create_ydl, download
from core.exceptions import (
    DownloadCancelled,
    FFmpegNoValidEncoderFound,
    PlaylistNotFound,
)
from gui.config import (
    CK_ACODEC,
    CK_AUDIO_ONLY,
    CK_COOKIES,
    CK_DEST_FOLDER,
    CK_FRAMERATE,
    CK_INDICES,
    CK_LANGUAGE,
    CK_NLE_READY,
    CK_ORIGINAL,
    CK_PLAYLIST,
    CK_SONG_ONLY,
    CK_SUBTITLES,
    CK_THEME,
    CK_VCODEC,
    CK_VQUALITY,
    USER_OPTIONS,
    VideodlConfig,
)
from gui.options import ACODECS, BROWSERS, FRAMERATE, QUALITY, VCODECS
from i18n.lang import GuiField as GF
from i18n.lang import (
    get_available_languages_name,
    get_current_language_name,
    set_current_language,
)
from i18n.lang import get_text as gt
from sys_vars import ARIA2C_PATH, FF_PATH, QJS_PATH
from utils.parse_util import simple_traverse, validate_url
from utils.sponsor_block_dict import CATEGORIES
from utils.sys_utils import APP_VERSION, PLATFORM, get_default_download_path

if TYPE_CHECKING:
    from flet import ControlEvent, Page


logger = logging.getLogger("videodl")


DISABLED_COLOR = Colors.ON_INVERSE_SURFACE


class VideodlApp:
    def __init__(self, page: Page):
        is_dark = bool(isDark())
        self.page = page
        self.page.title = "Video-dl"
        self.page.theme_mode = "dark" if is_dark else "light"
        self._height_collapsed = 460
        self._height_advanced = 290
        self._height_download = 120
        self.page.window.height = self._height_collapsed
        self.page.window.min_height = self._height_collapsed
        self.page.window.width = gt(GF.width)
        self.page.window.min_width = gt(GF.width)
        self.download_disabled_reason = None
        self.default_indices_value = "1,2,4-10,12"
        self.file_picker = FilePicker()
        self.page.services.append(self.file_picker)
        self.media_link = TextField(
            label=gt(GF.link),
            autofocus=True,
            dense=True,
            on_change=self._url_change,
            on_submit=self._url_submit,
            on_blur=self._url_submit,
        )
        self.video_preview = Text(
            visible=False,
            size=12,
            color=Colors.ON_SURFACE_VARIANT,
        )
        self.download_path_text = Text(
            get_default_download_path(),
            data=CK_DEST_FOLDER,
            expand=True,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.download_path = Button(
            content=Icon(Icons.FOLDER_OPEN),
            tooltip=gt(GF.destination_folder),
            on_click=self._pick_directory,
        )
        self._current_language_name = get_current_language_name()
        self.language_button = PopupMenuButton(
            content=Text(self._current_language_name, size=24),
            items=self._build_language_items(),
        )
        self._is_dark = is_dark
        self._theme_switch = Switch(
            value=is_dark,
            data=CK_THEME,
            on_change=self._change_theme,
        )
        self.theme = Row(
            controls=[
                Icon(Icons.LIGHT_MODE, size=18),
                self._theme_switch,
                Icon(Icons.DARK_MODE, size=18),
            ],
            spacing=0,
        )

        self.version_number = Text(value=f"v{APP_VERSION}", text_align=TextAlign.RIGHT)
        self.playlist = Checkbox(
            label=gt(GF.is_playlist),
            data=CK_PLAYLIST,
            on_change=self._playlist_checkbox_change,
        )
        self.indices = Checkbox(
            label=gt(GF.playlist_items),
            data=CK_INDICES,
            disabled=True,
            on_change=self._index_checkbox_change,
        )
        self.indices_selected = TextField(
            label=gt(GF.indices_selected),
            value=self.default_indices_value,
            width=200,
            disabled=True,
            text_style=TextStyle(color=DISABLED_COLOR),
        )
        self.quality = Dropdown(
            label=gt(GF.quality),
            data=CK_VQUALITY,
            value="1080p",
            width=120,
            dense=True,
            tooltip=gt(GF.quality_tooltip),
            on_select=self._option_change,
            options=[dropdown.Option(quality) for quality in QUALITY],
        )
        self.framerate = Dropdown(
            label=gt(GF.framerate),
            data=CK_FRAMERATE,
            value="60",
            width=120,
            dense=True,
            tooltip=gt(GF.framerate_tooltip),
            on_select=self._option_change,
            options=[dropdown.Option(framerate) for framerate in FRAMERATE],
        )
        self.nle_ready = Switch(
            label=gt(GF.nle_ready),
            data=CK_NLE_READY,
            value=True,
            tooltip=gt(GF.nle_ready_tooltip),
            on_change=self._nle_ready_change,
        )
        self.audio_only = Checkbox(
            label=gt(GF.audio_only),
            data=CK_AUDIO_ONLY,
            on_change=self._audio_only_checkbox_change,
        )
        self.song_only = Checkbox(
            label=gt(GF.song_only),
            data=CK_SONG_ONLY,
            disabled=True,
            tooltip=gt(GF.song_only_tooltip),
            on_change=self._option_change,
        )
        self.subtitles = Checkbox(
            label=gt(GF.subtitles),
            data=CK_SUBTITLES,
            on_change=self._option_change,
        )
        self.cookies = Dropdown(
            label=gt(GF.login_from),
            data=CK_COOKIES,
            value=gt(GF.login_from_none),
            width=150,
            dense=True,
            tooltip=gt(GF.login_from_tooltip),
            on_select=self._option_change,
            options=[dropdown.Option(browser) for browser in BROWSERS],
        )
        self.video_codec = Dropdown(
            label=gt(GF.vcodec),
            data=CK_VCODEC,
            value="Auto",
            width=150,
            tooltip=gt(GF.vcodec_auto_tooltip),
            on_select=self._codec_change,
            options=[dropdown.Option(vcodec) for vcodec in VCODECS],
        )
        self.audio_codec = Dropdown(
            label=gt(GF.acodec),
            data=CK_ACODEC,
            value="Auto",
            width=150,
            tooltip=gt(GF.acodec_auto_tooltip),
            on_select=self._codec_change,
            options=[dropdown.Option(acodec) for acodec in ACODECS],
        )
        self.encode_indicator = Icon(
            Icons.CHECK_CIRCLE,
            color="green",
            size=20,
            tooltip="",
            visible=False,
        )
        self.original_checkbox = Checkbox(
            label=gt(GF.original),
            tooltip=gt(GF.original_tooltip),
            data=CK_ORIGINAL,
            on_change=self._original_change,
        )
        self.original_video_dropdown = Dropdown(
            label=gt(GF.original_video_placeholder),
            width=180,
            dense=True,
            disabled=True,
            options=[],
        )
        self.original_audio_dropdown = Dropdown(
            label=gt(GF.original_audio_placeholder),
            width=180,
            dense=True,
            disabled=True,
            options=[],
        )
        self._video_formats = []
        self._audio_formats = []
        timecode_common_kwargs = {
            "value": "00",
            "max_length": 2,
            "dense": True,
            "width": 60,
            "disabled": True,
            "on_change": self._timecode_change,
            "border_color": "white" if is_dark else "black",
            "counter_style": TextStyle(size=0, color=DISABLED_COLOR),
            "on_focus": self._textfield_focus,
        }
        self.start_checkbox = Checkbox(
            label="Start",
            on_change=self._start_checkbox_change,
        )
        self.start_h = TextField(**timecode_common_kwargs)
        self.start_m = TextField(**timecode_common_kwargs)
        self.start_s = TextField(**timecode_common_kwargs)
        self.start_controls = [self.start_h, self.start_m, self.start_s]
        self.end_checkbox = Checkbox(
            label="End",
            on_change=self._end_checkbox_change,
        )
        self.end_h = TextField(**timecode_common_kwargs)
        self.end_m = TextField(**timecode_common_kwargs)
        self.end_s = TextField(**timecode_common_kwargs)
        self.end_controls = [self.end_h, self.end_m, self.end_s]
        self.advanced_section = ExpansionTile(
            title=gt(GF.advanced),
            expanded=False,
            maintain_state=True,
            on_change=self._advanced_toggle,
            controls_padding=ft.padding.only(top=10, left=10, right=10),
            controls=[
                Row(
                    controls=[
                        self.video_codec,
                        self.audio_codec,
                        self.encode_indicator,
                    ]
                ),
                Row(
                    controls=[
                        self.original_checkbox,
                        self.original_video_dropdown,
                        self.original_audio_dropdown,
                    ]
                ),
                ft.Container(height=8),
                Row(controls=[self.playlist, self.indices, self.indices_selected]),
                Row(controls=[self.subtitles, self.cookies]),
                Row(
                    controls=[
                        self.start_checkbox,
                        self.start_h,
                        Text(":"),
                        self.start_m,
                        Text(":"),
                        self.start_s,
                    ],
                    height=50,
                ),
                Row(
                    controls=[
                        self.end_checkbox,
                        self.end_h,
                        Text(":"),
                        self.end_m,
                        Text(":"),
                        self.end_s,
                    ],
                    height=50,
                ),
            ],
        )
        self.download_button = Button(
            content="Download", on_click=self._download_clicked, disabled=True, tooltip=gt(GF.invalid_url)
        )
        self.cancel_button = Button(
            content=gt(GF.cancel_button),
            on_click=self._cancel_clicked,
            disabled=True,
            visible=False,
        )
        self.open_folder_button = Button(
            content=Icon(Icons.FOLDER_OPEN),
            tooltip=gt(GF.open_folder),
            on_click=self._open_folder_clicked,
            visible=False,
        )
        self.download_status_text = Text(visible=False)
        self.download_progress_text = Text(gt(GF.download))
        self.process_progress_text = Text(gt(GF.process))
        self.download_progress_bar = ProgressBar(width=350)
        self.process_progress_bar = ProgressBar(width=350, color="red")
        self.download_progress = Column(
            [self.download_progress_text, self.download_progress_bar],
            visible=False,
        )
        self.process_progress = Column(
            [self.process_progress_text, self.process_progress_bar],
            visible=False,
        )
        self.ydl_opts: dict = {}
        self.download_last_update: datetime = datetime.now()
        self.download_last_speed: str = ""
        self.process_last_update: datetime = datetime.now()
        self.process_last_speed: str = ""
        self.download_progress_percent: float = 0
        self.process_progress_percent: float = 0
        self._ui_dirty = threading.Event()
        self._download_done = threading.Event()
        self._cancel_requested = threading.Event()
        self._preparing = False
        self._download_counter = ""
        self._url_queue: list[str] = []
        self.queue_button = Button(
            content=Icon(Icons.ADD),
            tooltip=gt(GF.queue_button_tooltip),
            on_click=self._open_queue_dialog,
        )
        self._queue_textfield = TextField(
            multiline=True,
            min_lines=5,
            max_lines=10,
            hint_text=gt(GF.queue_dialog_hint),
            expand=True,
        )
        self.tomlconfig = VideodlConfig()

    async def _pick_directory(self, e):
        result = await self.file_picker.get_directory_path()
        if result:
            self.download_path_text.value = result
            self.tomlconfig.update(CK_DEST_FOLDER, result)
            self.page.update()

    def _gen_ydl_opts(self) -> dict:
        """
        Generate yt-dlp options' dictionnary.

        Args:
            opts (dict): Options selected in the GUI

        Returns:
            dict: yt-dlp options
        """
        self.ydl_opts = {"verbose": True}
        if QJS_PATH:
            self.ydl_opts["js_runtimes"] = {"quickjs": {"path": QJS_PATH}}
        self._gen_file_opts()
        self._gen_av_opts()
        self._gen_ffmpeg_opts()
        self._gen_subtitles_opts()
        self._gen_browser_opts()
        self._gen_sponsor_block_opts()
        # Use aria2c for faster downloads when available and trim is not active
        if ARIA2C_PATH and "external_downloader" not in self.ydl_opts:
            self.ydl_opts["external_downloader"] = {"default": ARIA2C_PATH}
        return self.ydl_opts

    def _gen_file_opts(self):
        """
        Generate yt-dlp file's options
        """
        self.ydl_opts.update(
            {
                "noplaylist": not self.playlist.value,
                "ignoreerrors": "only_download" if self.playlist.value else False,
                "overwrites": True,
                "trim_file_name": 250,
                "outtmpl": os.path.join(
                    f"{self.download_path_text.value}",
                    "%(title).100s - %(uploader)s.%(ext)s",
                ),
                "progress_hooks": [self._update_download_bar],
                "postprocessor_hooks": [self._update_process_bar],
            }
        )
        if self.indices.value:
            self.ydl_opts["playlist_items"] = self.indices_selected.value or 1

        if FF_PATH.get("ffmpeg") != "ffmpeg":
            self.ydl_opts["ffmpeg_location"] = FF_PATH.get("ffmpeg")

    def _gen_av_opts(self):
        """
        Generate yt-dlp options for the audio and the video both for their
        search filters, their downloader and their post process.
        """
        if self.original_checkbox.value:
            self._gen_original_opts()
            return
        if self.audio_only.value:
            format_opt = "ba/ba*"
            acodec_val = self.audio_codec.value
            if acodec_val != "Auto":
                format_opt = f"ba[acodec*={acodec_val}]/{format_opt}"
            postprocessor = {"key": "FFmpegExtractAudio"}
            if acodec_val != "Auto":
                postprocessor["preferredcodec"] = acodec_val
            self.ydl_opts.update(
                {
                    "extract_audio": True,
                    "postprocessors": [postprocessor],
                }
            )
        else:
            resolution = self.quality.value[:-1]
            vcodec_re_str = "vcodec~='avc1|h264'"
            acodec_re_str = "acodec~='aac|mp3|mp4a'"
            format_opt = (
                f"((bv[{vcodec_re_str}][height={resolution}]/bv[height={resolution}]/bv)+(ba[{acodec_re_str}]/ba))/b"
            )
            self.ydl_opts.update(
                {
                    "format_sort": [
                        f"res:{resolution}",
                        f"fps:{self.framerate.value}",
                    ],
                    "merge_output_format": "mp4",
                }
            )
        self.ydl_opts["format"] = format_opt

    def _gen_original_opts(self):
        """Generate yt-dlp options for Original mode with specific stream selection."""
        video_id = self.original_video_dropdown.value
        audio_id = self.original_audio_dropdown.value
        if self.audio_only.value and audio_id:
            format_opt = audio_id
        elif video_id and audio_id:
            format_opt = f"{video_id}+{audio_id}"
        elif video_id:
            format_opt = f"{video_id}+ba"
        elif audio_id:
            format_opt = f"bv+{audio_id}"
        else:
            # No streams selected — fallback to best
            format_opt = "bv+ba/b"
        self.ydl_opts["format"] = format_opt
        self.ydl_opts["merge_output_format"] = "mp4"

    def _gen_ffmpeg_opts(self):
        """
        Generate the dictionnary for yt-dlp ffmpeg options
        """
        start_values = [ctrl.value for ctrl in self.start_controls]
        start_timecode = ":".join(start_values)
        end_values = [ctrl.value for ctrl in self.end_controls]
        end_timecode = ":".join(end_values)
        if self.start_checkbox.value or self.end_checkbox.value:
            start = start_timecode if self.start_checkbox.value else "00:00:00"
            ffmpeg_args = ["-ss", start]
            if self.end_checkbox.value:
                ffmpeg_args.extend(["-to", end_timecode])
            self.ydl_opts.update(
                {
                    "external_downloader": "ffmpeg",
                    "external_downloader_args": {"ffmpeg_i": ffmpeg_args},
                }
            )
            if PLATFORM == "Windows":
                self.ydl_opts.update({"ffmpeg_location": FF_PATH.get("ffmpeg")})
        logger.info(f"Options passed to yt-dlp are the following:\n{self.ydl_opts}")

    def _gen_subtitles_opts(self):
        """
        Generate the dictionnary for yt-dlp subtitles options
        """
        if self.subtitles.value:
            self.ydl_opts["subtitleslangs"] = ["all"]
            self.ydl_opts["writesubtitles"] = True

    def _gen_browser_opts(self):
        """
        Generate the dictionnary for yt-dlp cookies option
        """
        if self.cookies.value != gt(GF.login_from_none):
            self.ydl_opts["cookiesfrombrowser"] = [self.cookies.value.lower()]

    def _gen_sponsor_block_opts(self):
        if self.song_only.value:
            categories = CATEGORIES.keys()
            self.ydl_opts.setdefault("postprocessors", []).extend(
                [
                    {"key": "SponsorBlock", "when": "pre_process"},
                    {
                        "key": "ModifyChapters",
                        "SponsorBlock": categories,
                    },
                ]
            )

    def _update_download_bar(self, d: dict):
        if self._cancel_requested.is_set():
            raise YtdlpDownloadCancelled
        # Hide preparation status once actual download starts
        force = False
        if self._preparing:
            self._preparing = False
            self.download_status_text.visible = False
            force = True
        (
            self.download_last_update,
            self.download_last_speed,
            self.download_progress_percent,
        ) = self._update_bar(
            d,
            "downloaded_bytes",
            self.download_last_update,
            self.download_last_speed,
            self.download_progress_bar,
            self.download_progress_text,
            self.download_progress_percent,
            force_update=force,
        )

    def _update_process_bar(self, d: dict):
        (
            self.process_last_update,
            self.process_last_speed,
            self.process_progress_percent,
        ) = self._update_bar(
            d,
            "processed_bytes",
            self.process_last_update,
            self.process_last_speed,
            self.process_progress_bar,
            self.process_progress_text,
            self.process_progress_percent,
        )

    def _update_bar(
        self,
        d: dict,
        bytes_fieldname: str,
        time_last_update: datetime,
        last_speed: str,
        progress_bar: ProgressBar,
        progress_text: Text,
        last_progress_percent: float,
        force_update: bool = False,
    ):
        if self._cancel_requested.is_set():
            return time_last_update, last_speed, last_progress_percent

        speed = self._parse_speed(d, bytes_fieldname)
        downloaded = self._parse_quantity(d.get(bytes_fieldname))
        total = self._parse_quantity(d.get("total_bytes")) or self._parse_quantity(d.get("total_bytes_estimate"))
        progress_float, last_progress_percent = self._compute_progress(
            d.get("progress_float"), downloaded, total, last_progress_percent
        )

        progress_bar.value = progress_float
        status = d.get("status")
        if status == "finished":
            force_update = True
        time_elapsed = datetime.now() - time_last_update
        delta_ms = time_elapsed.seconds * 1_000 + time_elapsed.microseconds // 1_000
        if force_update or delta_ms >= 250:
            last_speed = speed
            time_last_update = datetime.now()
            action = d.get("action") or (gt(GF.download) if bytes_fieldname == "downloaded_bytes" else gt(GF.process))
            n_current = simple_traverse(d, ("info_dict", "playlist_autonumber"))
            n_entries = simple_traverse(d, ("info_dict", "n_entries"))
            progress_str = f"{action} {int(progress_float * 100)}% {speed}"
            if self._download_counter and bytes_fieldname == "downloaded_bytes":
                progress_str += f" {self._download_counter}"
            elif n_current and n_entries > 1:
                progress_str += f"({n_current}/{n_entries})"
            progress_text.value = progress_str
            self._ui_dirty.set()
        return time_last_update, last_speed, last_progress_percent

    @staticmethod
    def _parse_speed(d: dict, bytes_fieldname: str) -> str:
        try:
            raw_speed = d.get("speed")
            if bytes_fieldname == "downloaded_bytes":
                return Quantity(raw_speed, "B/s").render(prec=2)
            return Quantity(raw_speed / 8, "B/s").render(prec=2) if raw_speed else "-"
        except (InvalidNumber, TypeError):
            return "-"

    @staticmethod
    def _parse_quantity(value):
        try:
            return Quantity(value, "B")
        except (InvalidNumber, TypeError):
            return None

    @staticmethod
    def _compute_progress(progress_float, downloaded, total, last_progress_percent):
        if progress_float is not None:
            return progress_float, last_progress_percent
        try:
            progress_float = downloaded / total
            progress_float = max(0, min(progress_float, 0.99))
            return progress_float, progress_float
        except (ZeroDivisionError, TypeError):
            return last_progress_percent, last_progress_percent

    def _timecodes_are_valid(self) -> bool:
        if self.start_checkbox.value:
            sh, sm, ss = VideodlApp._timecode_is_valid(self.start_controls)
            if (sh, sm, ss) == (-1, -1, -1):
                return False
        if self.end_checkbox.value:
            eh, em, es = VideodlApp._timecode_is_valid(self.end_controls)
            if (eh, em, es) == (-1, -1, -1):
                return False
        if self.start_checkbox.value and self.end_checkbox.value:
            return sh < eh or (sh == eh and sm < em) or (sh == eh and sm == em and ss < es)
        return True

    @staticmethod
    def _timecode_is_valid(ctrls: list) -> tuple[int, int, int]:
        try:
            h_int, m_int, s_int = [int(ctr.value) for ctr in ctrls]
        except ValueError:
            return -1, -1, -1
        if m_int >= 60 or s_int >= 60:
            return -1, -1, -1
        return h_int, m_int, s_int

    def _build_language_items(self):
        return [
            PopupMenuItem(Text(name, size=20), on_click=self._on_language_click)
            for name in get_available_languages_name()
        ]

    def _on_language_click(self, e):
        lang_name = e.control.content.value
        self._current_language_name = lang_name
        self.language_button.content = Text(lang_name, size=24)
        self.language_button.items = self._build_language_items()
        self.tomlconfig.update(CK_LANGUAGE, lang_name)
        self._refresh_labels()
        self.page.update()

    def _refresh_labels(self):
        set_current_language(self._current_language_name)
        self._theme_switch.tooltip = gt(GF.theme)
        self.media_link.label = gt(GF.link)
        self.download_path.tooltip = gt(GF.destination_folder)
        self.playlist.label = gt(GF.is_playlist)
        self.indices.label = gt(GF.playlist_items)
        self.indices_selected.label = gt(GF.indices_selected)
        self.video_codec.label = gt(GF.vcodec)
        self.quality.label = gt(GF.quality)
        self.quality.tooltip = gt(GF.quality_tooltip)
        self.framerate.label = gt(GF.framerate)
        self.framerate.tooltip = gt(GF.framerate_tooltip)
        self.audio_codec.label = gt(GF.acodec)
        self._update_codec_tooltips()
        self.original_checkbox.label = gt(GF.original)
        self.original_checkbox.tooltip = gt(GF.original_tooltip)
        self.original_video_dropdown.label = gt(GF.original_video_placeholder)
        self.original_audio_dropdown.label = gt(GF.original_audio_placeholder)
        self.nle_ready.label = gt(GF.nle_ready)
        self.nle_ready.tooltip = gt(GF.nle_ready_tooltip)
        self.audio_only.label = gt(GF.audio_only)
        self.song_only.label = gt(GF.song_only)
        self.song_only.tooltip = gt(GF.song_only_tooltip)
        self.start_checkbox.label = gt(GF.start)
        self.end_checkbox.label = gt(GF.end)
        self.subtitles.label = gt(GF.subtitles)
        self.cookies.label = gt(GF.login_from)
        self.cookies.options[0].text = gt(GF.login_from_none)
        self.cookies.tooltip = gt(GF.login_from_tooltip)
        self.open_folder_button.tooltip = gt(GF.open_folder)
        self.queue_button.tooltip = gt(GF.queue_button_tooltip)
        self._queue_textfield.hint_text = gt(GF.queue_dialog_hint)
        self.advanced_section.title = gt(GF.advanced)
        self.download_button.content = gt(GF.download)
        self.cancel_button.content = gt(GF.cancel_button)
        self.download_progress.controls[0].value = gt(GF.download)
        self.process_progress.controls[0].value = gt(GF.process)
        self.page.window.width = gt(GF.width)
        self.page.window.min_width = gt(GF.width)
        if self.download_disabled_reason is not None:
            self.download_button.tooltip = gt(self.download_disabled_reason)

    def _change_theme(self, e):
        self._is_dark = e.control.value
        self._change_attribute_based_on_theme(self._is_dark)
        self.tomlconfig.update(e.control.data, self._is_dark)
        self.page.update()

    def _change_attribute_based_on_theme(self, dark: bool):
        new_theme, border = ("dark", "white") if dark else ("light", "black")
        self.page.theme_mode = new_theme
        for control in self.start_controls + self.end_controls:
            control.border_color = border

    def _playlist_checkbox_change(self, e):
        playlist: bool = e.control.value
        self.indices.disabled = not playlist
        if not playlist:
            self.indices.value = False
            self.indices_selected.disabled = not playlist
            self.tomlconfig.update(CK_INDICES, False)
        # Original not available for playlists
        if playlist:
            self.original_checkbox.value = False
            self._apply_original_state(False)
            self.tomlconfig.update(CK_ORIGINAL, False)
        self.original_checkbox.disabled = playlist
        self._update_encode_indicator()
        self.tomlconfig.update(e.control.data, e.control.value)
        # Re-fetch preview with updated noplaylist setting
        url = self.media_link.value
        if url and validate_url(url):
            self._clear_original_dropdowns()
            self._fetch_video_preview(url)
        self.page.update()

    def _index_checkbox_change(self, e):
        self._index_change()
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _index_change(self):
        self.indices_selected.disabled = not self.indices.value
        if self.indices.value:
            self.indices_selected.text_style = TextStyle(weight=FontWeight.BOLD, color=Colors.INVERSE_SURFACE)
            if self.indices_selected.value == self.default_indices_value:
                self.indices_selected.value = ""
        else:
            self.indices_selected.text_style = TextStyle(color=DISABLED_COLOR)

    def _url_change(self, e):
        self._url_validate(self.media_link.value)

    def _url_submit(self, e):
        self._url_validate(self.media_link.value)

    def _url_validate(self, url):
        self._clear_original_dropdowns()
        if not url:
            self.media_link.border_color = None
            self.video_preview.visible = False
            if self._url_queue:
                self._enable_download_button()
            else:
                self._disable_download_button(GF.invalid_url)
        elif validate_url(url):
            self.media_link.border_color = "green"
            if self._timecodes_are_valid():
                self._enable_download_button()
            else:
                self._disable_download_button(GF.incorrect_timestamp)
            threading.Thread(target=self._fetch_video_preview, args=(url,), daemon=True).start()
        else:
            self.media_link.border_color = "red"
            self.video_preview.visible = False
            self._disable_download_button(GF.invalid_url)
        self.page.update()

    def _clear_original_dropdowns(self):
        self._video_formats = []
        self._audio_formats = []
        self.original_video_dropdown.options = []
        self.original_audio_dropdown.options = []
        self.original_video_dropdown.value = None
        self.original_audio_dropdown.value = None

    def _fetch_video_preview(self, url):
        from yt_dlp import YoutubeDL

        try:
            preview_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "playlist_items": "1",
                "noplaylist": not self.playlist.value,
            }
            if QJS_PATH:
                preview_opts["js_runtimes"] = {"quickjs": {"path": QJS_PATH}}
            with YoutubeDL(preview_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info is None:
                return
            title = info.get("title", "")
            duration = info.get("duration")
            if duration:
                minutes, seconds = divmod(int(duration), 60)
                hours, minutes = divmod(minutes, 60)
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
                self.video_preview.value = f"{title}  —  {duration_str}"
            else:
                self.video_preview.value = title
            self.video_preview.visible = True

            # Fetch formats for Original stream selection (skip when user wants playlist)
            want_playlist = self.playlist.value
            formats = info.get("formats")
            if not want_playlist and not formats:
                # extract_flat doesn't return formats, do a full extract for the single video
                full_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
                if QJS_PATH:
                    full_opts["js_runtimes"] = {"quickjs": {"path": QJS_PATH}}
                with YoutubeDL(full_opts) as ydl2:
                    full_info = ydl2.extract_info(url, download=False)
                if full_info:
                    formats = full_info.get("formats", [])
            if formats and not want_playlist:
                self._populate_original_dropdowns(formats)
        except Exception:
            pass
        self.page.update()

    def _populate_original_dropdowns(self, formats):
        from flet import dropdown

        video_seen = {}
        audio_seen = {}
        for fmt in formats:
            vcodec = fmt.get("vcodec", "none")
            acodec = fmt.get("acodec", "none")
            fmt_id = fmt.get("format_id", "")
            if vcodec not in ("none", None):
                height = fmt.get("height") or 0
                key = vcodec.split(".")[0]
                if key not in video_seen or height > video_seen[key]["height"]:
                    video_seen[key] = {"format_id": fmt_id, "height": height, "codec": vcodec}
            if acodec not in ("none", None) and vcodec in ("none", None):
                abr = fmt.get("abr") or 0
                key = acodec.split(".")[0]
                if key not in audio_seen or abr > audio_seen[key]["abr"]:
                    audio_seen[key] = {"format_id": fmt_id, "abr": abr, "codec": acodec}

        self._video_formats = []
        self._audio_formats = []
        video_options = []
        for key, v in sorted(video_seen.items(), key=lambda x: x[1]["height"], reverse=True):
            label = f"{key} — {v['height']}p"
            self._video_formats.append({"format_id": v["format_id"], "label": label})
            video_options.append(dropdown.Option(key=v["format_id"], text=label))
        audio_options = []
        for key, a in sorted(audio_seen.items(), key=lambda x: x[1]["abr"], reverse=True):
            abr_str = f"{int(a['abr'])}kbps" if a["abr"] else ""
            label = f"{key} — {abr_str}" if abr_str else key
            self._audio_formats.append({"format_id": a["format_id"], "label": label})
            audio_options.append(dropdown.Option(key=a["format_id"], text=label))

        self.original_video_dropdown.options = video_options
        self.original_audio_dropdown.options = audio_options
        if video_options:
            self.original_video_dropdown.value = video_options[0].key
        if audio_options:
            self.original_audio_dropdown.value = audio_options[0].key

    def _compute_window_height(self):
        h = self._height_collapsed
        if self.advanced_section.expanded:
            h += self._height_advanced
        if self.download_progress.visible:
            h += self._height_download
        return h

    def _resize_window(self):
        h = self._compute_window_height()
        self.page.window.height = h
        self.page.window.min_height = h

    def _advanced_toggle(self, e):
        self._resize_window()
        self.page.update()

    def _option_change(self, e):
        self.tomlconfig.update(e.control.data, e.control.value)

    def _nle_ready_change(self, e):
        nle_on = e.control.value
        if nle_on:
            self.video_codec.value = "Auto"
            self.audio_codec.value = "Auto"
            self.original_checkbox.value = False
            self._apply_original_state(False)
            self.tomlconfig.update(CK_ORIGINAL, False)
        self._update_codec_tooltips()
        self._update_encode_indicator()
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _codec_change(self, e):
        self.tomlconfig.update(e.control.data, e.control.value)
        self._update_codec_tooltips()
        self._update_encode_indicator()
        self.page.update()

    def _original_change(self, e):
        original_on = e.control.value
        self._apply_original_state(original_on)
        self.tomlconfig.update(e.control.data, e.control.value)
        self._update_encode_indicator()
        self.page.update()

    def _apply_original_state(self, original_on: bool):
        color = DISABLED_COLOR if original_on else Colors.INVERSE_SURFACE
        for codec_dd in [self.video_codec, self.audio_codec]:
            codec_dd.disabled = original_on
            codec_dd.text_style = TextStyle(weight=FontWeight.BOLD, color=color)
        self.original_video_dropdown.disabled = not original_on
        self.original_audio_dropdown.disabled = not original_on

    def _update_codec_tooltips(self):
        vcodec_tooltips = {
            "Auto": gt(GF.vcodec_auto_tooltip),
        }
        acodec_tooltips = {
            "Auto": gt(GF.acodec_auto_tooltip),
        }
        self.video_codec.tooltip = vcodec_tooltips.get(self.video_codec.value)
        self.audio_codec.tooltip = acodec_tooltips.get(self.audio_codec.value)

    def _update_encode_indicator(self):
        if self.original_checkbox.value:
            # Original mode — remux (fast)
            self.encode_indicator.icon = Icons.CHECK_CIRCLE
            self.encode_indicator.color = "green"
            self.encode_indicator.tooltip = gt(GF.will_remux)
            self.encode_indicator.visible = True
            return
        vcodec = self.video_codec.value
        if vcodec == "Auto" and not self.nle_ready.value:
            # No processing — no indicator
            self.encode_indicator.visible = False
        elif vcodec == "Auto" and self.nle_ready.value:
            # Remux (fast): Auto+NLE remuxes if compatible
            self.encode_indicator.icon = Icons.CHECK_CIRCLE
            self.encode_indicator.color = "green"
            self.encode_indicator.tooltip = gt(GF.will_remux)
            self.encode_indicator.visible = True
        else:
            # Specific codec chosen — re-encode
            self.encode_indicator.icon = Icons.WARNING_AMBER
            self.encode_indicator.color = "orange"
            self.encode_indicator.tooltip = gt(GF.will_reencode)
            self.encode_indicator.visible = True

    def _get_effective_vcodec(self) -> str:
        if self.original_checkbox.value:
            return "Original"
        if self.video_codec.value != "Auto":
            return self.video_codec.value
        if self.nle_ready.value:
            return "NLE"
        return "Best"

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable all user-facing controls during download."""
        disabled = not enabled
        for ctrl in (
            [
                self.media_link,
                self.download_path,
                self.language_button,
                self.theme,
                self.playlist,
                self.indices,
                self.indices_selected,
                self.quality,
                self.framerate,
                self.nle_ready,
                self.audio_only,
                self.song_only,
                self.subtitles,
                self.cookies,
                self.video_codec,
                self.audio_codec,
                self.original_checkbox,
                self.original_video_dropdown,
                self.original_audio_dropdown,
                self.start_checkbox,
                self.end_checkbox,
                self.queue_button,
            ]
            + self.start_controls
            + self.end_controls
        ):
            ctrl.disabled = disabled

    def _apply_audio_only_state(self, audio_only: bool):
        self.song_only.disabled = not audio_only
        self.nle_ready.disabled = audio_only
        color = DISABLED_COLOR if audio_only else Colors.INVERSE_SURFACE
        for video_element in [self.video_codec, self.framerate, self.quality]:
            video_element.text_style = TextStyle(weight=FontWeight.BOLD, color=color)
            video_element.disabled = audio_only
        # In audio-only mode, disable original video stream dropdown
        if audio_only:
            self.original_video_dropdown.disabled = True
        elif self.original_checkbox.value:
            self.original_video_dropdown.disabled = False

    def _audio_only_checkbox_change(self, e):
        audio_only: bool = e.control.value
        self._apply_audio_only_state(audio_only)
        if not audio_only:
            self.song_only.value = False
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _start_checkbox_change(self, e):
        start: bool = e.control.value
        for ctrl in self.start_controls:
            ctrl.disabled = not start
        self._validate_and_update_timecodes()

    def _end_checkbox_change(self, e):
        end: bool = e.control.value
        for ctrl in self.end_controls:
            ctrl.disabled = not end
        self._validate_and_update_timecodes()

    def _enable_download_button(self):
        self.download_disabled_reason = None
        self.download_button.tooltip = None
        self.download_button.disabled = False

    def _disable_download_button(self, tooltip_message):
        self.download_disabled_reason = tooltip_message
        self.download_button.tooltip = gt(tooltip_message)
        self.download_button.disabled = True

    def _timecode_change(self, e):
        self._validate_and_update_timecodes()

    def _validate_and_update_timecodes(self):
        valid = self._timecodes_are_valid()
        color = ("white" if self.page.theme_mode == "dark" else "black") if valid else "red"
        for ctrl in self.start_controls + self.end_controls:
            ctrl.border_color = color
        if not valid:
            self._disable_download_button(GF.incorrect_timestamp)
        elif not validate_url(self.media_link.value or "") and not self._url_queue:
            self._disable_download_button(GF.invalid_url)
        else:
            self._enable_download_button()
        self.page.update()

    def _textfield_focus(self, e: ControlEvent):
        e.control.focus()

    def _show_status(self, message, color):
        self.download_status_text.value = message
        self.download_status_text.visible = True
        self.download_status_text.color = color

    def _update_queue_badge(self):
        count = len(self._url_queue)
        if count > 0:
            self.queue_button.badge = ft.Badge(label=str(count))
        else:
            self.queue_button.badge = None

    def _open_queue_dialog(self, e):
        self._queue_textfield.value = "\n".join(self._url_queue)
        dialog = ft.AlertDialog(
            title=Text(gt(GF.queue_dialog_title)),
            content=ft.Container(
                content=self._queue_textfield,
                width=500,
                height=300,
            ),
            actions=[
                ft.TextButton(gt(GF.queue_dialog_clear), on_click=self._clear_queue_dialog),
                ft.TextButton(gt(GF.queue_dialog_ok), on_click=self._confirm_queue_dialog),
            ],
        )
        self.page.show_dialog(dialog)

    def _clear_queue_dialog(self, e):
        self._queue_textfield.value = ""
        self.page.update()

    def _confirm_queue_dialog(self, e):
        raw = self._queue_textfield.value or ""
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        valid = [url for url in lines if validate_url(url)]
        self._url_queue = valid
        self._update_queue_badge()
        self.page.pop_dialog()
        self._url_validate(self.media_link.value)
        self.page.update()

    def _download_clicked(self, event):
        self.open_folder_button.visible = False
        has_main_url = validate_url(self.media_link.value)
        if not has_main_url and not self._url_queue:
            self._show_status(gt(GF.unsupported_url), "yellow")
            self.page.update()
            return
        self._set_controls_enabled(False)
        self.download_button.disabled = True
        self.cancel_button.disabled = False
        self.cancel_button.visible = True
        self._preparing = True
        self._show_status(gt(GF.preparing), Colors.ON_SURFACE_VARIANT)
        self.download_progress.visible = True
        self.process_progress.visible = True
        self._resize_window()
        self._ui_dirty.clear()
        self._download_done.clear()
        self._cancel_requested.clear()
        self.page.update()
        self.page.run_task(self._run_download_async)

    async def _run_download_async(self):
        ui_task = asyncio.create_task(self._ui_refresh_loop())
        main_url = self.media_link.value if validate_url(self.media_link.value) else None
        urls = ([main_url] if main_url else []) + list(self._url_queue)
        total = len(urls)
        error_occurred = False
        completed_urls = []
        ydl = await asyncio.to_thread(create_ydl, self)
        for i, url in enumerate(urls):
            self.download_progress_bar.value = 0
            self.process_progress_bar.value = 0
            self._download_counter = f"({i + 1}/{total})" if total > 1 else ""
            self.download_progress_text.value = gt(GF.download)
            self.process_progress_text.value = gt(GF.process)
            self.download_last_update = datetime.now()
            self.process_last_update = datetime.now()
            self.download_progress_percent = 0
            self.process_progress_percent = 0
            self._preparing = total == 1
            if total > 1:
                label = url or self.media_link.value
                self._show_status(f"{i + 1}/{total} — {label}", Colors.ON_SURFACE_VARIANT)
                self._ui_dirty.set()
            try:
                await asyncio.to_thread(download, self, ydl, url)
                completed_urls.append(url)
            except DownloadCancelled:
                logger.info("Download cancelled by user")
                self._show_status(gt(GF.dl_cancel), "yellow")
                error_occurred = True
                break
            except PlaylistNotFound:
                logger.error(traceback.format_exc())
                self._show_status(gt(GF.playlist_not_found), "yellow")
                error_occurred = True
                continue
            except FFmpegNoValidEncoderFound:
                logger.error(traceback.format_exc())
                self._show_status(gt(GF.no_encoder), "red")
                error_occurred = True
                continue
            except Exception as e:
                logger.error(traceback.format_exc())
                err_msg = str(e).removeprefix("ERROR: ").split(";")[0]
                self._show_status(f"{gt(GF.dl_error)} {err_msg}", "red")
                error_occurred = True
                continue
        if not error_occurred:
            logger.info("All downloads completed")
            self._show_status(gt(GF.dl_finish), "green")
            self.open_folder_button.visible = True
        # Only remove completed URLs from the queue (keep pending ones on cancel)
        self._url_queue = [u for u in self._url_queue if u not in completed_urls]
        self._update_queue_badge()
        ydl.close()
        self._download_done.set()
        await ui_task
        self._reset_after_download()

    async def _ui_refresh_loop(self):
        """Poll for UI changes from the download thread and flush them."""
        while not self._download_done.is_set():
            await asyncio.to_thread(self._ui_dirty.wait, 0.15)
            if self._ui_dirty.is_set():
                self._ui_dirty.clear()
                self.page.update()
        # Final flush
        self.page.update()

    def _reset_after_download(self):
        self._set_controls_enabled(True)
        self._apply_audio_only_state(self.audio_only.value)
        self._apply_original_state(self.original_checkbox.value)
        self.original_checkbox.disabled = self.playlist.value
        self.indices.disabled = not self.playlist.value
        self.indices_selected.disabled = not self.indices.value
        for ctrl in self.start_controls:
            ctrl.disabled = not self.start_checkbox.value
        for ctrl in self.end_controls:
            ctrl.disabled = not self.end_checkbox.value
        self.cancel_button.disabled = True
        self.cancel_button.visible = False
        self.download_button.disabled = False
        self.download_progress_bar.value = 0
        self.process_progress_bar.value = 0
        self.download_progress.visible = False
        self.process_progress.visible = False
        self.download_progress_text.value = gt(GF.download)
        self.process_progress_text.value = gt(GF.process)
        self._download_counter = ""
        self._resize_window()
        self.page.update()

    def _open_folder_clicked(self, e):
        path = self.download_path_text.value
        if PLATFORM == "Darwin":
            subprocess.Popen(["open", path])
        elif PLATFORM == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])

    def _cancel_clicked(self, e):
        self._cancel_requested.set()
        self.cancel_button.disabled = True
        self.page.update()

    def build_gui(self):
        self.page.add(
            Row(
                controls=[self.language_button, self.theme, self.version_number],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
            ),
            Row(controls=[self.media_link, self.queue_button]),
            self.video_preview,
            Row(controls=[self.download_path_text, self.download_path]),
            Row(controls=[self.nle_ready, self.quality, self.framerate]),
            Row(controls=[self.audio_only, self.song_only]),
            self.advanced_section,
            Row(
                controls=[
                    self.download_button,
                    self.cancel_button,
                    self.download_status_text,
                    self.open_folder_button,
                ]
            ),
            self.download_progress,
            self.process_progress,
        )

    def load_config(self):
        options = self.tomlconfig.config[USER_OPTIONS]
        self._current_language_name = options[CK_LANGUAGE]
        self.language_button.content = Text(self._current_language_name, size=24)
        set_current_language(self._current_language_name)
        self._is_dark = options[CK_THEME]
        self._theme_switch.value = self._is_dark
        self.download_path_text.value = options[CK_DEST_FOLDER]
        self.playlist.value = options[CK_PLAYLIST]
        self.indices.value = options[CK_INDICES]
        self.nle_ready.value = options[CK_NLE_READY]
        self.original_checkbox.value = options.get(CK_ORIGINAL, False)
        self.video_codec.value = options[CK_VCODEC]
        self.quality.value = options[CK_VQUALITY]
        self.framerate.value = options[CK_FRAMERATE]
        self.audio_codec.value = options[CK_ACODEC]
        self.audio_only.value = options[CK_AUDIO_ONLY]
        self.song_only.value = options[CK_SONG_ONLY]
        self.subtitles.value = options[CK_SUBTITLES]
        self.cookies.value = options[CK_COOKIES]
        self.indices.disabled = not self.playlist.value
        self.indices_selected.disabled = not self.indices.value
        self.original_checkbox.disabled = self.playlist.value
        self._apply_audio_only_state(self.audio_only.value)
        self._apply_original_state(self.original_checkbox.value)
        self._change_attribute_based_on_theme(self._is_dark)
        self._refresh_labels()
        self._index_change()
        self._update_encode_indicator()
        self.page.update()


def videodl_fletgui(page: Page):
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    if os.path.isfile(icon_path):
        page.window.icon = icon_path
    videodl_app = VideodlApp(page)
    videodl_app.build_gui()
    videodl_app.load_config()


def videodl_gui():
    ft.run(videodl_fletgui, assets_dir="assets")
