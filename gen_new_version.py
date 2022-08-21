import json
import logging
import os
from os.path import exists, getsize, join
from platform import machine, system
from re import match
from zipfile import ZipFile

import PyInstaller.__main__

from updater.bs3 import Bs3client
from utils.crypto_util import compute_sha256
from utils.sys_utils import get_system_architecture

log = logging.getLogger(__name__)
APP_NAME = "video-dl"
APP_VERSION = "0.10.2"
ASSETS = {"Windows": ["ffmpeg.exe", "ffprobe.exe"]}
VERSIONS_ARCHIVE_NAME = "versions.zip"
VERSIONS_JSON_NAME = "versions.json"
PLATFORM = system()
ARCHITECTURE = get_system_architecture()


def update():
    GenUpdate().gen_update()


class GenUpdate:
    def __init__(self):
        self.app_name = APP_NAME
        self.app_version = APP_VERSION
        self.platform = PLATFORM
        self.machine = machine()
        self.archive_name = gen_archive_name()
        self.bin_name = get_bin_ext_for_platform()
        self.s3client = Bs3client()
        self.versions_archive_name = VERSIONS_ARCHIVE_NAME
        self.versions_json_name = VERSIONS_JSON_NAME

    def gen_update(self):
        self._gen_archives()
        self._upload_archives()

    def _upload_archives(self):
        self.s3client.upload(filename=self.archive_name)
        self.s3client.upload(filename=self.versions_archive_name)

    def _gen_archives(self) -> None:
        self._gen_json_archive()
        self._gen_app_archive()

    def _gen_app_archive(self):
        self._gen_binary()
        zipObj = ZipFile(self.archive_name, "w")
        path2bin = join("dist", self.bin_name)
        if not exists(path2bin):
            log.error("Binary file wasn't found")
            raise FileNotFoundError
        zipObj.write(path2bin, arcname=self.bin_name)
        zipObj.close()

    def _gen_json_archive(self) -> None:
        versions_dict = self._gen_versions_json()
        zipObj = ZipFile(self.versions_archive_name, "w")
        with open(self.versions_json_name, "w") as outfile:
            json.dump(versions_dict, outfile)
        # signature_dict = {"signature": compute_signature(json_versions_path)}
        # with open("signature.json", 'w') as outfile:
        #     json.dump(signature_dict, outfile)
        if not exists(self.versions_json_name):
            log.error(f"{self.versions_json_name} file wasn't found")
            raise FileNotFoundError
        zipObj.write(self.versions_json_name)
        # zipObj.write("signature.json")
        zipObj.close()

    def _get_versions_json(self) -> dict:
        self._clean_versions_files()
        if not self.s3client.download(
            self.versions_archive_name, can_fail=True
        ):
            log.info(f"{self.versions_json_name} doesn't exists")
            return dict()
        with ZipFile(self.versions_archive_name, "r") as zip_ref:
            zip_ref.extractall()
        with open(self.versions_json_name) as f:
            versions_dict = json.load(f)
        self._clean_versions_files()
        if versions_dict is None:
            log.info(f"{self.versions_json_name} doesn't exists")
            raise FileNotFoundError
        return versions_dict

    def _gen_binary(self) -> None:
        log.info("Generating the binary file")
        PyInstaller.__main__.run(
            [
                f"{PLATFORM}-video-dl.spec"
            ]
        )

    def _check_version_number_validity(self, latest_version) -> bool:
        lv_re = match(
            r"(?P<major>\d+)\.(?P<minor>\d+)\." r"(?P<patch>\d+)",
            latest_version,
        )
        cv_re = match(
            r"(?P<major>\d+)\.(?P<minor>\d+)\." r"(?P<patch>\d+)",
            self.app_version,
        )
        if not cv_re or not lv_re:
            log.error("No versions infos found")
            return False
        if int(lv_re.group("major")) > int(cv_re.group("major")):
            log.error("Major version is lesser than the latest one")
            return False
        elif int(lv_re.group("major")) < int(cv_re.group("major")):
            log.info("Version number is valid: Generating new major version")
            return True
        elif int(lv_re.group("minor")) > int(cv_re.group("minor")):
            log.error("Minor version is lesser than the latest one")
            return False
        elif int(lv_re.group("minor")) < int(cv_re.group("minor")):
            log.info("Version number is valid: Generating new minor version")
            return True
        elif int(lv_re.group("patch")) >= int(cv_re.group("patch")):
            log.error("Patch version is lesser or equal to the latest one")
            return False
        else:
            log.info("Version number is valid: Generating new patch version")
            return True

    def _clean_versions_files(self) -> None:
        try:
            log.info("Removing existing versions files")
            os.remove(self.versions_json_name)
            os.remove(self.versions_archive_name)
        except FileNotFoundError:
            log.info("No versions files were found")

    def _gen_versions_json(self) -> dict:
        dict_versions = self._get_versions_json()
        try:
            latest_version = dict_versions[self.app_name][self.platform][
                ARCHITECTURE
            ]["latest_version"]
            if not self._check_version_number_validity(latest_version):
                log.error("Version number isn't valid")
                raise ValueError
        except KeyError:
            log.info("No latest_version key found")
            raise KeyError
        dict_versions.update(
            {
                self.app_name: {
                    self.platform: {
                        ARCHITECTURE: {
                            "latest_version": self.app_version,
                            self.app_version: {
                                "archive_name": self.archive_name,
                                "archive_size": getsize(self.archive_name),
                                "archive_hash": compute_sha256(
                                    self.archive_name
                                ),
                            },
                        }
                    },
                },
            }
        )
        return dict_versions


def get_bin_ext_for_platform() -> str:
    ext = None
    if PLATFORM == "Windows":
        ext = ".exe"
    elif PLATFORM == "Linux":
        ext = "_amd64.deb"
    elif PLATFORM == "Darwin":
        ext = ".dmg"
    if ext is None:
        log.error("Platform isn't supported")
        raise RuntimeError
    return f"{APP_NAME}{ext}"


def gen_archive_name() -> str:
    correct_format = match(
        r"(?P<major>\d+)\.(?P<minor>\d+)\." r"(?P<patch>\d+)", APP_VERSION
    )
    if not correct_format:
        log.error("Version number isn't formatted correctly")
        raise ValueError
    return f"{APP_NAME}-{PLATFORM}-{ARCHITECTURE}-{APP_VERSION}.zip"


if __name__ == "__main__":
    update()
