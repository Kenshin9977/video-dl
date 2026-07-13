"""Run an ffmpeg command and report its progress.

ffmpeg writes a machine readable progress report to the pipe named by
``-progress``, one ``key=value`` per line, ending each block with ``progress=``.
This parses that stream and calls back with the same status shape the GUI's
process bar consumes: ``processed_bytes`` out of ``total_bytes``.

ffmpeg reports how far it has got in *time*, never in bytes, so the byte counts
here are that time ratio applied to the input size. They are honest enough for a
progress bar and are not to be trusted for anything else.

This used to live in a fork of yt-dlp. It never needed to: it takes an argument
list, runs a subprocess and parses stdout. See core/ytdlp_patch.py for the part
that teaches yt-dlp's own postprocessors to report through it.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
import time
from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread

logger = logging.getLogger("videodl")

ProgressHook = Callable[[dict], None]

# One report block, as written by `-progress pipe:1`. The frame/fps/quality lines
# only appear when a video stream is being encoded.
_PROGRESS_BLOCK = re.compile(
    r"""(?x)
    (?:
        frame=\s*(?P<frame>\S+)\n
        fps=\s*(?P<fps>\S+)\n
        (?:stream_\d+_\d+_q=\s*\S+\n)+
    )?
    bitrate=\s*(?P<bitrate>\S+)\n
    total_size=\s*(?P<total_size>\S+)\n
    out_time_us=\s*(?P<out_time_us>\S+)\n
    out_time_ms=\s*(?P<out_time_ms>\S+)\n
    out_time=\s*(?P<out_time>\S+)\n
    dup_frames=\s*(?P<dup_frames>\S+)\n
    drop_frames=\s*(?P<drop_frames>\S+)\n
    speed=\s*(?P<speed>\S+)\n
    progress=\s*(?P<progress>\S+)
    """
)

_TIME_WITH_UNIT = re.compile(r"(?P<value>\d+)(?P<unit>[mu]?s)")
# [[HH:]MM:]SS, so `1:30` is a minute and a half, not an hour and thirty seconds.
# The hours group only exists when a minutes group follows it.
_TIME_HMS = re.compile(r"(?:(?:(?P<hours>\d+):)?(?P<minutes>\d+):)?(?P<seconds>\d+)(\.(?P<fraction>\d+))?")
_BITRATE = re.compile(r"(?P<value>\d+)(\.(?P<fraction>\d+))?(?P<prefix>[gmk])?bits/s")

_SEEK_FLAGS = ("-ss", "-sseof", "-to", "-t")


def ffmpeg_time_to_seconds(value: str) -> float:
    """Parse any of the time formats ffmpeg accepts: `12`, `1:02:03.5`, `500ms`, `900us`."""
    with_unit = _TIME_WITH_UNIT.fullmatch(value)
    if with_unit:
        seconds = float(with_unit.group("value"))
        unit = with_unit.group("unit")
        if unit == "ms":
            return seconds / 1_000
        if unit == "us":
            return seconds / 1_000_000
        return seconds

    hms = _TIME_HMS.fullmatch(value)
    if not hms:
        return 0.0

    seconds = float(hms.group("seconds"))
    if hms.group("hours"):
        seconds += 3600 * int(hms.group("hours"))
    if hms.group("minutes"):
        seconds += 60 * int(hms.group("minutes"))
    if hms.group("fraction"):
        fraction = hms.group("fraction")
        seconds += int(fraction) / (10 ** len(fraction))
    return seconds


def bitrate_to_bits_per_second(value: str) -> float:
    """Parse ffmpeg's `bitrate=` field, e.g. `1234.5kbits/s`. Returns 0 when ffmpeg reports `N/A`."""
    match = _BITRATE.fullmatch(value)
    if not match:
        return 0.0

    bitrate = float(match.group("value"))
    if match.group("fraction"):
        fraction = match.group("fraction")
        bitrate += int(fraction) / (10 ** len(fraction))

    multiplier = {"g": 1_000_000_000, "m": 1_000_000, "k": 1_000}.get(match.group("prefix") or "", 1)
    return bitrate * multiplier


