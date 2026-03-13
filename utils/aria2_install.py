import logging
import os
import stat
import time
import urllib.request
from platform import machine, system

import flet as ft

logger = logging.getLogger("videodl")

_ARIA2C_REPO = "Kenshin9977/aria2"
_ARIA2C_RELEASE_TAG = "release-2.0.0"
_ARIA2C_BASE_URL = f"https://github.com/{_ARIA2C_REPO}/releases/download/{_ARIA2C_RELEASE_TAG}"

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

    install()
    time.sleep(1)
    page.run_task(page.window.destroy)
