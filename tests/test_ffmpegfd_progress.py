import inspect
import shutil
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

for _name in [
    name for name, mod in list(sys.modules.items()) if name.startswith("yt_dlp") and isinstance(mod, MagicMock)
]:
    del sys.modules[_name]

from yt_dlp import YoutubeDL  # noqa: E402
from yt_dlp.downloader import external as external_fd  # noqa: E402
from yt_dlp.downloader.external import FFmpegFD  # noqa: E402

from core import ffmpegfd_progress  # noqa: E402


class TestSeams:
    """Guard the yt-dlp internals core/ffmpegfd_progress.py reaches into."""

    def test_ffmpeg_is_still_what_downloads_a_trimmed_video(self):
        """The whole reason this patch exists: trimming hands the download to ffmpeg."""
        source = inspect.getsource(external_fd)
        assert "class FFmpegFD" in source

        from yt_dlp.downloader import _get_suitable_downloader

        selector = inspect.getsource(_get_suitable_downloader)
        assert "section_start" in selector and "FFmpegFD" in selector, (
            "yt-dlp no longer routes trimmed downloads through ffmpeg"
        )

    def test_call_downloader_still_has_the_signature_we_wrap(self):
        params = inspect.signature(FFmpegFD._call_downloader).parameters
        assert list(params) == ["self", "tmpfilename", "info_dict"]

    def test_it_still_runs_ffmpeg_through_the_module_popen(self):
        source = inspect.getsource(FFmpegFD._call_downloader)
        assert "Popen(" in source, "FFmpegFD no longer runs ffmpeg through Popen"
        assert inspect.isclass(external_fd.Popen)


class TestInstall:
    def test_replaces_the_seams_and_is_idempotent(self):
        assert ffmpegfd_progress.install()
        patched_call = FFmpegFD._call_downloader
        patched_popen = external_fd.Popen

        assert ffmpegfd_progress.install()

        assert FFmpegFD._call_downloader is patched_call
        assert external_fd.Popen is patched_popen
        assert ffmpegfd_progress._ORIGINAL_POPEN is not None
        assert issubclass(external_fd.Popen, ffmpegfd_progress._ORIGINAL_POPEN)

    def test_gives_up_quietly_when_a_seam_is_missing(self, monkeypatch, caplog):
        monkeypatch.setattr(ffmpegfd_progress, "_installed", False)
        monkeypatch.delattr(external_fd, "Popen")

        assert ffmpegfd_progress.install() is False
        assert not ffmpegfd_progress._installed
        assert "yt-dlp has moved" in caplog.text

    def test_still_reports_when_the_duration_is_unknown(self):
        """A direct file often has no duration, and the bar used to sit at zero for it.

        It does not need one: ffmpeg is the downloader here, so the bytes it writes
        are the bytes that came down the wire, and it counts those itself.
        """
        context = ffmpegfd_progress._Context(MagicMock(), {"filesize": 1000})
        reporter, path = ffmpegfd_progress._prepare(context, ["ffmpeg", "-i", "in.mp4"])

        assert context.duration == 0
        assert reporter is not None
        assert path is not None

    def test_leaves_every_other_external_downloader_alone(self):
        """The stand-in only touches an ffmpeg run. aria2c, wget and curl go through it too."""
        ffmpegfd_progress.install()
        ffmpegfd_progress._current.context = None

        process = external_fd.Popen([sys.executable, "-c", "pass"])
        process.wait()

        assert process.args == [sys.executable, "-c", "pass"], "the args were touched outside an FFmpegFD run"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
class TestAgainstRealFfmpeg:
    def test_a_real_ffmpeg_download_reports_progress(self, tmp_path):
        """Drive the real FFmpegFD, on a real file, and watch the download bar fill."""
        source = tmp_path / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15", str(source)],
            check=True,
            capture_output=True,
        )

        ffmpegfd_progress.install()

        reports = []
        with YoutubeDL({"quiet": True, "noprogress": True}) as ydl:
            downloader = FFmpegFD(ydl, {})
            downloader.add_progress_hook(reports.append)
            info_dict = {
                # A local path, not a file:// URI: ffmpeg on Windows will not open one.
                "url": str(source),
                "protocol": "https",
                "ext": "mp4",
                "duration": 3,
                "filesize": source.stat().st_size,
                "_filename": str(tmp_path / "out.mp4"),
            }
            assert downloader._call_downloader(str(tmp_path / "out.mp4"), info_dict) == 0

        assert (tmp_path / "out.mp4").is_file()

        downloading = [r for r in reports if r.get("downloaded_bytes", 0) > 0]
        assert downloading, "ffmpeg downloaded the file but the bar never moved"
        assert downloading[-1]["status"] == "downloading"
        assert downloading[-1]["total_bytes"] > 0
