import shutil
import subprocess
import sys
import textwrap

import pytest

from core.ffmpeg_progress import (
    FFmpegProgressTracker,
    bitrate_to_bits_per_second,
    duration_to_process,
    ffmpeg_time_to_seconds,
)

# A stand in for ffmpeg: writes the same progress blocks to stdout, some noise to
# stderr, and exits. Lets the tracker be tested for real, as a subprocess, on a
# machine with no ffmpeg.
FAKE_FFMPEG = textwrap.dedent(
    """
    import sys
    blocks, duration = int(sys.argv[1]), float(sys.argv[2])
    for i in range(1, blocks + 1):
        out_time = duration * i / blocks
        sys.stderr.write(f"frame {i} encoded\\n")
        sys.stdout.write(
            "frame= 100\\n"
            "fps= 25\\n"
            "stream_0_0_q= 28.0\\n"
            "bitrate= 1500.0kbits/s\\n"
            "total_size= 999\\n"
            f"out_time_us= {int(out_time * 1_000_000)}\\n"
            f"out_time_ms= {int(out_time * 1_000_000)}\\n"
            f"out_time= {out_time}\\n"
            "dup_frames= 0\\n"
            "drop_frames= 0\\n"
            "speed= 2.0x\\n"
            f"progress= {'end' if i == blocks else 'continue'}\\n"
        )
        sys.stdout.flush()
    sys.exit(int(sys.argv[3]))
    """
)


def fake_ffmpeg_args(blocks: int, duration: float, returncode: int = 0) -> list[str]:
    return [sys.executable, "-c", FAKE_FFMPEG, str(blocks), str(duration), str(returncode)]


class TestFfmpegTimeToSeconds:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("42", 42),
            ("1:30", 90),
            ("1:00:00", 3600),
            ("0:0:1.5", 1.5),
            ("500ms", 0.5),
            ("250000us", 0.25),
            ("12s", 12),
            ("garbage", 0),
        ],
    )
    def test_parses_every_format_ffmpeg_accepts(self, value, expected):
        assert ffmpeg_time_to_seconds(value) == expected


class TestBitrate:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1500kbits/s", 1_500_000),
            ("1.5mbits/s", 1_500_000),
            ("128bits/s", 128),
            ("2gbits/s", 2_000_000_000),
            ("N/A", 0),
        ],
    )
    def test_parses_bitrates(self, value, expected):
        assert bitrate_to_bits_per_second(value) == expected


class TestDurationToProcess:
    def test_whole_file_without_seek_flags(self):
        assert duration_to_process(["-i", "in.mp4", "out.mp4"], 120) == 120

    def test_trimmed_range(self):
        assert duration_to_process(["-ss", "60", "-to", "90", "-i", "in.mp4", "out.mp4"], 120) == 30

    def test_explicit_duration_wins(self):
        assert duration_to_process(["-ss", "10", "-t", "5", "-i", "in.mp4", "out.mp4"], 120) == 5

    def test_from_end(self):
        assert duration_to_process(["-sseof", "20", "-i", "in.mp4", "out.mp4"], 120) == 20

    def test_inline_value_form(self):
        assert duration_to_process(["-ss=60", "-to=90", "-i", "in.mp4", "out.mp4"], 120) == 30

    def test_no_duration_means_nothing_to_measure(self):
        assert duration_to_process(["-i", "in.mp4"], 0) == 0

    def test_negative_range_is_clamped(self):
        assert duration_to_process(["-ss", "90", "-to", "60", "-i", "in.mp4"], 120) == 0


class TestFFmpegProgressTracker:
    def test_reports_progress_up_to_the_total(self):
        reports = []
        tracker = FFmpegProgressTracker(
            fake_ffmpeg_args(blocks=4, duration=10),
            reports.append,
            duration=10,
            total_bytes=1000,
            filename="out.mp4",
        )
        _, _, returncode = tracker.run()

        assert returncode == 0
        progressed = [r for r in reports if r["processed_bytes"] > 0]
        assert progressed, "the tracker never reported any progress"
        assert [r["processed_bytes"] for r in progressed] == sorted(r["processed_bytes"] for r in progressed)
        assert progressed[-1]["processed_bytes"] == 1000
        assert progressed[-1]["total_bytes"] == 1000
        assert progressed[-1]["status"] == "processing"
        assert progressed[-1]["filename"] == "out.mp4"
        assert progressed[-1]["speed"] == 1_500_000

    def test_scales_the_total_to_a_trimmed_range(self):
        reports = []
        tracker = FFmpegProgressTracker(
            [*fake_ffmpeg_args(blocks=2, duration=5), "-ss", "0", "-t", "5"],
            reports.append,
            duration=10,
            total_bytes=1000,
        )
        tracker.run()

        # Half the media is being processed, so the output is worth half the bytes.
        assert reports[-1]["total_bytes"] == 500

    def test_eta_counts_down(self):
        reports = []
        tracker = FFmpegProgressTracker(fake_ffmpeg_args(blocks=4, duration=100), reports.append, duration=100)
        tracker.run()

        etas = [r["eta"] for r in reports if r.get("eta") is not None]
        assert etas == sorted(etas, reverse=True)
        assert etas[-1] == 0

    def test_reports_nothing_without_a_duration_but_still_runs(self):
        reports = []
        tracker = FFmpegProgressTracker(fake_ffmpeg_args(blocks=2, duration=10), reports.append, duration=0)
        _, _, returncode = tracker.run()

        assert returncode == 0
        assert all(r["processed_bytes"] == 0 for r in reports)

    def test_surfaces_the_return_code_and_stderr_of_a_failed_run(self):
        tracker = FFmpegProgressTracker(
            fake_ffmpeg_args(blocks=1, duration=10, returncode=1),
            lambda status: None,
            duration=10,
        )
        _, stderr, returncode = tracker.run()

        assert returncode == 1
        assert "frame 1 encoded" in stderr


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not on PATH")
class TestAgainstRealFfmpeg:
    def test_tracks_a_real_transcode(self, tmp_path):
        source = tmp_path / "source.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15", str(source)],
            check=True,
            capture_output=True,
        )

        output = tmp_path / "out.mp4"
        reports = []
        tracker = FFmpegProgressTracker(
            ["ffmpeg", "-y", "-i", str(source), "-c:v", "libx264", "-preset", "ultrafast", str(output)],
            reports.append,
            duration=3,
            total_bytes=source.stat().st_size,
            filename=str(output),
        )
        _, stderr, returncode = tracker.run()

        assert returncode == 0, stderr
        assert output.is_file()
        assert any(r["processed_bytes"] > 0 for r in reports), "real ffmpeg produced no progress"
