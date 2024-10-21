import json
import logging
import os
import re
import sys
import urllib.request
from zipfile import ZipFile

import flet as ft

from utils.sys_architecture import ARCHITECTURE

logger = logging.getLogger()


def ffmpeg_progress_page(page: ft.Page) -> None:
    page.window_width = 400
    page.window_height = 150
    folder_path = os.path.join(os.getenv("LOCALAPPDATA"), "video-dl")
    page.title = "FFmpeg installation progress"
    progress_bar = ft.ProgressBar(width=300)
    download_text = ft.Text(f"Downloading FFmpeg to: {folder_path}", size=16)

    page.add(download_text, progress_bar)
    page.update()

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded / total_size
            progress_bar.value = percent
            progress_bar.label = f"{percent * 100:.2f}%"
            page.update()

    def install_ffmpeg():
        try:
            os.makedirs(folder_path, exist_ok=True)
            if ARCHITECTURE == "x86":
                bits_archi = "32"
            elif ARCHITECTURE == "x86_64":
                bits_archi = "64"
            elif ARCHITECTURE == "arm64":
                bits_archi = "arm64"
            else:
                sys.exit(-1)

            archive_name = download_ffmpeg(bits_archi, folder_path)
            zip_path = os.path.join(folder_path, archive_name)

            with ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(folder_path)

            progress_bar.value = 1.0
            progress_bar.label = "Download complete"
            page.update()

        except Exception as e:
            ft.AlertDialog(title="Error", content=f"An error occurred: {e}").show(page)

    def download_ffmpeg(bits_archi: str, download_folder) -> str:
        api_url = "https://api.github.com/repos/yt-dlp/FFmpeg-Builds/releases/latest"
        asset_pattern = f"-win{bits_archi}-gpl-shared.zip"
        try:
            with urllib.request.urlopen(api_url) as response:
                release_info = json.load(response)

            assets = release_info.get("assets", [])
            for asset in assets:
                if re.search(asset_pattern, asset["name"]):
                    asset_url = asset["browser_download_url"]
                    file_name = os.path.join(download_folder, asset["name"])

                    download_text.value = f"Downloading: {asset['name']}..."
                    page.update()

                    urllib.request.urlretrieve(asset_url, file_name, reporthook)
                    return asset["name"]

        except Exception as e:
            raise Exception(f"Error occurred while retrieving FFmpeg from GitHub: {e}")

    install_ffmpeg()
    page.window_destroy()


def ffmpeg_missing_on_windows(page: ft.Page) -> None:
    page.window_width = 400
    page.window_height = 150
    message = "FFmpeg is missing. "
    message += (
        "On Windows, FFmpeg should be installed if missing.\n"
        "This error shouldn't happen. Please open an issue on the following link:"
    )
    url = "[Open an issue on GitHub](https://github.com/Kenshin9977/video-dl/issues)"
    page.title = "FFmpeg required"
    error_message = "Video-dl needs FFmpeg and FFprobe to work. "
    page.add(
        ft.Text(error_message, color="red"),
        ft.Text(message),
        ft.Markdown(url, on_tap_link=lambda e: page.launch_url(e.data)),
    )
    page.update()


def ffmpeg_missing_on_mac(page: ft.Page) -> None:
    page.window_width = 344
    page.window_height = 150
    message = "FFmpeg is missing. "
    message += "On MacOS you can follow this guide to install it:"
    url = "[Install FFmpeg](https://macappstore.org/ffmpeg/)"
    page.title = "FFmpeg required"
    error_message = "Video-dl needs FFmpeg and FFprobe to work. "
    page.add(
        ft.Text(error_message, color="red"),
        ft.Text(message),
        ft.Markdown(url, on_tap_link=lambda e: page.launch_url(e.data)),
    )
    page.update()


def ffmpeg_missing_on_linux(page: ft.Page) -> None:
    page.window_width = 344
    page.window_height = 150
    message = "FFmpeg is missing. "
    message += (
        "On Linux you can install FFmpeg \nthrough your "
        'package manager using the package name "ffmpeg"'
    )
    page.title = "FFmpeg required"
    error_message = "Video-dl needs FFmpeg and FFprobe to work. "
    page.add(ft.Text(error_message, color="red"), ft.Text(message))
    page.update()
