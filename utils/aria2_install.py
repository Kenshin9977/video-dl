import hashlib
import logging
import os
import stat
import threading
import time
import urllib.request
from platform import machine, system

import flet as ft

from deps import ARIA2_REPO, ARIA2_TAG

logger = logging.getLogger("videodl")

_ARIA2C_BASE_URL = f"https://github.com/{ARIA2_REPO}/releases/download/{ARIA2_TAG}"

# Map (platform, arch) to release asset name
_ASSET_MAP = {
    ("Windows", "x86_64"): "aria2c-windows-x86_64.exe",
    ("Windows", "AMD64"): "aria2c-windows-x86_64.exe",
    ("Darwin", "arm64"): "aria2c-macos-arm64",
    ("Linux", "x86_64"): "aria2c-linux-x86_64",
    ("Linux", "aarch64"): "aria2c-linux-aarch64",
}


def _get_asset_name() -> str | None:
    key = (system(), machine())
    return _ASSET_MAP.get(key)


def _published_sha256(asset: str) -> str | None:
    """Read an asset's digest from the SHA256SUMS file shipped with the release."""
    with urllib.request.urlopen(f"{_ARIA2C_BASE_URL}/SHA256SUMS") as response:
        sums = response.read().decode()

    for line in sums.splitlines():
        digest, _, name = line.partition(" ")
        if name.strip() == asset:
            return digest.strip()
    return None


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_download(path: str, asset: str) -> None:
    """Check a downloaded asset against the digest published with the release.

    Fails closed: we are about to hand this file to the OS as an executable, so
    an unverifiable download is treated the same as a corrupted one. The caller
    deletes it and the app runs without aria2c, which only costs download speed.
    """
    expected = _published_sha256(asset)
    if expected is None:
        raise ValueError(f"No published checksum for {asset}")

    actual = _file_sha256(path)
    if actual != expected:
        raise ValueError(f"Checksum mismatch for {asset}: expected {expected}, got {actual}")


def get_aria2c_install_folder() -> str:
    platform = system()
    if platform == "Windows":
        return os.path.join(os.getenv("LOCALAPPDATA", ""), "video-dl")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "video-dl")


def _get_installed_path() -> str:
    ext = ".exe" if system() == "Windows" else ""
    return os.path.join(get_aria2c_install_folder(), f"aria2c{ext}")


def aria2c_progress_page(page: ft.Page) -> None:
    """Flet page handler: download aria2c from GitHub release."""
    page.window.width = 450
    page.window.height = 180
    install_path = _get_installed_path()
    page.title = "aria2c installation"
    explanation = ft.Text(
        "aria2c speeds up downloads by using multiple connections.\nInstalling it now...",
        size=14,
    )
    progress_bar = ft.ProgressBar(width=350)
    download_text = ft.Text(f"Downloading to: {os.path.dirname(install_path)}", size=12, italic=True)

    page.add(explanation, download_text, progress_bar)
    page.update()

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded / total_size
            progress_bar.value = percent
            page.update()

    def install():
        try:
            asset = _get_asset_name()
            if not asset:
                logger.error(f"No aria2c binary for {system()} {machine()}")
                return

            os.makedirs(os.path.dirname(install_path), exist_ok=True)
            url = f"{_ARIA2C_BASE_URL}/{asset}"

            download_text.value = f"Downloading: {asset}..."
            page.update()

            urllib.request.urlretrieve(url, install_path, reporthook)

            try:
                verify_download(install_path, asset)
            except Exception:
                os.remove(install_path)
                raise

            # Make executable on non-Windows
            if system() != "Windows":
                st = os.stat(install_path)
                os.chmod(install_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

            progress_bar.value = 1.0
            download_text.value = "Installation complete!"
            page.update()

        except Exception as e:
            logger.error(f"aria2c installation error: {e}")
            download_text.value = f"Error: {e}"
            page.update()
        finally:
            time.sleep(1)
            page.window.destroy()

    threading.Thread(target=install, daemon=True).start()
