import logging
import os
import subprocess
import time
import urllib.request
from platform import system
from zipfile import ZipFile

import flet as ft

from utils.sys_architecture import ARCHITECTURE

logger = logging.getLogger("videodl")

_ARIA2C_VERSION = "1.37.0"
_ARIA2C_GITHUB_BASE = f"https://github.com/aria2/aria2/releases/download/release-{_ARIA2C_VERSION}"


def get_aria2c_install_folder() -> str:
    platform = system()
    if platform == "Windows":
        return os.path.join(os.getenv("LOCALAPPDATA", ""), "video-dl")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "video-dl")


def _get_aria2c_windows_filename() -> str | None:
    if ARCHITECTURE in ("x86_64", "arm64"):
        return f"aria2-{_ARIA2C_VERSION}-win-64bit-build1.zip"
    elif ARCHITECTURE == "x86":
        return f"aria2-{_ARIA2C_VERSION}-win-32bit-build1.zip"
    return None


def aria2c_progress_page(page: ft.Page) -> None:
    """Flet page handler: download and install aria2c on Windows."""
    page.window.width = 450
    page.window.height = 180
    folder_path = get_aria2c_install_folder()
    page.title = "aria2c installation"
    explanation = ft.Text(
        "aria2c speeds up downloads by using multiple connections.\nInstalling it now...",
        size=14,
    )
    progress_bar = ft.ProgressBar(width=350)
    download_text = ft.Text(f"Downloading to: {folder_path}", size=12, italic=True)

    page.add(explanation, download_text, progress_bar)
    page.update()

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded / total_size
            progress_bar.value = percent
            progress_bar.label = f"{percent * 100:.2f}%"  # type: ignore[attr-defined]
            page.update()

    def install_aria2c():
        try:
            os.makedirs(folder_path, exist_ok=True)
            filename = _get_aria2c_windows_filename()
            if not filename:
                logger.error("Unsupported architecture for aria2c")
                return

            asset_url = f"{_ARIA2C_GITHUB_BASE}/{filename}"
            zip_path = os.path.join(folder_path, filename)

            download_text.value = f"Downloading: {filename}..."
            page.update()

            urllib.request.urlretrieve(asset_url, zip_path, reporthook)

            with ZipFile(zip_path, "r") as zip_ref:
                for member in zip_ref.namelist():
                    member_path = os.path.realpath(os.path.join(folder_path, member))
                    if not member_path.startswith(
                        os.path.realpath(folder_path) + os.sep
                    ) and member_path != os.path.realpath(folder_path):
                        raise ValueError(f"Zip path traversal blocked: {member}")
                zip_ref.extractall(folder_path)

            # The zip extracts into a subfolder like aria2-1.37.0-win-64bit-build1/
            # Move aria2c.exe to the install folder root
            subfolder = filename.removesuffix(".zip")
            extracted_exe = os.path.join(folder_path, subfolder, "aria2c.exe")
            target_exe = os.path.join(folder_path, "aria2c.exe")
            if os.path.isfile(extracted_exe) and not os.path.isfile(target_exe):
                os.rename(extracted_exe, target_exe)

            progress_bar.value = 1.0
            progress_bar.label = "Download complete"  # type: ignore[attr-defined]
            page.update()

        except Exception as e:
            logger.error(f"aria2c installation error: {e}")

    install_aria2c()
    page.run_task(page.window.destroy)


def aria2c_brew_install_page(page: ft.Page) -> None:
    """Flet page handler: install aria2c via brew on macOS."""
    page.window.width = 450
    page.window.height = 180
    page.title = "aria2c installation"
    explanation = ft.Text(
        "aria2c speeds up downloads by using multiple connections.\nInstalling it now via Homebrew...",
        size=14,
    )
    status_text = ft.Text("Running: brew install aria2", size=12, italic=True)
    progress_ring = ft.ProgressRing(width=40, height=40)

    page.add(explanation, status_text, progress_ring)
    page.update()

    try:
        result = subprocess.run(
            ["brew", "install", "aria2"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            status_text.value = "aria2c installed successfully!"
        else:
            status_text.value = "brew install aria2 failed."
            logger.error(f"brew install aria2 failed: {result.stderr}")
    except FileNotFoundError:
        status_text.value = "Homebrew not found."
        logger.error("brew not found, cannot install aria2c")
    except subprocess.TimeoutExpired:
        status_text.value = "Installation timed out."
        logger.error("brew install aria2 timed out")
    except Exception as e:
        status_text.value = f"Error: {e}"
        logger.error(f"aria2c brew install error: {e}")

    page.update()
    time.sleep(2)
    page.run_task(page.window.destroy)


def aria2c_info_linux(page: ft.Page) -> None:
    """Flet page handler: inform Linux users how to install aria2c."""
    page.window.width = 450
    page.window.height = 200
    page.title = "aria2c recommended"
    page.add(
        ft.Text(
            "aria2c enables faster downloads using multiple connections.",
            size=14,
        ),
        ft.Text("Install it with:", size=14, weight=ft.FontWeight.BOLD),
        ft.Text("sudo apt install aria2", selectable=True, font_family="monospace"),
        ft.Text("(or equivalent for your distribution)", size=12, italic=True),
        ft.TextButton(
            "Continue without aria2c",
            on_click=lambda e: page.run_task(page.window.destroy),
        ),
    )
    page.update()
