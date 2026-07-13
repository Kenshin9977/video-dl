import hashlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.modules.setdefault("flet", MagicMock())

# Other test modules replace utils.aria2_install with a MagicMock in sys.modules.
# Drop that first, so the names below are bound to the real module whatever the
# collection order turns out to be.
sys.modules.pop("utils.aria2_install", None)

from utils.aria2_install import _ARIA2C_RELEASE_TAG, verify_download  # noqa: E402

ASSET = "aria2c-linux-x86_64"


def _sums_response(payload: bytes, asset: str = ASSET):
    """Fake the SHA256SUMS asset published alongside the binaries."""
    digest = hashlib.sha256(payload).hexdigest()
    body = f"{digest}  {asset}\nffffffff  aria2c-macos-arm64\n".encode()
    response = MagicMock()
    response.read.return_value = body
    response.__enter__ = lambda self: self
    response.__exit__ = lambda *_: None
    return response


class TestVerifyDownload:
    def test_accepts_a_matching_digest(self, tmp_path):
        payload = b"aria2c binary"
        binary = tmp_path / ASSET
        binary.write_bytes(payload)

        with patch("urllib.request.urlopen", return_value=_sums_response(payload)):
            verify_download(str(binary), ASSET)

    def test_rejects_a_tampered_binary(self, tmp_path):
        binary = tmp_path / ASSET
        binary.write_bytes(b"not what was published")

        with (
            patch("urllib.request.urlopen", return_value=_sums_response(b"aria2c binary")),
            pytest.raises(ValueError, match="Checksum mismatch"),
        ):
            verify_download(str(binary), ASSET)

    def test_rejects_an_asset_absent_from_the_sums_file(self, tmp_path):
        payload = b"aria2c binary"
        binary = tmp_path / ASSET
        binary.write_bytes(payload)

        with (
            patch("urllib.request.urlopen", return_value=_sums_response(payload, asset="aria2c-windows-x86_64.exe")),
            pytest.raises(ValueError, match="No published checksum"),
        ):
            verify_download(str(binary), ASSET)

    def test_propagates_a_failure_to_fetch_the_sums_file(self, tmp_path):
        binary = tmp_path / ASSET
        binary.write_bytes(b"aria2c binary")

        with (
            patch("urllib.request.urlopen", side_effect=OSError("network down")),
            pytest.raises(OSError, match="network down"),
        ):
            verify_download(str(binary), ASSET)


class TestReleasePinning:
    def test_desktop_tag_matches_the_tag_bundled_into_the_apk(self):
        """The APK and the desktop download must ship the same aria2c build."""
        workflow = Path(__file__).parent.parent / ".github" / "workflows" / "build.yml"
        assert f"ARIA2_TAG: {_ARIA2C_RELEASE_TAG}" in workflow.read_text(encoding="utf-8")
