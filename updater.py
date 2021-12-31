import io
import logging
import json
import sys

from bs3 import Bs3client
from gen_new_version import APP_VERSION, APP_NAME, VERSIONS_ARCHIVE_NAME, VERSIONS_JSON_NAME, gen_archive_name, get_name_for_platform
from os import remove, path
from platform import system
from subprocess import Popen
from util import compute_sha256
from zipfile import ZipFile

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        self.platform = system()
        self.app_archive_name = gen_archive_name()
        self.app_bin_name = get_name_for_platform()
        self.versions_archive_name = VERSIONS_ARCHIVE_NAME
        self.versions_json_name = VERSIONS_JSON_NAME
        self.versions_dict = None
        self.latest_version = None
        self.s3 = Bs3client(
            aws_id="AKIAQART2O4ARFYTSSRB",
            aws_skey="Xbm2SI3Nwbtk+02ZEl2M5mmxXKxZsaUmDCcDIV+R"
        )

    def update_app(self) -> None:
        if not self._new_version_available():
            log.info("No newer version found")
            return
        self._download_and_replace()

    def _new_version_available(self) -> bool:
        self._get_versions_json()
        if self.versions_dict is None:
            log.info("No versions file found")
            return False
        self.latest_version = self.versions_dict[APP_NAME][self.platform]["latest_version"]
        return self.latest_version != APP_VERSION

    def _get_versions_json(self) -> None:
        self._clean_versions_files()
        if not self.s3.download(self.versions_archive_name, can_fail=True):
            log.info(f"{self.versions_archive_name} doesn't exists")
            return
        with ZipFile(self.versions_archive_name, 'r') as zip_ref:
            zip_ref.extractall()
        with open(self.versions_json_name) as f:
            self.versions_dict = json.load(f)
        if self.versions_dict is None:
            log.info(f"{self.versions_json_name} doesn't exists")
        self._clean_versions_files()

    def _clean_versions_files(self) -> None:
        try:
            remove(self.versions_json_name)
            remove(self.versions_archive_name)
            log.info("Cleaned folder of existing versions files")
        except FileNotFoundError:
            log.info("versions files not found")

    def _download_and_replace(self) -> None:
        latest_archive_name = f"{APP_NAME}-{self.platform}-{self.latest_version}.zip"
        self._download_latest_version(latest_archive_name)
        self._replace_with_latest(latest_archive_name)
        if not self._archive_ok():
            try:
                remove(latest_archive_name)
            except FileNotFoundError:
                log.info(f"{latest_archive_name} not found")

    def _download_latest_version(self, latest_archive_name) -> None:
        self.s3.download(latest_archive_name)

    def _replace_with_latest(self, latest_archive_name) -> None:
        if self.platform == "Windows":
            self._replace_on_windows(latest_archive_name)
        else:
            print("The updater doesn't currently handle this platform")

    def _replace_on_windows(self, latest_archive_name):
        tmp_folder = "tmp"
        bat_name = "updater.bat"
        with ZipFile(latest_archive_name, 'r') as zip_ref:
            zip_ref.extractall(tmp_folder)
        # Batch waits 5s, move the update then run it
        batch_content = f"""
        @echo off
        chcp 65001
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
            bat.write(batch_content)
        Popen(f'"{bat_name}"')
        sys.exit(0)

    def _archive_ok(self) -> bool:
        latest_version = self.versions_dict[APP_NAME][self.platform]["latest_version"]
        bin_infos = self.versions_dict[APP_NAME][self.platform][latest_version]
        try:
            archive_name_json = bin_infos["archive_name"]
            archive_size_json = bin_infos["archive_size"]
            archive_hash_json = bin_infos["archive_hash"]
            archive_actual_size = path.getsize(self.app_archive_name)
            archive_actual_hash = compute_sha256(self.app_archive_name)
            if archive_name_json != self.app_archive_name:
                log.info(f"Mismatch archive name {archive_name_json} != {self.app_archive_name}")
                return False
            elif archive_size_json != archive_actual_size:
                log.info(f"Mismatch archive name {archive_size_json} != {archive_actual_size}")
                return False
            elif archive_hash_json != archive_actual_hash:
                log.info(f"Mismatch archive hash {archive_hash_json} != {archive_actual_hash}")
                return False
            else:
                log.info(f"Archive is ok")
                return True
        except KeyError as e:
            log.info(f"Key missing in {self.versions_json_name}: {e}")
            return False
        # match signature
