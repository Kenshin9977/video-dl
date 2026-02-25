import json
import logging
import os
import stat
import urllib.request
from platform import system
from zipfile import ZipFile

import flet as ft

from utils.sys_architecture import ARCHITECTURE

logger = logging.getLogger("videodl")

_QUICKJS_BASE_URL = "https://bellard.org/quickjs/binary_releases"


def get_quickjs_install_folder() -> str:
    platform = system()
    if platform == "Windows":
        return os.path.join(os.getenv("LOCALAPPDATA", ""), "video-dl")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "video-dl")


def _get_quickjs_platform_tag() -> str:
    platform = system()
    if platform == "Windows":
        if ARCHITECTURE == "x86_64":
            return "win-x86_64"
        elif ARCHITECTURE == "x86":
            return "win-i686"
        return "cosmo"
    elif platform == "Linux" and ARCHITECTURE == "x86_64":
        return "linux-x86_64"
    # macOS (all archs) and Linux ARM use the universal cosmo build
    return "cosmo"


def quickjs_progress_page(page: ft.Page) -> None:
    page.window.width = 400
    page.window.height = 150
    folder_path = get_quickjs_install_folder()
    page.title = "QuickJS installation progress"
    progress_bar = ft.ProgressBar(width=300)
    download_text = ft.Text(f"Downloading QuickJS to: {folder_path}", size=16)

    page.add(download_text, progress_bar)
    page.update()

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded / total_size
            progress_bar.value = percent
            progress_bar.label = f"{percent * 100:.2f}%"
            page.update()

    def install_quickjs():
        try:
            os.makedirs(folder_path, exist_ok=True)
            platform_tag = _get_quickjs_platform_tag()

            archive_name = download_quickjs(platform_tag, folder_path)
            zip_path = os.path.join(folder_path, archive_name)

            with ZipFile(zip_path, "r") as zip_ref:
                for member in zip_ref.namelist():
                    member_path = os.path.realpath(os.path.join(folder_path, member))
                    if not member_path.startswith(
                        os.path.realpath(folder_path) + os.sep
                    ) and member_path != os.path.realpath(folder_path):
                        raise ValueError(f"Zip path traversal blocked: {member}")
                zip_ref.extractall(folder_path)

            # Make qjs executable on Unix
            if system() != "Windows":
                for name in os.listdir(folder_path):
                    if name.startswith("qjs"):
                        qjs_path = os.path.join(folder_path, name)
                        st = os.stat(qjs_path)
                        os.chmod(qjs_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

            progress_bar.value = 1.0
            progress_bar.label = "Download complete"
            page.update()

        except Exception as e:
            logger.error(f"QuickJS installation error: {e}")

    def download_quickjs(platform_tag: str, download_folder) -> str:
        try:
            with urllib.request.urlopen(f"{_QUICKJS_BASE_URL}/LATEST.json") as response:
                latest = json.load(response)
            version = latest["version"]
            filename = f"quickjs-{platform_tag}-{version}.zip"
            asset_url = f"{_QUICKJS_BASE_URL}/{filename}"
            file_path = os.path.join(download_folder, filename)

            download_text.value = f"Downloading: {filename}..."
            page.update()

            urllib.request.urlretrieve(asset_url, file_path, reporthook)
            return filename

        except Exception as e:
            raise Exception(f"Error occurred while retrieving QuickJS: {e}") from e

    install_quickjs()
    page.run_task(page.window.destroy)


def quickjs_missing(page: ft.Page):
    """Flet page handler for the quickjs-missing dialog."""
    page.window.width = 400
    page.window.height = 150
    page.title = "QuickJS required"
    page.add(
        ft.Text("Video-dl needs QuickJS for YouTube support. ", color="red"),
        ft.Text("QuickJS could not be installed automatically.\nPlease open an issue on the following link:"),
        ft.Markdown(
            "[Open an issue on GitHub](https://github.com/Kenshin9977/video-dl/issues)",
            on_tap_link=lambda e: page.launch_url(e.data),
        ),
    )
    page.update()
