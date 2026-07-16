from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import threading
import urllib.request
from pathlib import PurePosixPath
from typing import TypedDict
from zipfile import ZipFile

import flet as ft

from utils.sys_architecture import ARCHITECTURE

logger = logging.getLogger("videodl")


def extract_ffmpeg(zip_path: str, folder_path: str) -> None:
    """Extract the archive's bin/ directory flat into folder_path.

    FFmpeg-Builds archives nest everything under
    ffmpeg-master-latest-<arch>-gpl-shared/bin/, while the app looks for
    ffmpeg.exe and ffprobe.exe directly inside folder_path. The shared build
    keeps its DLLs in that same bin/ directory, so they come along.

    Members are written under their basename, which makes zip path traversal
    impossible by construction.
    """
    extracted = set()
    with ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            if member.is_dir():
                continue
            member_path = PurePosixPath(member.filename)
            if member_path.parent.name != "bin":
                continue
            target_path = os.path.join(folder_path, member_path.name)
            with zip_ref.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
            extracted.add(member_path.name)

    missing = {"ffmpeg.exe", "ffprobe.exe"} - extracted
    if missing:
        raise FileNotFoundError(f"{', '.join(sorted(missing))} missing from {os.path.basename(zip_path)}")


def ffmpeg_progress_page(page: ft.Page) -> None:
    page.window.width = 400
    page.window.height = 150
    folder_path = os.path.join(os.getenv("LOCALAPPDATA", ""), "video-dl")
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
            progress_bar.label = f"{percent * 100:.2f}%"  # type: ignore[attr-defined]
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

            extract_ffmpeg(zip_path, folder_path)
            os.remove(zip_path)

            progress_bar.value = 1.0
            progress_bar.label = "Download complete"  # type: ignore[attr-defined]
            page.update()

        except Exception as e:
            logger.error(f"FFmpeg installation error: {e}")
        finally:
            # Coroutine in Flet 0.81, so schedule it rather than calling it bare from
            # this worker thread, where it would never run and hang the app.
            page.run_task(page.window.close)

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
            raise Exception(f"Error occurred while retrieving FFmpeg from GitHub: {e}") from e
        return ""

    threading.Thread(target=install_ffmpeg, daemon=True).start()


class _FfmpegMissingInfo(TypedDict):
    width: int
    message: str
    url: str | None


_FFMPEG_MISSING: dict[str, _FfmpegMissingInfo] = {
    "Windows": {
        "width": 400,
        "message": (
            "FFmpeg is missing. On Windows, FFmpeg should be installed if "
            "missing.\nThis error shouldn't happen. Please open an issue on "
            "the following link:"
        ),
        "url": "[Open an issue on GitHub](https://github.com/Kenshin9977/video-dl/issues)",
    },
    "Darwin": {
        "width": 460,
        "message": (
            "FFmpeg is missing or won't run. A Homebrew update can leave it broken; "
            "install or repair it from a terminal with:  brew reinstall ffmpeg"
        ),
        "url": "[Get Homebrew](https://brew.sh)",
    },
    "Linux": {
        "width": 344,
        "message": (
            "FFmpeg is missing. On Linux you can install FFmpeg \nthrough "
            'your package manager using the package name "ffmpeg"'
        ),
        "url": None,
    },
}


def _ffmpeg_missing_page(platform: str):
    """Return a Flet page handler for the ffmpeg-missing dialog."""
    info = _FFMPEG_MISSING[platform]

    def handler(page: ft.Page):
        page.window.width = info["width"]
        page.window.height = 150
        page.title = "FFmpeg required"
        page.add(
            ft.Text("Video-dl needs FFmpeg and FFprobe to work. ", color="red"),
            ft.Text(info["message"]),
        )
        if info["url"]:
            page.add(
                ft.Markdown(
                    info["url"],
                    on_tap_link=lambda e: page.launch_url(e.data),
                )
            )
        page.update()

    return handler


ffmpeg_missing_on_windows = _ffmpeg_missing_page("Windows")
ffmpeg_missing_on_mac = _ffmpeg_missing_page("Darwin")
ffmpeg_missing_on_linux = _ffmpeg_missing_page("Linux")
