import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before importing
mock_lang = MagicMock()
mock_lang.get_text.return_value = "None"
mock_lang.get_available_languages_name.return_value = ["English", "Français"]
mock_lang.get_current_language_name.return_value = "English"
mock_lang.set_current_language = MagicMock()

mock_options = MagicMock()
mock_options.VCODECS = ["Auto", "x264", "x265", "ProRes", "AV1"]
mock_options.ACODECS = ["Auto", "AAC", "ALAC", "FLAC", "OPUS", "MP3", "VORBIS", "WAV"]
mock_options.QUALITY = ["4320p", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]
mock_options.FRAMERATE = ["30", "60"]
mock_options.BROWSERS = ["None", "Brave", "Chrome", "Firefox"]

mock_tomlkit = MagicMock()
mock_tomlkit_exceptions = MagicMock()
mock_tomlkit_exceptions.ParseError = Exception

for mod_name, mod_mock in [
    ("darkdetect", MagicMock()),
    ("tomlkit", mock_tomlkit),
    ("tomlkit.exceptions", mock_tomlkit_exceptions),
    ("i18n", MagicMock()),
    ("i18n.lang", mock_lang),
    ("gui.options", mock_options),
    ("utils.sys_utils", MagicMock()),
    ("flet", MagicMock()),
    ("sys_vars", MagicMock()),
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = mod_mock

from gui.config import (  # noqa: E402
    CK_ACODEC,
    CK_AUDIO_ONLY,
    CK_INDICES,
    CK_ORIGINAL,
    CK_PLAYLIST,
    CK_SONG_ONLY,
    CK_VCODEC,
    VideodlConfig,
)


class TestLogicIsRespected:
    def test_valid_basic(self):
        opts = {CK_PLAYLIST: True, CK_INDICES: True, CK_AUDIO_ONLY: True, CK_SONG_ONLY: True}
        assert VideodlConfig._logic_is_respected(opts) is True

    def test_indices_without_playlist(self):
        opts = {CK_PLAYLIST: False, CK_INDICES: True, CK_AUDIO_ONLY: False, CK_SONG_ONLY: False}
        assert VideodlConfig._logic_is_respected(opts) is False

    def test_song_only_without_audio_only(self):
        opts = {CK_PLAYLIST: False, CK_INDICES: False, CK_AUDIO_ONLY: False, CK_SONG_ONLY: True}
        assert VideodlConfig._logic_is_respected(opts) is False

    def test_all_off(self):
        opts = {CK_PLAYLIST: False, CK_INDICES: False, CK_AUDIO_ONLY: False, CK_SONG_ONLY: False}
        assert VideodlConfig._logic_is_respected(opts) is True

    def test_playlist_without_indices(self):
        opts = {CK_PLAYLIST: True, CK_INDICES: False, CK_AUDIO_ONLY: False, CK_SONG_ONLY: False}
        assert VideodlConfig._logic_is_respected(opts) is True

    def test_audio_only_without_song_only(self):
        opts = {CK_PLAYLIST: False, CK_INDICES: False, CK_AUDIO_ONLY: True, CK_SONG_ONLY: False}
        assert VideodlConfig._logic_is_respected(opts) is True


class TestMigrateOriginal:
    def test_vcodec_original_migrated(self):
        opts = {CK_VCODEC: "Original", CK_ACODEC: "Auto"}
        VideodlConfig._migrate_original(opts)
        assert opts[CK_VCODEC] == "Auto"
        assert opts[CK_ORIGINAL] is True

    def test_acodec_original_migrated(self):
        opts = {CK_VCODEC: "Auto", CK_ACODEC: "Original"}
        VideodlConfig._migrate_original(opts)
        assert opts[CK_ACODEC] == "Auto"
        assert opts[CK_ORIGINAL] is True

    def test_both_original_migrated(self):
        opts = {CK_VCODEC: "Original", CK_ACODEC: "Original"}
        VideodlConfig._migrate_original(opts)
        assert opts[CK_VCODEC] == "Auto"
        assert opts[CK_ACODEC] == "Auto"
        assert opts[CK_ORIGINAL] is True

    def test_no_migration_needed(self):
        opts = {CK_VCODEC: "x264", CK_ACODEC: "AAC"}
        VideodlConfig._migrate_original(opts)
        assert opts[CK_VCODEC] == "x264"
        assert opts[CK_ACODEC] == "AAC"
        assert opts[CK_ORIGINAL] is False

    def test_adds_original_key_if_missing(self):
        opts = {CK_VCODEC: "Auto", CK_ACODEC: "Auto"}
        VideodlConfig._migrate_original(opts)
        assert CK_ORIGINAL in opts
        assert opts[CK_ORIGINAL] is False

    def test_preserves_existing_original_flag(self):
        opts = {CK_VCODEC: "Auto", CK_ACODEC: "Auto", CK_ORIGINAL: True}
        VideodlConfig._migrate_original(opts)
        assert opts[CK_ORIGINAL] is True
