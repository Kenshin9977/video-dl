import sys
from unittest.mock import MagicMock
from zipfile import ZipFile

import pytest

sys.modules.setdefault("flet", MagicMock())

from utils.ffmpeg_install import extract_ffmpeg  # noqa: E402

ARCHIVE_ROOT = "ffmpeg-master-latest-win64-gpl-shared"


def _build_archive(tmp_path, names):
    """Write a zip mimicking the layout of a real FFmpeg-Builds release asset."""
    zip_path = tmp_path / "ffmpeg.zip"
    with ZipFile(zip_path, "w") as archive:
        for name in names:
            archive.writestr(name, b"binary")
    return str(zip_path)


class TestExtractFfmpeg:
    def test_flattens_nested_bin_directory(self, tmp_path):
        zip_path = _build_archive(
            tmp_path,
            [
                f"{ARCHIVE_ROOT}/bin/ffmpeg.exe",
                f"{ARCHIVE_ROOT}/bin/ffprobe.exe",
                f"{ARCHIVE_ROOT}/bin/avcodec-62.dll",
                f"{ARCHIVE_ROOT}/doc/ffmpeg.html",
                f"{ARCHIVE_ROOT}/lib/avcodec.lib",
            ],
        )
        target = tmp_path / "install"
        target.mkdir()

        extract_ffmpeg(zip_path, str(target))

        assert (target / "ffmpeg.exe").is_file()
        assert (target / "ffprobe.exe").is_file()
        assert (target / "avcodec-62.dll").is_file()

    def test_ignores_everything_outside_bin(self, tmp_path):
        zip_path = _build_archive(
            tmp_path,
            [
                f"{ARCHIVE_ROOT}/bin/ffmpeg.exe",
                f"{ARCHIVE_ROOT}/bin/ffprobe.exe",
                f"{ARCHIVE_ROOT}/doc/ffmpeg.html",
                f"{ARCHIVE_ROOT}/LICENSE.txt",
            ],
        )
        target = tmp_path / "install"
        target.mkdir()

        extract_ffmpeg(zip_path, str(target))

        assert sorted(p.name for p in target.iterdir()) == ["ffmpeg.exe", "ffprobe.exe"]

    def test_path_traversal_member_lands_inside_target(self, tmp_path):
        zip_path = _build_archive(
            tmp_path,
            [
                f"{ARCHIVE_ROOT}/bin/ffmpeg.exe",
                f"{ARCHIVE_ROOT}/bin/ffprobe.exe",
                "../../bin/evil.dll",
            ],
        )
        target = tmp_path / "install"
        target.mkdir()

        extract_ffmpeg(zip_path, str(target))

        assert (target / "evil.dll").is_file()
        assert not (tmp_path.parent / "evil.dll").exists()

    def test_raises_when_the_archive_has_no_ffmpeg(self, tmp_path):
        zip_path = _build_archive(tmp_path, [f"{ARCHIVE_ROOT}/bin/ffplay.exe"])
        target = tmp_path / "install"
        target.mkdir()

        with pytest.raises(FileNotFoundError, match="ffmpeg.exe, ffprobe.exe"):
            extract_ffmpeg(zip_path, str(target))
