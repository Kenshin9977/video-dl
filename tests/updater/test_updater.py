import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock heavy dependencies before importing
for mod in [
    "tufup",
    "tufup.client",
    "tufup.repo",
    "flet",
    "darkdetect",
    "quantiphy",
    "i18n",
    "i18n.lang",
    "sys_vars",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from updater.client import _get_install_dir, _get_update_cache_dir  # noqa: E402


class TestGetInstallDir:
    def test_frozen(self):
        with patch("updater.client.FROZEN", True), patch("sys.executable", "/opt/video-dl/video-dl"):
            result = _get_install_dir()
            assert result == pathlib.Path("/opt/video-dl")

    def test_not_frozen(self):
        with patch("updater.client.FROZEN", False):
            result = _get_install_dir()
            # Should be parent of updater/ → project root
            assert result.is_absolute()


class TestGetUpdateCacheDir:
    def test_linux(self):
        with patch("sys.platform", "linux"), patch("updater.client.APP_NAME", "video-dl"):
            result = _get_update_cache_dir()
            assert "video-dl" in str(result)
            assert "update_cache" in str(result)
            assert ".local/share" in str(result)

    def test_darwin(self):
        with patch("sys.platform", "darwin"), patch("updater.client.APP_NAME", "video-dl"):
            result = _get_update_cache_dir()
            assert "video-dl" in str(result)
            assert "update_cache" in str(result)
            assert "Library" in str(result)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_windows(self):
        with patch("sys.platform", "win32"), patch("updater.client.APP_NAME", "video-dl"):
            result = _get_update_cache_dir()
            assert "video-dl" in str(result)
            assert "update_cache" in str(result)


class TestCheckForUpdates:
    def test_returns_false_on_import_error(self):
        """When tufup is not installed, check_for_updates should fail gracefully."""
        mock_tufup = MagicMock()
        mock_tufup.client.Client.side_effect = Exception("no tufup")
        with patch.dict(sys.modules, {"tufup": mock_tufup, "tufup.client": mock_tufup.client}):
            from updater.client import check_for_updates

            assert check_for_updates() is False

    def test_returns_false_when_no_update(self):
        mock_client_cls = MagicMock()
        mock_client = mock_client_cls.return_value
        mock_client.check_for_updates.return_value = None
        mock_tufup_client = MagicMock()
        mock_tufup_client.Client = mock_client_cls

        with patch.dict(sys.modules, {"tufup.client": mock_tufup_client}):
            from updater.client import check_for_updates

            assert check_for_updates() is False
