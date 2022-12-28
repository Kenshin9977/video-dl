from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime

import flet as ft
from darkdetect import isDark
from quantiphy import InvalidNumber, Quantity
from yt_dlp import utils
from yt_dlp.postprocessor.sponsorblock import SponsorBlockPP
from yt_dlp.utils import traverse_obj

from components_handlers.ytdlp_handler import download
from gui_config import VideodlConfig
from gui_options import ACODECS, BROWSERS, FRAMERATE, QUALITY, VCODECS
from lang import GuiField as GF
from lang import get_available_languages_name, get_current_language_name
from lang import get_text as gt
from lang import set_current_language
from sys_vars import FF_PATH
from utils.sys_utils import APP_VERSION, get_default_download_path
from videodl_exceptions import DownloadCancelled, PlaylistNotFound

logger = logging.getLogger()

DISABLED_COLOR = ft.colors.ON_INVERSE_SURFACE


class VideodlApp:
    def __init__(self, page: ft.Page):
        is_dark = bool(isDark())
        self.page = page
        self.page.title = "Video-dl"
        self.page.theme_mode = "dark" if is_dark else "light"
        self.page.window_height = 900
        self.page.window_min_height = 900
        self.page.window_width = gt(GF.width)
        self.page.window_min_width = gt(GF.width)
        self.download_disabled_reason = None
        self.default_indices_value = "1,2,4-10,12"
        checkbox_common_kwargs = {"fill_color": "Blue"}
        self.file_picker = ft.FilePicker(
            on_result=self._directory_selected,
            data="Destination folder",  # NOSONAR
        )
        self.page.overlay.append(self.file_picker)
        self.media_link = ft.TextField(
            label=gt(GF.link),
            autofocus=True,
            dense=True,
        )
        self.download_path_text = ft.Text(
            get_default_download_path(), data="Destination folder"
        )
        self.download_path = ft.ElevatedButton(
            gt(GF.destination_folder),
            icon=ft.icons.FOLDER,
            on_click=lambda _: self.file_picker.get_directory_path(),
        )
        self.language = ft.Dropdown(
            label=gt(GF.language),
            data="Language",
            value=get_current_language_name(),
            width=120,
            dense=True,
            on_change=self._change_language,
            options=[
                ft.dropdown.Option(lang)
                for lang in get_available_languages_name()
            ],
        )
        self.theme = ft.Switch(
            label=gt(GF.theme),
            data="Theme",
            value=is_dark,
            active_color="blue",
            on_change=self._change_theme,
        )

        self.version_number = ft.Text(
            value=f"v{APP_VERSION}", text_align=ft.TextAlign.RIGHT
        )
        self.playlist = ft.Checkbox(
            label=gt(GF.is_playlist),
            data="Playlist",
            **checkbox_common_kwargs,
            on_change=self._playlist_checkbox_change,
        )
        self.indices = ft.Checkbox(
            label=gt(GF.playlist_items),
            data="Indices",
            disabled=True,
            **checkbox_common_kwargs,
            on_change=self._index_checkbox_change,
        )
        self.indices_selected = ft.TextField(
            label=gt(GF.indices_selected),
            value=self.default_indices_value,
            width=200,
            disabled=True,
            text_style=ft.TextStyle(color=DISABLED_COLOR),
        )
        self.quality = ft.Dropdown(
            label=gt(GF.quality),
            data="Video quality",
            value="1080p",
            width=120,
            dense=True,
            on_change=self._option_change,
            options=[ft.dropdown.Option(quality) for quality in QUALITY],
        )
        self.framerate = ft.Dropdown(
            label=gt(GF.framerate),
            data="Framerate",
            value="60",
            width=120,
            dense=True,
            on_change=self._option_change,
            options=[ft.dropdown.Option(framerate) for framerate in FRAMERATE],
        )
        self.audio_only = ft.Checkbox(
            label=gt(GF.audio_only),
            data="Audio only",
            on_change=self._audio_only_checkbox_change,
            **checkbox_common_kwargs,
        )
        self.song_only = ft.Checkbox(
            label=gt(GF.song_only),
            data="Song only",
            disabled=True,
            tooltip=gt(GF.song_only_tooltip),
            on_change=self._option_change,
            **checkbox_common_kwargs,
        )
        self.subtitles = ft.Checkbox(
            label=gt(GF.subtitles),
            data="Subtitles",
            on_change=self._option_change,
            **checkbox_common_kwargs,
        )
        self.cookies = ft.Dropdown(
            label=gt(GF.cookies),
            data="Cookies",
            value=gt(GF.cookies_none),
            width=100,
            dense=True,
            tooltip=gt(GF.cookies_tooltip),
            on_change=self._option_change,
            options=[ft.dropdown.Option(browser) for browser in BROWSERS],
        )
        self.video_codec = ft.Dropdown(
            label=gt(GF.vcodec),
            data="Video codec",
            value="x264",
            width=100,
            dense=True,
            on_change=self._option_change,
            options=[ft.dropdown.Option(vcodec) for vcodec in VCODECS],
        )
        self.audio_codec = ft.Dropdown(
            label=gt(GF.acodec),
            data="Audio codec",
            value="BEST",
            width=100,
            dense=True,
            on_change=self._option_change,
            options=[ft.dropdown.Option(acodec) for acodec in ACODECS],
        )
        timecode_common_kwargs = {
            "value": "00",
            "max_length": 2,
            "dense": True,
            "width": 50,
            "disabled": True,
            "on_change": self._timecode_change,
            "border_color": "white",
            "counter_style": ft.TextStyle(size=0, color=DISABLED_COLOR),
            "on_focus": self._textfield_focus,
        }
        self.start_checkbox = ft.Checkbox(
            label="Start",
            **checkbox_common_kwargs,
            on_change=self._start_checkbox_change,
        )
        self.start_h = ft.TextField(**timecode_common_kwargs)
        self.start_m = ft.TextField(**timecode_common_kwargs)
        self.start_s = ft.TextField(**timecode_common_kwargs)
        self.start_controls = [self.start_h, self.start_m, self.start_s]
        self.end_checkbox = ft.Checkbox(
            label="End",
            **checkbox_common_kwargs,
            on_change=self._end_checkbox_change,
        )
        self.end_h = ft.TextField(**timecode_common_kwargs)
        self.end_m = ft.TextField(**timecode_common_kwargs)
        self.end_s = ft.TextField(**timecode_common_kwargs)
        self.end_controls = [self.end_h, self.end_m, self.end_s]
        self.colon = ft.Text(":")
        self.download_button = ft.ElevatedButton(
            text="Download", on_click=self._download_clicked
        )
        self.cancel_button = ft.ElevatedButton(
            text=gt(GF.cancel_button),
            on_click=self._cancel_clicked,
            disabled=True,
        )
        self.download_status_text = ft.Text(visible=False)
        self.download_progress_text = ft.Text(gt(GF.download))
        self.process_progress_text = ft.Text(gt(GF.process))
        self.download_progress_bar = ft.ProgressBar(width=200)
        self.process_progress_bar = ft.ProgressBar(width=200, color="red")
        self.download_progress = ft.Column(
            [self.download_progress_text, self.download_progress_bar],
            visible=False,
        )
        self.process_progress = ft.Column(
            [self.process_progress_text, self.process_progress_bar],
            visible=False,
        )
        self.ydl_opts: dict = {}
        self.download_last_update: datetime = datetime.now()
        self.download_last_speed: str = ""
        self.process_last_update: datetime = datetime.now()
        self.process_last_speed: str = ""
        self.download_progress_percent: int = 0
        self.process_progress_percent: int = 0
        self.tomlconfig = VideodlConfig()

    def _gen_ydl_opts(self) -> dict:
        """
        Generate yt-dlp options' dictionnary.

        Args:
            opts (dict): Options selected in the GUI

        Returns:
            dict: yt-dlp options
        """
        self._gen_file_opts()
        self._gen_av_opts()
        self._gen_ffmpeg_opts()
        self._gen_subtitles_opts()
        self._gen_browser_opts()
        self._gen_sponsor_block_opts()
        return self.ydl_opts

    def _gen_file_opts(self):
        """
        Generate yt-dlp file's options
        """
        self.ydl_opts.update(
            {
                "noplaylist": not self.playlist.value,
                "ignoreerrors": "only_download"
                if self.playlist.value
                else False,
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
        if self.indices:
            self.ydl_opts["playlist_items"] = self.indices_selected.value or 1

        if FF_PATH.get("ffmpeg") != "ffmpeg":
            self.ydl_opts["ffmpeg_location"] = FF_PATH.get("ffmpeg")

    def _gen_av_opts(self):
        """
        Generate yt-dlp options for the audio and the video both for their
        search filters, their downloader and their post process.
        """
        if self.audio_only.value:
            format_opt = "ba/ba*"
            if self.video_codec.value != "best":
                format_opt = (
                    f"ba[acodec*={self.audio_codec.value}]/{format_opt}"
                )
            # Either the target audio codec, the best without video so the
            # download is faster or the best one even if there is a video with
            # it
            self.ydl_opts.update(
                {
                    "extract_audio": True,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": self.audio_codec.value,
                        }
                    ],
                }
            )
        else:
            vcodec_re_str = "vcodec~='avc1|h264'"
            # Either the target vcodec or the most common and easiest to
            # convert (h264)
            acodec_re_str = "acodec~='aac|mp3|mp4a'"
            # Audio codecs compatible with mp4 containers
            format_opt = (
                f"((bv[{vcodec_re_str}]/bv)+(ba[{acodec_re_str}]/ba))/b"
            )
            # The best video preferably with the target codec merged with the
            # best audio without video preferably with a codec compatible with
            # mp4 containers or the overall best
            self.ydl_opts.update(
                {
                    "format_sort": [
                        f"res:{self.quality}",
                        f"fps:{self.framerate}",
                    ],
                    "merge-output-format": "mp4",
                }
            )
            # In order looks for the exact resolution, lower if not found,
            # higher if not found
        self.ydl_opts["format"] = format_opt

    def _gen_ffmpeg_opts(self) -> dict:
        """
        Generate the dictionnary for yt-dlp ffmpeg options
        """
        start_values = [getattr(ctrl, "value") for ctrl in self.start_controls]
        start_timecode = ":".join(start_values)
        end_values = [getattr(ctrl, "value") for ctrl in self.end_controls]
        end_timecode = ":".join(end_values)
        if self.start_checkbox.value or self.end_checkbox.value:
            start = start_timecode if self.start_checkbox else "00:00:00"
            end = end_timecode if self.end_checkbox else "99:99:99"
            self.ydl_opts.update(
                {
                    "external_downloader": "ffmpeg",
                    "external_downloader_args": {
                        "ffmpeg_i": ["-ss", start, "-to", end]
                    },
                }
            )

    def _gen_subtitles_opts(self):
        """
        Generate the dictionnary for yt-dlp subtitles options
        """
        if self.subtitles:
            self.ydl_opts["subtitleslangs"] = ["all"], {"writesubtitles": True}

    def _gen_browser_opts(self):
        """
        Generate the dictionnary for yt-dlp cookies option
        """
        if self.cookies.value != gt(GF.cookies_none):
            self.ydl_opts["cookiesfrombrowser"] = [self.cookies.value.lower()]

    def _gen_sponsor_block_opts(self):
        if self.song_only.value:
            categories = SponsorBlockPP.CATEGORIES.keys()
            self.ydl_opts.get("postprocessors", []).append(
                [
                    {"key": "SponsorBlock", "when": "pre_process"},
                    {
                        "key": "ModifyChapters",
                        "SponsorBlock": categories,
                    },
                ]
            )

    def _update_download_bar(self, d: dict):
        self.download_last_update, self.download_last_speed = self._update_bar(
            d,
            "downloaded_bytes",
            self.download_last_update,
            self.download_last_speed,
            self.download_progress_bar,
            self.download_progress_text,
            self.download_progress_percent,
        )

    def _update_process_bar(self, d: dict):
        self.process_last_update, self.process_last_speed = self._update_bar(
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
        progress_bar: ft.ProgressBar,
        progress_text: ft.Text,
        last_progress_percent: int,  # NOSONAR
    ):
        if self.cancel_button.disabled:
            raise DownloadCancelled
        try:
            speed = Quantity(d.get("speed"), "B/s").render(prec=2)
        except InvalidNumber:
            speed = "-"
        try:
            downloaded = Quantity(d.get(bytes_fieldname), "B")
        except InvalidNumber:
            downloaded = "-"
        try:
            total = Quantity(d.get("total_bytes"), "B")
        except InvalidNumber:
            try:
                total = Quantity(d.get("total_bytes_estimate"), "B")
            except InvalidNumber:
                total = 0
        progress_float = d.get("progress_float")
        if not progress_float:
            try:
                progress_float = downloaded / total
                # Necessary for when the total size is inaccurate
                if progress_float >= 1:
                    progress_float = 0.99
                elif progress_float < 0:
                    progress_float = 0
                last_progress_percent = progress_float
            except (ZeroDivisionError, TypeError):
                progress_float = last_progress_percent

        n_current_entry = traverse_obj(d, ("info_dict", "playlist_autonumber"))
        n_entries = traverse_obj(d, ("info_dict", "n_entries"))
        progress_bar.value = progress_float
        time_elapsed = datetime.now() - time_last_update
        delta_ms = (
            time_elapsed.seconds * 1_000 + time_elapsed.microseconds // 1_000
        )
        if delta_ms >= 500:
            last_speed = speed
            time_last_update = datetime.now()
        action = d.get("action")
        if not action and bytes_fieldname == "downloaded_bytes":
            action = gt(GF.download)
        if not action and bytes_fieldname == "processed_bytes":
            action = gt(GF.process)
        progress_str = f"{action} {int(progress_float * 100)}% {speed}"
        if n_current_entry and n_entries > 1:
            progress_str += f"({n_current_entry}/{n_entries})"
        progress_text.value = progress_str
        self.page.update()
        return time_last_update, last_speed

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
            return (
                sh < eh
                or (sh == eh and sm < em)
                or (sh == eh and sm == em and ss < es)
            )
        return True

    @staticmethod
    def _timecode_is_valid(ctrls: list) -> tuple[int, int, int]:
        try:
            h_int, m_int, s_int = [int(getattr(ctr, "value")) for ctr in ctrls]
        except ValueError:
            return -1, -1, -1
        if m_int >= 60 or s_int >= 60:
            return -1, -1, -1
        return h_int, m_int, s_int

    def _change_language(self, e=None):
        set_current_language(self.language.value)
        self.language.label = gt(GF.language)
        self.theme.label = gt(GF.theme)
        self.media_link.label = gt(GF.link)
        self.download_path.text = gt(GF.destination_folder)
        self.playlist.label = gt(GF.is_playlist)
        self.indices.label = gt(GF.playlist_items)
        self.indices_selected.label = gt(GF.indices_selected)
        self.video_codec.label = gt(GF.vcodec)
        self.quality.label = gt(GF.quality)
        self.framerate.label = gt(GF.framerate)
        self.audio_codec.label = gt(GF.acodec)
        self.audio_only.label = gt(GF.audio_only)
        self.song_only.label = gt(GF.song_only)
        self.song_only.tooltip = gt(GF.song_only_tooltip)
        self.start_checkbox.label = gt(GF.start)
        self.end_checkbox.label = gt(GF.end)
        self.subtitles.label = gt(GF.subtitles)
        self.cookies.label = gt(GF.cookies)
        self.cookies.options[0].text = gt(GF.cookies_none)
        self.cookies.tooltip = gt(GF.cookies_tooltip)
        self.download_button.text = gt(GF.download)
        self.cancel_button.text = gt(GF.cancel_button)
        self.download_progress.controls[0].value = gt(GF.download)
        self.process_progress.controls[0].value = gt(GF.process)
        self.page.window_width = gt(GF.width)
        self.page.window_min_width = gt(GF.width)
        if self.download_disabled_reason is not None:
            self.download_button.tooltip = gt(self.download_disabled_reason)
        if e:
            self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _change_theme(self, e):
        dark_mode: bool = e.control.value
        self._change_attribute_based_on_theme(dark_mode)
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _change_attribute_based_on_theme(self, dark: bool):
        new_theme, border = ("dark", "white") if dark else ("light", "black")
        self.page.theme_mode = new_theme
        for control in self.start_controls + self.end_controls:
            control.border_color = border

    def _directory_selected(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return
        self.download_path_text.value = e.path
        self.tomlconfig.update(e.control.data, e.path)
        self.page.update()

    def _playlist_checkbox_change(self, e):
        playlist: bool = e.control.value
        self.indices.disabled = not playlist
        if not playlist:
            self.indices.value = False
            self.indices_selected.disabled = not playlist
            self.tomlconfig.update("Indices", False)
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _index_checkbox_change(self, e):
        self._index_change()
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _index_change(self):
        self.indices_selected.disabled = not self.indices.value
        if self.indices.value:
            self.indices_selected.text_style = ft.TextStyle(
                weight=ft.FontWeight.BOLD, color=ft.colors.INVERSE_SURFACE
            )
            if self.indices_selected.value == self.default_indices_value:
                self.indices_selected.value = ""
        else:
            self.indices_selected.text_style = ft.TextStyle(
                color=DISABLED_COLOR
            )

    def _option_change(self, e):
        self.tomlconfig.update(e.control.data, e.control.value)

    def _audio_only_checkbox_change(self, e):
        audio_only: bool = e.control.value
        self.song_only.disabled = not audio_only
        video_elements = [self.video_codec, self.framerate, self.quality]
        for video_element in video_elements:
            color = DISABLED_COLOR if audio_only else ft.colors.INVERSE_SURFACE
            video_element.text_style = ft.TextStyle(
                weight=ft.FontWeight.BOLD, color=color
            )
            video_element.disabled = audio_only
        if not audio_only:
            self.song_only.value = False
        self.tomlconfig.update(e.control.data, e.control.value)
        self.page.update()

    def _start_checkbox_change(self, e):
        start: bool = e.control.value
        [setattr(ctrl, "disabled", not start) for ctrl in self.start_controls]
        if not self._timecodes_are_valid():
            self._disable_download_button(GF.incorrect_timestamp)
        else:
            self._enable_download_button()
        self.page.update()

    def _end_checkbox_change(self, e):
        end: bool = e.control.value
        [setattr(ctrl, "disabled", not end) for ctrl in self.end_controls]
        if not self._timecodes_are_valid():
            self._disable_download_button(GF.incorrect_timestamp)
        else:
            self._enable_download_button()
        self.page.update()

    def _enable_download_button(self):
        self.download_disabled_reason = None
        self.download_button.tooltip = None
        self.download_button.disabled = False

    def _disable_download_button(self, tooltip_message):
        self.download_disabled_reason = tooltip_message
        self.download_button.tooltip = gt(tooltip_message)
        self.download_button.disabled = True

    def _timecode_change(self, e):
        if not self._timecodes_are_valid():
            self._disable_download_button(GF.incorrect_timestamp)
        else:
            self._enable_download_button()
        self.page.update()

    def _textfield_focus(self, e: ft.ControlEvent):
        e.control.focus()

    def _download_clicked(self, event):
        try:
            self.download_button.disabled = True
            self.cancel_button.disabled = False
            self.download_status_text.visible = False
            self.download_progress.visible = True
            self.process_progress.visible = True
            self.page.update()
            download(self)
        except DownloadCancelled:
            logging.error(traceback.format_exc())
            self.download_status_text.value = gt(GF.dl_cancel)
            self.download_status_text.visible = True
            self.download_status_text.color = "yellow"
        except PlaylistNotFound:
            logging.error(traceback.format_exc())
            self.download_status_text.value = gt(GF.playlist_not_found)
            self.download_status_text.visible = True
            self.download_status_text.color = "yellow"
        except FileExistsError:
            self.download_status_text.value = gt(GF.dl_finish)
            self.download_status_text.visible = True
            self.download_status_text.color = "red"
        except utils.UnsupportedError:
            self.download_status_text.value = gt(GF.unsupported_url)
            self.download_status_text.visible = True
            self.download_status_text.color = "red"
        except utils.DownloadError:
            logging.error(traceback.format_exc())
            self.download_status_text.value = gt(GF.unsupported_url)
            self.download_status_text.visible = True
            self.download_status_text.color = "red"
        except Exception as e:
            logging.error(traceback.format_exc())
            self.download_status_text.value = (
                f"{gt(GF.dl_error)}\n{str(e)}\n{traceback.format_exc()}"
            )
            self.download_status_text.visible = True
            self.download_status_text.color = "red"
        else:
            logging.error(traceback.format_exc())
            self.download_status_text.value = gt(GF.dl_finish)
            self.download_status_text.visible = True
            self.download_status_text.color = "green"
        self.cancel_button.disabled = True
        self.download_button.disabled = False
        self.download_progress_bar.value = 0
        self.process_progress_bar.value = 0
        self.download_progress.visible = False
        self.process_progress.visible = False
        self.download_progress_text.value = gt(GF.download)
        self.process_progress_text.value = gt(GF.process)
        self.page.update()

    def _cancel_clicked(self, e):
        self.cancel_button.disabled = True
        self.download_progress.visible = False
        self.process_progress.visible = False
        self.download_button.disabled = False
        self.page.update()

    def build_gui(self):
        self.page.add(
            ft.Row(
                controls=[self.language, self.theme, self.version_number],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Row(controls=[self.media_link]),
            ft.Row(controls=[self.download_path_text]),
            ft.Row(controls=[self.download_path]),
            ft.Row(
                controls=[self.playlist, self.indices, self.indices_selected]
            ),
            ft.Row(controls=[self.video_codec, self.quality, self.framerate]),
            ft.Row(
                controls=[self.audio_codec, self.audio_only, self.song_only]
            ),
            ft.Row(
                controls=[
                    self.start_checkbox,
                    self.start_h,
                    self.colon,
                    self.start_m,
                    self.colon,
                    self.start_s,
                ]
            ),
            ft.Row(
                controls=[
                    self.end_checkbox,
                    self.end_h,
                    self.colon,
                    self.end_m,
                    self.colon,
                    self.end_s,
                ]
            ),
            ft.Row(controls=[self.subtitles, self.cookies]),
            ft.Row(
                controls=[
                    self.download_button,
                    self.cancel_button,
                    self.download_status_text,
                ]
            ),
            ft.Row(controls=[self.download_progress, self.process_progress]),
        )

    def load_config(self):
        options = self.tomlconfig.config["User options"]
        self.language.value = options["Language"]
        self.theme.value = options["Theme"]
        self.download_path_text.value = options["Destination folder"]
        self.playlist.value = options["Playlist"]
        self.indices.value = options["Indices"]
        self.video_codec.value = options["Video codec"]
        self.quality.value = options["Video quality"]
        self.framerate.value = options["Framerate"]
        self.audio_codec.value = options["Audio codec"]
        self.audio_only.value = options["Audio only"]
        self.song_only.value = options["Song only"]
        self.subtitles.value = options["Subtitles"]
        self.cookies.value = options["Cookies"]
        self.indices.disabled = not self.playlist.value
        self.indices_selected.disabled = not self.indices.value
        self.song_only.disabled = not self.audio_only.value
        self.video_codec.disabled = self.audio_only.value
        self.quality.disabled = self.audio_only.value
        self.framerate.disabled = self.audio_only.value
        self._change_attribute_based_on_theme(self.theme.value)
        self._change_language()
        self._index_change()
        audio_only = self.audio_only.value
        color = DISABLED_COLOR if audio_only else ft.colors.INVERSE_SURFACE
        video_elements = [self.video_codec, self.framerate, self.quality]
        for video_element in video_elements:
            video_element.disabled = audio_only
            video_element.text_style = ft.TextStyle(
                weight=ft.FontWeight.BOLD, color=color
            )
        self.page.update()


def videodl_fletgui(page: ft.Page):
    videodl_app = VideodlApp(page)
    videodl_app.build_gui()
    videodl_app.load_config()


def videodl_gui():
    ft.app(target=videodl_fletgui)
