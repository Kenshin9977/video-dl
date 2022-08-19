import io
import json
import logging
import sys
from datetime import datetime, timedelta
from os import path, remove
from platform import system
from subprocess import Popen
from zipfile import ZipFile

from gen_new_version import (APP_NAME, APP_VERSION, VERSIONS_ARCHIVE_NAME,
                             VERSIONS_JSON_NAME, gen_archive_name,
                             get_name_for_platform)
from lang import GuiField, get_text
from quantiphy import Quantity
from requests import get
from utils.crypto_util import compute_sha256
from utils.gui_utils import create_progress_bar
from yt_dlp.utils import traverse_obj

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        self.platform = system()
        self.app_archive_name = gen_archive_name()
        self.app_bin_name = get_name_for_platform()
        self.versions_archive_name = VERSIONS_ARCHIVE_NAME
        self.versions_json_name = VERSIONS_JSON_NAME
        self.update_prog_win = create_progress_bar(
            get_text(GuiField.update), True
        )
        self.versions_dict = self._get_versions_json()
        self.latest_version = (
            traverse_obj(
                self.versions_dict, (APP_NAME, self.platform, "latest_version")
            )
            or APP_VERSION
        )
        self.update_canceled = False
        self.time_last_update = datetime.now()
        self.size_last_update = 0

    def update_app(self) -> None:
        if not self._new_version_is_available():
            log.info("No newer version found")
            return
        log.info("New version found")
        self._download_and_replace()

    def _new_version_is_available(self) -> bool:
        bs3_version_parsed = [int(n) for n in self.latest_version.split(".")]
        bin_version_parsed = [int(n) for n in APP_VERSION.split(".")]
        if bs3_version_parsed[0] < bin_version_parsed[0]:
            return False
        elif bs3_version_parsed[1] < bin_version_parsed[1]:
            return False
        return bs3_version_parsed[2] >= bin_version_parsed[2]

    def _get_versions_json(self) -> dict:
        self._clean_versions_files()
        versions_dict = None
        r = get(
            "http://video-dl-binaries.s3.amazonaws.com/"
            f"{self.versions_archive_name}"
        )
        if r.status_code != 200:
            log.info(f"{self.versions_archive_name} doesn't exists")
            return
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
        try:
            log.info("Removing existing versions files")
            remove(self.versions_json_name)
            remove(self.versions_archive_name)
        except FileNotFoundError:
            log.info("No versions files were found")

    def _download_and_replace(self) -> None:
        latest_archive_name = (
            f"{APP_NAME}-{self.platform}-{self.latest_version}.zip"
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

    def _download_latest_version(self, latest_archive_name) -> None:
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

    def _replace_with_latest(self, latest_archive_name) -> None:
        if self.platform == "Windows":
            self._replace_on_windows(latest_archive_name)
        else:
            print("The updater doesn't currently handle this platform")

    def _replace_on_windows(self, latest_archive_name):
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
        Popen(f'"{bat_name}"', shell=False)
        sys.exit(0)

    def _archive_ok(self, latest_archive_name) -> bool:
        latest_version = self.versions_dict[APP_NAME][self.platform][
            "latest_version"
        ]
        bin_infos = self.versions_dict[APP_NAME][self.platform][latest_version]
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

    def update_progress_bar(self, chunks_downloaded, total_size):
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
