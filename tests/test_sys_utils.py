import sys
from unittest.mock import MagicMock, patch

# Mock heavy dependencies that sys_utils imports at module level.
# Force-set even if already mocked by another test, to ensure consistency.
for mod in [
    "flet",
    "darkdetect",
    "quantiphy",
    "i18n",
    "i18n.lang",
    "sys_vars",
    "utils.aria2_install",
    "utils.ffmpeg_install",
    "utils.quickjs_install",
]:
    sys.modules[mod] = MagicMock()

# Force reimport the real sys_utils module (may have been mocked by another test)
if "utils.sys_utils" in sys.modules:
    del sys.modules["utils.sys_utils"]

from utils.sys_utils import (  # noqa: E402
    _find_executable,
    _get_extension_for_platform,
    get_default_download_path,
)


class TestGetExtensionForPlatform:
    def test_windows(self):
        with patch("utils.sys_utils.PLATFORM", "Windows"):
            assert _get_extension_for_platform() == ".exe"

    def test_linux(self):
        with patch("utils.sys_utils.PLATFORM", "Linux"):
            assert _get_extension_for_platform() == ""

    def test_darwin(self):
        with patch("utils.sys_utils.PLATFORM", "Darwin"):
            assert _get_extension_for_platform() == ""


class TestFindExecutable:
    def test_found_in_path(self):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert _find_executable("ffmpeg") == "/usr/bin/ffmpeg"

    def test_found_in_fallback_dir(self):
        with (
            patch("shutil.which", return_value=None),
            patch("os.path.isfile", return_value=True),
            patch("os.access", return_value=True),
        ):
            result = _find_executable("ffmpeg")
            assert result is not None
            assert "ffmpeg" in result

    def test_not_found(self):
        with (
            patch("shutil.which", return_value=None),
            patch("os.path.isfile", return_value=False),
        ):
            assert _find_executable("nonexistent") is None


class TestGetDefaultDownloadPath:
    def test_unix_downloads_exists(self, tmp_path):
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        with (
            patch("utils.sys_utils.system", return_value="Linux"),
            patch("os.path.expanduser", return_value=str(tmp_path)),
            patch("os.path.isdir", return_value=True),
        ):
            result = get_default_download_path()
            assert "Downloads" in result

    def test_unix_downloads_missing(self, tmp_path):
        with (
            patch("utils.sys_utils.system", return_value="Linux"),
            patch("os.path.expanduser", return_value=str(tmp_path)),
            patch("os.path.isdir", return_value=False),
        ):
            assert get_default_download_path() == ""
