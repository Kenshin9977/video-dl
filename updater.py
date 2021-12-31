import logging
import json
import os

from os import remove, path, unlink
from bs3 import Bs3client
from gen_new_version import APP_VERSION, APP_NAME, VERSIONS_ARCHIVE_NAME, VERSIONS_JSON_NAME, gen_archive_name, get_name_for_platform
from platform import system
from zipfile import ZipFile
from util import compute_sha256

log = logging.getLogger(__name__)


class Updater:
    def __init__(self):
        self.platform = system()
        self.app_archive_name = gen_archive_name()
        self.versions_archive_name = VERSIONS_ARCHIVE_NAME
        self.versions_json_name = VERSIONS_JSON_NAME
        self.versions_dict = None
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
        return self.versions_dict[APP_NAME][self.platform]["latest_version"] != APP_VERSION

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
        self.s3.download(self.app_archive_name)
        if not self._archive_ok():
            try:
                remove(self.app_archive_name)
            except FileNotFoundError:
                log.info(f"{self.app_archive_name} not found")
        unlink(get_name_for_platform())
        with ZipFile(self.app_archive_name, 'r') as zip_ref:
            zip_ref.extractall()

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
