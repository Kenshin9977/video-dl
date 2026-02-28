from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

# Ensure we get the real i18n.lang, not a mock left by another test file
for _mod in ["i18n.lang", "i18n"]:
    sys.modules.pop(_mod, None)

import i18n.lang as _real_lang_module  # noqa: E402
from i18n.lang import (  # noqa: E402
    GuiField,
    Language,
    _get_language,
    get_available_languages_name,
    get_current_language_name,
    get_text,
    set_current_language,
)


class TestLanguageEnum:
    def test_has_expected_members(self):
        assert hasattr(Language, "english")
        assert hasattr(Language, "french")
        assert hasattr(Language, "german")

    def test_members_are_distinct(self):
        values = [lang.value for lang in Language]
        assert len(values) == len(set(values))


class TestGuiFieldEnum:
    def test_has_at_least_60_members(self):
        assert len(GuiField) >= 60

    def test_key_fields_exist(self):
        for name in ["link", "download", "cancel_button", "dl_finish", "extracting_cookies", "fetching_info"]:
            assert hasattr(GuiField, name)


class TestGetLanguage:
    def setup_method(self):
        # Restore the real module in sys.modules so @patch("i18n.lang.locale")
        # targets the same object where _get_language looks up `locale`.
        sys.modules["i18n.lang"] = _real_lang_module

    @patch("i18n.lang.locale")
    def test_english_locale(self, mock_locale):
        mock_locale.getlocale.return_value = ("en_US", "UTF-8")
        assert _get_language() == Language.english

    @patch("i18n.lang.locale")
    def test_french_locale(self, mock_locale):
        mock_locale.getlocale.return_value = ("fr_FR", "UTF-8")
        assert _get_language() == Language.french

    @patch("i18n.lang.locale")
    def test_german_locale(self, mock_locale):
        mock_locale.getlocale.return_value = ("de_DE", "UTF-8")
        assert _get_language() == Language.german

    @patch("i18n.lang.locale")
    def test_unknown_locale_defaults_to_english(self, mock_locale):
        mock_locale.getlocale.return_value = ("ja_JP", "UTF-8")
        assert _get_language() == Language.english

    @patch("i18n.lang.locale")
    def test_none_locale_defaults_to_english(self, mock_locale):
        mock_locale.getlocale.return_value = (None, None)
        assert _get_language() == Language.english


class TestGetText:
    def setup_method(self):
        names = get_available_languages_name()
        set_current_language(names[0])  # Reset to English

    def test_returns_string_for_link(self):
        result = get_text(GuiField.link)
        assert isinstance(result, str)
        assert result == "Link"

    def test_cancel_button_english(self):
        assert get_text(GuiField.cancel_button) == "Cancel"

    def test_dl_finish_english(self):
        assert get_text(GuiField.dl_finish) == "Download finished."

    def test_width_returns_int(self):
        result = get_text(GuiField.width)
        assert isinstance(result, int)

    @pytest.mark.parametrize("field", list(GuiField))
    def test_every_field_has_translation(self, field):
        result = get_text(field)
        assert result is not None


class TestSetCurrentLanguage:
    def setup_method(self):
        names = get_available_languages_name()
        set_current_language(names[0])  # Reset to English

    def test_switch_to_french(self):
        names = get_available_languages_name()
        set_current_language(names[1])
        assert get_text(GuiField.link) == "Lien"

    def test_switch_to_german(self):
        names = get_available_languages_name()
        set_current_language(names[2])
        assert get_text(GuiField.cancel_button) == "Abbrechen"

    def test_invalid_name_is_noop(self):
        set_current_language("nonexistent_language")
        assert get_text(GuiField.cancel_button) == "Cancel"

    def test_roundtrip(self):
        names = get_available_languages_name()
        set_current_language(names[1])  # French
        assert get_text(GuiField.cancel_button) == "Annuler"
        set_current_language(names[0])  # Back to English
        assert get_text(GuiField.cancel_button) == "Cancel"


class TestGetAvailableLanguagesName:
    def test_returns_list_of_three(self):
        result = get_available_languages_name()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_all_entries_are_strings(self):
        for name in get_available_languages_name():
            assert isinstance(name, str)


class TestGetCurrentLanguageName:
    def test_returns_string(self):
        assert isinstance(get_current_language_name(), str)

    def test_is_in_available_list(self):
        assert get_current_language_name() in get_available_languages_name()