def to_int(value: str | None) -> int:
    """ffmpeg writes `N/A` rather than a number whenever it has nothing to report yet."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def microseconds_to_seconds(value: str | None) -> int:
    """Read ffmpeg's `out_time_us=` field.

    ffmpeg writes `N/A` there, not a number, until it has something to report: at
    the start of a run, and for the whole of some audio only ones. Reading it as an
    integer took the whole download down with a ValueError.
    """
    try:
        return int(value) // 1_000_000  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def duration_to_process(args: list[str], duration: float) -> float:
    """How much of the media the command will actually touch, given its seek flags.

    A command that trims with `-ss 60 -to 90` processes 30 seconds, not the whole
    file, and its progress must be measured against those 30 seconds.
    """
    if not duration:
        return 0.0

    start, end, explicit = 0.0, duration, None
    for i, arg in enumerate(args[:-1]):
        flag, _, inline_value = arg.partition("=")
        if flag not in _SEEK_FLAGS:
            continue
        timestamp = ffmpeg_time_to_seconds(inline_value or args[i + 1])
        if flag == "-ss":
            start = timestamp
        elif flag == "-sseof":
            start = end - timestamp
        elif flag == "-to":
            end = timestamp
        elif flag == "-t":
            explicit = timestamp

    processed = explicit if explicit is not None else end - start
    return processed if processed >= 0 else 0.0


class FFmpegProgressReporter:
    """Turn ffmpeg's progress reports into status dicts, wherever they come from.

    Feed it whatever ffmpeg has written so far, as many times as you like. It keeps
    the leftovers, and calls `on_progress` once per complete report block.

    `duration` and `total_bytes` describe the *input*: the media duration in seconds
    and its size in bytes. Without a duration there is no ratio to compute, so it
    reports nothing rather than reporting nonsense.

    ffmpeg reports how far it has got in *time*, never in bytes, so the byte counts
    are that time ratio applied to the input size. Honest enough for a bar.

    The byte count goes out under `bytes_key`, because the GUI reads a different key
    depending on which bar it is filling: `downloaded_bytes` while ffmpeg is doing
    the downloading, `processed_bytes` while it is doing the encoding.
    """

    def __init__(
        self,
        on_progress: ProgressHook,
        *,
        args: list[str],
        duration: float = 0,
        total_bytes: int = 0,
        filename: str = "",
        bytes_key: str = "processed_bytes",
        status: str = "processing",
        bytes_from_output: bool = False,
    ) -> None:
        self._on_progress = on_progress
        self._bytes_key = bytes_key
        self._bytes_from_output = bytes_from_output
        self._block = ""
        self._started_at = time.time()

        self._duration = duration_to_process(args, duration)
        # The output covers only the part of the input being processed.
        self._total_bytes = int(total_bytes * self._duration / duration) if duration else 0
        self._status: dict = {
            "filename": filename,
            "status": status,
            "elapsed": 0,
            bytes_key: 0,
            "total_bytes": self._total_bytes,
        }

    @property
    def reports_anything(self) -> bool:
        """False when there is nothing we could report, so why even ask ffmpeg for it."""
        return bool(self._duration or self._bytes_from_output)

    def feed(self, text: str) -> None:
        """Hand it more of ffmpeg's progress output."""
        self._block += text
        while True:
            report = _PROGRESS_BLOCK.match(self._block)
            if not report:
                return
            self._block = self._block[report.end() :].lstrip("\n")
            self._emit(report)

    def tick(self) -> None:
        """Refresh `elapsed` even when ffmpeg has said nothing new."""
        self._status["elapsed"] = time.time() - self._started_at
        self._on_progress(self._status.copy())

    def _emit(self, report: re.Match) -> None:
        out_time = microseconds_to_seconds(report.group("out_time_us"))

        if self._bytes_from_output:
            # ffmpeg is downloading, so the bytes it has written are the bytes that
            # came down the wire. That is a real count, and it needs no duration:
            # a direct file often has none, and the bar would sit at zero.
            done = to_int(report.group("total_size"))
        else:
            # ffmpeg is encoding, and then total_size is the size of a file that is
            # still being written: it can overshoot and push the bar past 100%. How
            # far into the media it has got is the honest measure.
            done = int(out_time / self._duration * self._total_bytes) if self._duration else 0

        self._status.update(
            {
                self._bytes_key: done,
                "total_bytes": self._total_bytes or None,
                "speed": bitrate_to_bits_per_second(report.group("bitrate")) or None,
                "eta": self._eta(report.group("speed"), out_time),
                "elapsed": time.time() - self._started_at,
            }
        )
        self._on_progress(self._status.copy())

    def _eta(self, speed_field: str, out_time: int) -> float | None:
        """`speed=` is a multiple of realtime, e.g. `2.5x`, so the remaining media time over it."""
        if not self._duration:
            return None
        try:
            speed = float(speed_field.rstrip("x"))
            return (self._duration - out_time) / speed
        except (TypeError, ValueError, ZeroDivisionError):
            return None


