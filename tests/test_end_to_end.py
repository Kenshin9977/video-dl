"""A real download, over the real network, through the real yt-dlp.

Everything else in this suite mocks the network. This does not, which is the point:
it is what gives an unattended yt-dlp bump the right to merge. It proves the version
Renovate proposes can still fetch a file, still run its ffmpeg postprocessor, and
still drive both progress bars through our two runtime patches.

Marked `network`, so it is excluded from the default run (see pyproject.toml) and
runs in the `download` CI job and the daily canary.
"""

import shutil
import sys
from unittest.mock import MagicMock

import pytest

for _name in [
    name for name, mod in list(sys.modules.items()) if name.startswith("yt_dlp") and isinstance(mod, MagicMock)
]:
    del sys.modules[_name]

from yt_dlp import YoutubeDL  # noqa: E402

from core import aria2c_progress, ytdlp_patch  # noqa: E402

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH"),
]

# A small, stable, direct http file. Deliberately not YouTube: YouTube blocks
# datacenter IPs often enough that gating a merge on it would train us to ignore a
# red CI. The YouTube run is a separate, informational CI step.
SAMPLE = "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4"


@pytest.fixture
def hooks():
    return {"download": [], "postprocess": []}


@pytest.fixture
def ydl_opts(tmp_path, hooks):
    ytdlp_patch.install()
    aria2c_progress.install()
    return {
        "quiet": True,
        "noprogress": True,
        "outtmpl": str(tmp_path / "%(title).40s.%(ext)s"),
        "progress_hooks": [hooks["download"].append],
        "postprocessor_hooks": [hooks["postprocess"].append],
    }


class TestRealDownload:
    def test_downloads_a_file_and_reports_progress(self, ydl_opts, hooks, tmp_path):
        with YoutubeDL(ydl_opts) as ydl:
            assert ydl.download([SAMPLE]) == 0

        assert list(tmp_path.iterdir()), "nothing was downloaded"
        assert any(h["status"] == "finished" for h in hooks["download"])

    def test_the_ffmpeg_postprocessor_reports_progress(self, ydl_opts, hooks, tmp_path):
        """Extracting audio makes yt-dlp run ffmpeg itself, which is what we patch."""
        ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]

        with YoutubeDL(ydl_opts) as ydl:
            assert ydl.download([SAMPLE]) == 0

        assert list(tmp_path.glob("*.mp3")), "ffmpeg did not produce the audio file"

        processing = [h for h in hooks["postprocess"] if h.get("processed_bytes", 0) > 0]
        assert processing, "yt-dlp ran ffmpeg but the progress patch reported nothing"
        assert processing[-1]["total_bytes"] > 0
