import inspect
import shutil
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

# tests/test_download.py replaces the whole yt_dlp package tree in sys.modules with
# MagicMocks and never puts it back, so any module imported after it gets the mock.
# This file is the one place that must see the real yt-dlp: it exists to check our
# assumptions against it. Drop the mocks before importing.
for _name in [
    name for name, mod in list(sys.modules.items()) if name.startswith("yt_dlp") and isinstance(mod, MagicMock)
]:
    del sys.modules[_name]

from yt_dlp import YoutubeDL  # noqa: E402
from yt_dlp.postprocessor import ffmpeg as ffmpeg_pp  # noqa: E402
from yt_dlp.postprocessor.common import PostProcessor  # noqa: E402
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor  # noqa: E402

from core import ytdlp_patch  # noqa: E402


class TestSeams:
    """Guard the yt-dlp internals core/ytdlp_patch.py reaches into.

    These are the load-bearing assumptions. When a yt-dlp bump moves one of them,
    this fails in CI, which is the whole point: the alternative was discovering it
    in a release, or maintaining a fork of yt-dlp to avoid the question.
    """

    def test_real_run_ffmpeg_still_has_the_signature_we_wrap(self):
        params = inspect.signature(FFmpegPostProcessor.real_run_ffmpeg).parameters
        assert list(params) == ["self", "input_path_opts", "output_path_opts", "expected_retcodes"]
        assert params["expected_retcodes"].kind is inspect.Parameter.KEYWORD_ONLY

    def test_real_run_ffmpeg_still_runs_its_command_through_the_module_popen(self):
        source = inspect.getsource(ffmpeg_pp.FFmpegPostProcessor.real_run_ffmpeg)
        assert "Popen.run(" in source, "real_run_ffmpeg no longer runs ffmpeg through Popen.run"
        assert inspect.isclass(ffmpeg_pp.Popen)
        assert isinstance(inspect.getattr_static(ffmpeg_pp.Popen, "run"), classmethod)

    def test_hook_progress_still_reaches_postprocessor_hooks(self):
        params = inspect.signature(PostProcessor._hook_progress).parameters
        assert list(params) == ["self", "status", "info_dict"]

    def test_metadata_object_still_probes_the_duration(self):
        assert callable(FFmpegPostProcessor.get_metadata_object)


class TestInstall:
    def test_replaces_the_seams_and_is_idempotent(self):
        ytdlp_patch.install()
        patched_run = FFmpegPostProcessor.real_run_ffmpeg
        patched_popen = ffmpeg_pp.Popen

        ytdlp_patch.install()

        assert FFmpegPostProcessor.real_run_ffmpeg is patched_run
        assert ffmpeg_pp.Popen is patched_popen
        assert ytdlp_patch._ORIGINAL_POPEN is not None
        assert issubclass(ffmpeg_pp.Popen, ytdlp_patch._ORIGINAL_POPEN)

    def test_gives_up_quietly_when_a_seam_is_missing(self, monkeypatch, caplog):
        """A yt-dlp that moved must cost the progress bar, never the download."""
        monkeypatch.setattr(ytdlp_patch, "_installed", False)
        monkeypatch.delattr(ffmpeg_pp, "Popen")

        ytdlp_patch.install()

        assert not ytdlp_patch._installed
        assert "yt-dlp has moved" in caplog.text


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
class TestAgainstRealYtDlp:
    def test_a_real_postprocessor_reports_progress(self, tmp_path):
        """The end of the fork, proven: yt-dlp's own ffmpeg run drives our bar."""
        source = tmp_path / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15", str(source)],
            check=True,
            capture_output=True,
        )

        ytdlp_patch.install()

        reports = []
        with YoutubeDL({"quiet": True}) as ydl:
            pp = FFmpegPostProcessor(ydl)
            pp.add_progress_hook(reports.append)
            pp.run_ffmpeg(str(source), str(tmp_path / "out.mp4"), ["-c:v", "libx264", "-preset", "ultrafast"])

        progressed = [r for r in reports if r.get("processed_bytes", 0) > 0]
        assert progressed, "yt-dlp ran ffmpeg but reported no progress"
        assert progressed[-1]["status"] == "processing"
        assert progressed[-1]["total_bytes"] > 0
        # yt-dlp stamps the reports itself, which is the proof they went through
        # its own hook plumbing rather than straight from us to the test.
        assert progressed[-1]["postprocessor"]
        assert "info_dict" in progressed[-1]

    def test_ffprobe_calls_are_left_alone(self, tmp_path):
        """Only the ffmpeg run is intercepted. The probe that measures it must not be."""
        source = tmp_path / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=10", str(source)],
            check=True,
            capture_output=True,
        )

        ytdlp_patch.install()

        with YoutubeDL({"quiet": True}) as ydl:
            metadata = FFmpegPostProcessor(ydl).get_metadata_object(str(source))

        assert float(metadata["format"]["duration"]) == pytest.approx(1, abs=0.5)