class FFmpegProgressTracker:
    """Run `args` to completion, calling `on_progress` with a status dict as it goes.

    `duration` and `total_bytes` describe the *input*: the media duration in
    seconds and its size on disk. Without a duration ffmpeg's output cannot be
    turned into a ratio, so the command still runs, it just reports no progress.
    """

    def __init__(
        self,
        args: list[str],
        on_progress: ProgressHook,
        *,
        duration: float = 0,
        total_bytes: int = 0,
        filename: str = "",
        stdin: int | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        # Without this ffmpeg reports nothing on stdout and the bar never moves,
        # which is too easy for a caller to forget. Guarantee it here.
        self._args = args if "-progress" in args else [*args, "-progress", "pipe:1"]
        self._on_progress = on_progress
        self._stdin = stdin
        self._env = env

        self._duration = duration_to_process(args, duration)
        # The output covers only the part of the input being processed.
        self._total_bytes = int(total_bytes * self._duration / duration) if duration else 0

        self._reporter = FFmpegProgressReporter(
            on_progress,
            args=args,
            duration=duration,
            total_bytes=total_bytes,
            filename=filename,
        )
        self._stdout_queue: Queue[str] = Queue()
        self._stderr_queue: Queue[str] = Queue()
        self._stdout = ""
        self._stderr = ""
        self.proc: subprocess.Popen | None = None

    def run(self) -> tuple[str, str, int]:
        """Run ffmpeg to completion. Returns (stdout, stderr, returncode)."""
        self.proc = subprocess.Popen(
            self._args,
            text=True,
            encoding="utf8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=self._stdin,
            env=self._env,
        )
        self._started_at = time.time()

        readers = [
            Thread(target=self._drain, args=(self.proc.stdout, self._stdout_queue), daemon=True),
            Thread(target=self._drain, args=(self.proc.stderr, self._stderr_queue), daemon=True),
        ]
        for reader in readers:
            reader.start()

        returncode = self._wait()

        for reader in readers:
            reader.join(timeout=5)
        self._consume_queues()

        if sys.platform == "win32":
            # Give Windows a moment to release the handles on the output file,
            # which the caller is about to rename.
            time.sleep(0.5)

        return self._stdout, self._stderr, returncode

    @staticmethod
    def _drain(stream, queue: Queue[str]) -> None:
        """Read a pipe to EOF from its own thread.

        ffmpeg writes progress to stdout and its log to stderr. Reading them
        one after the other in a single thread deadlocks as soon as the pipe
        we are not reading fills up.
        """
        for line in iter(stream.readline, ""):
            queue.put(line.rstrip())
        stream.close()

    def _wait(self) -> int:
        assert self.proc is not None
        returncode = self.proc.poll()
        while returncode is None:
            time.sleep(0.05)
            self._consume_queues()
            self._reporter.tick()
            returncode = self.proc.poll()
        return returncode

    def _consume_queues(self) -> None:
        while True:
            try:
                line = self._stdout_queue.get_nowait() + "\n"
            except Empty:
                break
            self._stdout += line
            self._reporter.feed(line)

        while True:
            try:
                line = self._stderr_queue.get_nowait()
            except Empty:
                break
            self._stderr += line + "\n"
            if line.strip():
                logger.debug(f"ffmpeg: {line}")
