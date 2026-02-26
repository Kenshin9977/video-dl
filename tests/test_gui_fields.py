import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before importing gui.app
for mod in [
    "flet",
    "darkdetect",
    "quantiphy",
    "core.download",
    "core.hwaccel",
    "gui.config",
    "gui.options",
    "utils.sponsor_block_dict",
    "utils.parse_util",
    "utils.sys_utils",
    "i18n",
    "i18n.lang",
    "sys_vars",
    "core.exceptions",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from gui.app import VideodlApp  # noqa: E402


class MockControl:
    """Minimal mock for Flet TextField controls with a .value attribute."""

    def __init__(self, value):
        self.value = value


class TestTimecodesAreValid:
    def _make_app(self, start_on, end_on, start_vals, end_vals):
        app = MagicMock(spec=VideodlApp)
        app.start_checkbox = MagicMock(value=start_on)
        app.end_checkbox = MagicMock(value=end_on)
        app.start_controls = [MockControl(v) for v in start_vals]
        app.end_controls = [MockControl(v) for v in end_vals]
        return app

    def test_both_off(self):
        app = self._make_app(False, False, ("00", "00", "00"), ("00", "00", "00"))
        assert VideodlApp._timecodes_are_valid(app) is True

    def test_start_only_valid(self):
        app = self._make_app(True, False, ("01", "30", "00"), ("00", "00", "00"))
        assert VideodlApp._timecodes_are_valid(app) is True

    def test_start_only_invalid(self):
        app = self._make_app(True, False, ("00", "60", "00"), ("00", "00", "00"))
        assert VideodlApp._timecodes_are_valid(app) is False

    def test_end_only_valid(self):
        app = self._make_app(False, True, ("00", "00", "00"), ("01", "30", "00"))
        assert VideodlApp._timecodes_are_valid(app) is True

    def test_end_only_invalid(self):
        app = self._make_app(False, True, ("00", "00", "00"), ("00", "00", "cc"))
        assert VideodlApp._timecodes_are_valid(app) is False

    def test_end_after_start(self):
        app = self._make_app(True, True, ("00", "00", "00"), ("00", "00", "01"))
        assert VideodlApp._timecodes_are_valid(app) is True

    def test_end_equals_start(self):
        app = self._make_app(True, True, ("00", "00", "00"), ("00", "00", "00"))
        assert VideodlApp._timecodes_are_valid(app) is False

    def test_end_before_start(self):
        app = self._make_app(True, True, ("00", "01", "00"), ("00", "00", "30"))
        assert VideodlApp._timecodes_are_valid(app) is False

    def test_end_hour_greater(self):
        app = self._make_app(True, True, ("00", "59", "59"), ("01", "00", "00"))
        assert VideodlApp._timecodes_are_valid(app) is True
