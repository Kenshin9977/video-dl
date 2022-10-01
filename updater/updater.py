import io
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from os import getcwd, mkdir, path, remove
from platform import system
from shutil import move, rmtree
from subprocess import Popen
from zipfile import ZipFile

from lang import GuiField, get_text
from quantiphy import Quantity
from requests import get
from sys_vars import ARCHITECTURE
from utils.crypto_util import compute_sha256
from utils.gui_utils import create_progress_bar
from utils.sys_utils import (
    APP_NAME,
    APP_VERSION,
    VERSIONS_ARCHIVE_NAME,
    VERSIONS_JSON_NAME,
    gen_archive_name,
    get_bin_ext_for_platform,
)
from yt_dlp.utils import traverse_obj

log = logging.getLogger()


class Updater:
    def __init__(self):
        self.platform = system()
        self.app_archive_name = gen_archive_name()
        self.app_bin_name = get_bin_ext_for_platform()
        self.versions_archive_name = VERSIONS_ARCHIVE_NAME
        self.versions_json_name = VERSIONS_JSON_NAME

        self.update_prog_win = create_progress_bar(
            get_text(GuiField.update), True
        )
        self.versions_dict = self._get_versions_json()
        self.latest_version = (
            traverse_obj(
                self.versions_dict,
                (APP_NAME, self.platform, ARCHITECTURE, "latest_version"),
            )
            or APP_VERSION
        )
        self.update_canceled = False
        self.time_last_update = datetime.now()
        self.size_last_update = 0

    def update_app(self) -> None:
        """
        Check if a new version of the app is available. Download it if there is
        """
        if not self._new_version_is_available():
            log.info("No newer version found")
            return
        log.info("New version found")
        self._download_and_replace()

    def _new_version_is_available(self) -> bool:
        """
        Check if a new version is available.

        Returns:
            bool: Whether or not a new version is available
        """
        bs3_version_parsed = [int(n) for n in self.latest_version.split(".")]
        bin_version_parsed = [int(n) for n in APP_VERSION.split(".")]
        if bs3_version_parsed[0] > bin_version_parsed[0]:
            log.info("New major version found")
            return True
        elif (
            bs3_version_parsed[0] == bin_version_parsed[0]
            and bs3_version_parsed[1] > bin_version_parsed[1]
        ):
            log.info("New minor version found")
            return True
        elif (
            bs3_version_parsed[0] == bin_version_parsed[0]
            and bs3_version_parsed[1] == bin_version_parsed[1]
            and bs3_version_parsed[2] > bin_version_parsed[2]
        ):
            log.info("New patch version found")
            return True
        return False

    def _get_versions_json(self) -> dict:
        """
        Fetch the versions.json and load it into a dictionnary.

        Returns:
            dict: versions.json loaded
        """
        self._clean_versions_files()
        versions_dict = {}
        r = get(
            "http://video-dl-binaries.s3.amazonaws.com/"
            f"{self.versions_archive_name}"
        )
        if r.status_code != 200:
            log.info(f"{self.versions_archive_name} doesn't exists")
            return versions_dict
        with open(self.versions_archive_name, "wb") as f:
            f.write(r.content)
        with ZipFile(self.versions_archive_name, "r") as zip_ref:
            zip_ref.extractall()
        with open(self.versions_json_name, "rb") as f:
            versions_dict = json.load(f)
        if versions_dict is None:
            log.info(f"{self.versions_json_name} doesn't exists")
        self._clean_versions_files()
        return versions_dict

    def _clean_versions_files(self) -> None:
        """
        Remove version's files
        """
        try:
            log.info("Removing existing versions files")
            remove(self.versions_json_name)
            remove(self.versions_archive_name)
        except FileNotFoundError:
            log.info("No versions files were found")

    def _download_and_replace(self) -> None:
        """
        Download the latest version and replace the current one.

        Raises:
            AssertionError: If the archive of the latest version isn't there
        """
        latest_archive_name = (
            f"{APP_NAME}-{self.platform}-{ARCHITECTURE}"
            f"-{self.latest_version}.zip"
        )
        log.info("Downloading...")
        try:
            self._download_latest_version(latest_archive_name)
        except ValueError:
            log.info("Update canceled")
            return
        log.info("Checking archive integrity...")
        if not self._archive_ok(latest_archive_name):
            try:
                remove(latest_archive_name)
            except FileNotFoundError:
                log.info(f"{latest_archive_name} not found")
            raise AssertionError
        log.info("Restarting...")
        self._replace_with_latest(latest_archive_name)

    def _download_latest_version(self, latest_archive_name: str) -> None:
        """
        Download the latest version

        Args:
            latest_archive_name (str): The name of the latest version's archive

        Raises:
            ValueError: If the download is canceled
        """
        uri = "http://video-dl-binaries.s3.amazonaws.com/"
        url = f"{uri}{latest_archive_name}"
        with get(url, stream=True) as r:
            total_size = int(r.headers.get("Content-Length"))
            with open(latest_archive_name, "wb") as f:
                for nth_chunk, chunk in enumerate(r.iter_content(8192)):
                    f.write(chunk)
                    self.update_progress_bar(nth_chunk, total_size)
                    if self.update_canceled:
                        raise ValueError
            self.update_prog_win.close()
            if r.status_code != 200:
                log.error("Couldn't retrieve the latest version")

    def _replace_with_latest(self, latest_archive_name: str) -> None:
        """
        Replace the current version with the latest one.

        Args:
            latest_archive_name (str): Latest version archive's name
        """
        if self.platform == "Windows":
            self._replace_on_windows(latest_archive_name)
        else:
            self._replace_on_unix(latest_archive_name)

    def _replace_on_windows(self, latest_archive_name: str) -> None:
        """
        Replace the current version with the latest one on Windows using a
        .bat file.

        Args:
            latest_archive_name (str): Latest version archive's name
        """
        tmp_folder = "tmp"
        bat_name = "updater.bat"
        with ZipFile(latest_archive_name, "r") as zip_ref:
            zip_ref.extractall(tmp_folder)
        # Batch waits 5s, move the update, runs it, deletes the archive and
        # deletes itself
        batch_script = f"""
        @echo off
        chcp 65001 >nul 2>&1
        PING 127.0.0.1 -n 5 -w 1000 > NUL
        ECHO Updating to latest version...
        MOVE /Y "{path.join(tmp_folder, self.app_bin_name)}" "{path.curdir}"
        ECHO Restarting...
        START "" "{self.app_bin_name}"
        RMDIR "tmp"
        DEL {latest_archive_name}
        DEL "%~f0"&exit
        """
        with io.open(bat_name, "w", encoding="utf-8") as bat:
            bat.write(batch_script)
        Popen(f'"{bat_name}"', shell=True)
        sys.exit(0)

    def _replace_on_unix(self, latest_archive_name: str) -> None:
        """
        Replace the current version with the latest one on Unix like systems

        Args:
            latest_archive_name (str): Name of the latest version's archive
        """
        tmp_folder = "tmp"
        rmtree(tmp_folder, ignore_errors=True)
        mkdir(tmp_folder)
        try:
            remove(self.app_bin_name)
        except OSError:
            pass
        os.system(f"unzip -q -o {latest_archive_name} -d {tmp_folder}")
        move(
            f"{path.join(tmp_folder, self.app_bin_name)}",
            f"{self.app_bin_name}",
        )
        rmtree(tmp_folder, ignore_errors=True)
        try:
            remove(latest_archive_name)
        except OSError:
            pass
        fullpath_bin = path.join(path.abspath(getcwd()), self.app_bin_name)
        os.system(f"open -a {fullpath_bin}")
        exit()

    def _archive_ok(self, latest_archive_name: str) -> bool:
        """
        Check the archive's size and SHA256.

        Args:
            latest_archive_name (str): Latest version archive's name

        Returns:
            bool: Whether or not the archive size and SHA256 match
        """
        latest_version = self.versions_dict[APP_NAME][self.platform][
            ARCHITECTURE
        ]["latest_version"]
        bin_infos = self.versions_dict[APP_NAME][self.platform][ARCHITECTURE][
            latest_version
        ]
        try:
            archive_name_json = bin_infos["archive_name"]
            archive_size_json = bin_infos["archive_size"]
            archive_hash_json = bin_infos["archive_hash"]
            archive_actual_size = path.getsize(latest_archive_name)
            archive_actual_hash = compute_sha256(latest_archive_name)
            if archive_name_json != latest_archive_name:
                log.info(
                    f"Mismatch archive name {archive_name_json} != "
                    f"{latest_archive_name}"
                )
                return False
            elif archive_size_json != archive_actual_size:
                log.info(
                    f"Mismatch archive name {archive_size_json} != "
                    f"{archive_actual_size}"
                )
                return False
            elif archive_hash_json != archive_actual_hash:
                log.info(
                    f"Mismatch archive hash {archive_hash_json} != "
                    f"{archive_actual_hash}"
                )
                return False
            else:
                log.info("Archive is ok")
                return True
        except KeyError as e:
            log.info(f"Key missing in {self.versions_json_name}: {e}")
            return False
        # match signature

    def update_progress_bar(
        self, chunks_downloaded: int, total_size: int
    ) -> None:
        """
        Handle the update's progress bar.

        Args:
            chunks_downloaded (int): Number of chunk downloaded
            total_size (int): File's total size of to download
        """
        event = None
        downloaded_bytes = chunks_downloaded * 8192
        cancel_button_str = get_text(GuiField.cancel_button)
        try:
            progress_percent = downloaded_bytes * 100 // total_size
        except ZeroDivisionError:
            progress_percent = 100
        now = datetime.now()
        delta_time = now - self.time_last_update
        average_speed = 0
        seconds_interval = 0.1
        if delta_time >= timedelta(milliseconds=seconds_interval * 1_000):
            event, _ = self.update_prog_win.read(timeout=20)
            if event == cancel_button_str:
                self.update_prog_win.close()
                self.update_canceled = True
            downloaded_in_interval = downloaded_bytes - self.size_last_update
            average_speed = downloaded_in_interval // seconds_interval
            self.time_last_update = now
            self.size_last_update = downloaded_bytes
            average_speed_str = Quantity(average_speed, "B/s").render(prec=2)
            self.update_prog_win["PROGINFOS1"].update(f"{progress_percent}%")
            self.update_prog_win["-PROG-"].update(progress_percent)
            self.update_prog_win["PROGINFOS2"].update(
                f"{get_text(GuiField.ff_speed)}: {average_speed_str}"
            )
