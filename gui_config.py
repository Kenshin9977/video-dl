import os
from os import path
from os.path import isdir, isfile

import sys

import tomlkit
from darkdetect import isDark
from tomlkit.exceptions import ParseError

from gui_options import ACODECS, BROWSERS, FRAMERATE, QUALITY, VCODECS
from lang import GuiField as GF
from lang import get_available_languages_name, get_current_language_name
from lang import get_text as gt
from lang import set_current_language
from utils.sys_utils import get_default_download_path

CONFIG_FILENAME = "videodl-config.toml"
USER_OPTIONS = "User options"


class VideodlConfig:
    def __init__(self):
        self.work_path = os.path.dirname(sys.argv[0])
        if os.path.isfile(CONFIG_FILENAME):
            self.config = self._load()
        else:
            self.config = self._create_default()

    def update(self, key, value):
        self.config[USER_OPTIONS][key] = value
        self._save()

    def _create_default(self) -> dict:
        config = {
            USER_OPTIONS: {
                "Language": get_current_language_name(),
                "Theme": bool(isDark()),
                "Destination folder": get_default_download_path(),
                "Playlist": False,
                "Indices": False,
                "Video codec": "x264",
                "Video quality": "1080p",
                "Framerate": "60",
                "Audio codec": "BEST",
                "Audio only": False,  # NOSONAR
                "Song only": False,  # NOSONAR
                "Subtitles": False,
                "Cookies": gt(GF.cookies_none),
            }
        }
        self._save(config)
        return config

    def _save(self, config: dict = None):
        config = config or self.config
        with open(CONFIG_FILENAME, mode="wt", encoding="utf-8") as fp:
            tomlkit.dump(config, fp)

    def _load(self) -> dict:
        config = None
        try:
            with open(CONFIG_FILENAME, mode="rt", encoding="utf-8") as fp:
                config = tomlkit.load(fp)
            if not self._config_is_valid(config):
                config = None
        except ParseError:
            pass
        if not config:
            config = self._create_default()
        return config

    def _config_is_valid(self, config: dict) -> bool:
        try:
            user_options = config[USER_OPTIONS]
            if user_options["Language"] not in get_available_languages_name():
                return False
            set_current_language(user_options["Language"])
            browsers = BROWSERS
            browsers[0] = gt(GF.cookies_none)
            return (
                user_options["Language"] in get_available_languages_name()
                and isinstance(user_options["Theme"], bool)
                and isdir(user_options["Destination folder"])
                and isinstance(user_options["Playlist"], bool)
                and isinstance(user_options["Indices"], bool)
                and user_options["Video codec"] in VCODECS
                and user_options["Video quality"] in QUALITY
                and user_options["Framerate"] in FRAMERATE
                and user_options["Audio codec"] in ACODECS
                and isinstance(user_options["Audio only"], bool)
                and isinstance(user_options["Song only"], bool)
                and isinstance(user_options["Subtitles"], bool)
                and user_options["Cookies"] in browsers
                and VideodlConfig._logic_is_respected(user_options)
            )
        except KeyError:
            return False

    @staticmethod
    def _logic_is_respected(options: dict):
        if options["Indices"] and not options["Playlist"]:
            return False
        if options["Song only"] and not options["Audio only"]:
            return False
        return True
