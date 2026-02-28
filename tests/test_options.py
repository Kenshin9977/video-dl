from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Mock i18n before importing gui.options (gt() is called at import time)
_mock_lang = MagicMock()
_mock_lang.get_text.return_value = "None"
_mock_lang.GuiField = MagicMock()

for _mod in ["i18n", "i18n.lang"]:
    sys.modules[_mod] = MagicMock()
sys.modules["i18n.lang"] = _mock_lang

sys.modules.pop("gui.options", None)

from gui.options import ACODECS, BROWSERS, FRAMERATE, QUALITY, VCODECS  # noqa: E402


class TestFramerate:
    def test_expected_values(self):
        assert FRAMERATE == ["30", "60"]

    def test_all_numeric_strings(self):
        for fps in FRAMERATE:
            assert fps.isdigit()


class TestQuality:
    def test_descending_order(self):
        heights = [int(q.rstrip("p")) for q in QUALITY]
        assert heights == sorted(heights, reverse=True)

    def test_all_end_with_p(self):
        for q in QUALITY:
            assert q.endswith("p")

    def test_includes_common_resolutions(self):
        for expected in ["1080p", "720p", "480p", "360p"]:
            assert expected in QUALITY


class TestVcodecs:
    def test_auto_is_first(self):
        assert VCODECS[0] == "Auto"

    def test_contains_expected_codecs(self):
        for codec in ["x264", "x265", "ProRes", "AV1"]:
            assert codec in VCODECS


class TestAcodecs:
    def test_auto_is_first(self):
        assert ACODECS[0] == "Auto"

    def test_contains_expected_codecs(self):
        for codec in ["AAC", "FLAC", "MP3", "OPUS"]:
            assert codec in ACODECS


class TestBrowsers:
    def test_none_is_first(self):
        assert BROWSERS[0] == "None"

    def test_contains_common_browsers(self):
        for browser in ["Chrome", "Firefox", "Safari", "Edge"]:
            assert browser in BROWSERS

    def test_all_are_strings(self):
        for b in BROWSERS:
            assert isinstance(b, str)
