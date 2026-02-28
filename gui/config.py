from __future__ import annotations

import os
from os.path import isdir, isfile
from typing import Any

import tomlkit
from tomlkit.exceptions import ParseError

import runtime
from gui.options import ACODECS, BROWSERS, FRAMERATE, QUALITY, VCODECS
from i18n.lang import GuiField as GF
from i18n.lang import get_available_languages_name, get_current_language_name, set_current_language
from i18n.lang import get_text as gt
from utils.sys_utils import get_default_browser, get_default_download_path

try:
    from darkdetect import isDark
except ImportError:

    def isDark():
        return True


_paths = runtime.get_paths()
CONFIG_FILENAME = os.path.join(_paths.get_config_dir(), "videodl-config.toml")
USER_OPTIONS = "User options"

# Config key constants — used by config.py and app.py
CK_LANGUAGE = "Language"
CK_THEME = "Theme"
CK_DEST_FOLDER = "Destination folder"
CK_PLAYLIST = "Playlist"
CK_INDICES = "Indices"
CK_NLE_READY = "NLE Ready"
CK_ORIGINAL = "Original"
CK_VCODEC = "Video codec"
CK_VQUALITY = "Video quality"
CK_FRAMERATE = "Framerate"
CK_ACODEC = "Audio codec"
CK_AUDIO_ONLY = "Audio only"
CK_SONG_ONLY = "Song only"
CK_SUBTITLES = "Subtitles"
CK_COOKIES = "Cookies"


class VideodlConfig:
    def __init__(self):
        if isfile(CONFIG_FILENAME):
            self.config = self._load()
        else:
            self.config = self._create_default()

    def update(self, key, value):
        self.config[USER_OPTIONS][key] = value
        self._save()

    def _create_default(self) -> dict[str, Any]:
        detected_browser = get_default_browser()
        config = {
            USER_OPTIONS: {
                CK_LANGUAGE: get_current_language_name(),
                CK_THEME: bool(isDark()),
                CK_DEST_FOLDER: get_default_download_path(),
                CK_PLAYLIST: False,
                CK_INDICES: False,
                CK_NLE_READY: True,
                CK_ORIGINAL: False,
                CK_VCODEC: "Auto",
                CK_VQUALITY: "1080p",
                CK_FRAMERATE: "60",
                CK_ACODEC: "Auto",
                CK_AUDIO_ONLY: False,
                CK_SONG_ONLY: False,
                CK_SUBTITLES: False,
                CK_COOKIES: detected_browser or gt(GF.login_from_none),
            }
        }
        self._save(config)
        return config

    def _save(self, config: dict[str, Any] | None = None):
        config = config or self.config
        with open(CONFIG_FILENAME, mode="w", encoding="utf-8") as fp:
            tomlkit.dump(config, fp)

    def _load(self) -> dict[str, Any]:
        config: dict[str, Any] | None = None
        try:
            with open(CONFIG_FILENAME, encoding="utf-8") as fp:
                config = tomlkit.load(fp)
            if not self._config_is_valid(config):
                config = None
        except ParseError:
            pass
        if not config:
            config = self._create_default()
        return config

    def _config_is_valid(self, config: dict[str, Any]) -> bool:
        try:
            opts = config[USER_OPTIONS]
            if opts[CK_LANGUAGE] not in get_available_languages_name():
                return False
            set_current_language(opts[CK_LANGUAGE])
            browsers = list(BROWSERS)
            browsers[0] = gt(GF.login_from_none)
            self._migrate_original(opts)
            return (
                opts[CK_LANGUAGE] in get_available_languages_name()
                and isinstance(opts[CK_THEME], bool)
                and isdir(opts[CK_DEST_FOLDER])
                and isinstance(opts[CK_PLAYLIST], bool)
                and isinstance(opts[CK_INDICES], bool)
                and isinstance(opts[CK_NLE_READY], bool)
                and isinstance(opts.get(CK_ORIGINAL, False), bool)
                and opts[CK_VCODEC] in VCODECS
                and opts[CK_VQUALITY] in QUALITY
                and opts[CK_FRAMERATE] in FRAMERATE
                and opts[CK_ACODEC] in ACODECS
                and isinstance(opts[CK_AUDIO_ONLY], bool)
                and isinstance(opts[CK_SONG_ONLY], bool)
                and isinstance(opts[CK_SUBTITLES], bool)
                and opts[CK_COOKIES] in browsers
                and VideodlConfig._logic_is_respected(opts)
            )
        except KeyError:
            return False

    @staticmethod
    def _migrate_original(opts: dict):
        """Migrate old config where 'Original' was a codec dropdown value."""
        if opts.get(CK_VCODEC) == "Original":
            opts[CK_VCODEC] = "Auto"
            opts[CK_ORIGINAL] = True
        if opts.get(CK_ACODEC) == "Original":
            opts[CK_ACODEC] = "Auto"
            opts[CK_ORIGINAL] = True
        if CK_ORIGINAL not in opts:
            opts[CK_ORIGINAL] = False

    @staticmethod
    def _logic_is_respected(opts: dict):
        if opts[CK_INDICES] and not opts[CK_PLAYLIST]:
            return False
        return not (opts[CK_SONG_ONLY] and not opts[CK_AUDIO_ONLY])
