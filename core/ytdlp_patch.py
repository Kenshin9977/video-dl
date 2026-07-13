"""Teach yt-dlp's ffmpeg postprocessors to report progress.

yt-dlp runs ffmpeg for the operations it owns: merging video and audio,
extracting audio, cutting SponsorBlock segments, trimming to a range. Upstream
reports none of it, so the GUI's process bar sits frozen through operations that
can take minutes.

video-dl used to solve this with a fork of yt-dlp, which meant republishing the
whole project to PyPI on a cron and shipping a yt-dlp that was months behind
upstream. Everything that fork changed on the ffmpeg side is replaced here by
one interception, on top of three things upstream already offers:

  FFmpegPostProcessor.real_run_ffmpeg   the one call that runs an ffmpeg command
  PostProcessor._hook_progress          already routed to `postprocessor_hooks`
  FFmpegPostProcessor.get_metadata_object   ffprobe, for the duration

We deliberately do not rebuild yt-dlp's ffmpeg command line: the wrapper lets
upstream build it, and swaps only the call that runs it. Whatever flags upstream
adds or fixes, we inherit.

This reaches into yt-dlp's internals, so it is guarded: if any seam it needs has
moved, install() logs and returns, yt-dlp keeps working, and the process bar just
does not move. tests/test_ytdlp_patch.py asserts the seams against the installed
yt-dlp, so a yt-dlp bump that breaks this fails CI instead of failing users.
"""

from __future__ import annotations

import contextlib
import logging
import os
import threading
from typing import Any, cast

from core.ffmpeg_progress import FFmpegProgressTracker

logger = logging.getLogger("videodl")

_installed = False

# yt-dlp's own Popen, kept so the shim can fall back to it and so tests can assert
# the shim is really a subclass of it rather than a lookalike.
_ORIGINAL_POPEN: type | None = None

# Set only for the duration of one real_run_ffmpeg call, on the thread making it,
# so the Popen shim below knows it is running an ffmpeg command we want to follow
# rather than, say, the ffprobe call that measured the duration.
_current: threading.local = threading.local()


class _Context:
    def __init__(self, pp, duration: float, total_bytes: int, filename: str) -> None:
        self.pp = pp
        self.duration = duration
        self.total_bytes = total_bytes
        self.filename = filename


def install() -> bool:
    """Wrap yt-dlp's ffmpeg execution so postprocessors report progress. Idempotent."""
    global _installed, _ORIGINAL_POPEN
    if _installed:
        return True

    from yt_dlp.postprocessor import ffmpeg as ffmpeg_pp

    pp_class = getattr(ffmpeg_pp, "FFmpegPostProcessor", None)
    original_run = getattr(pp_class, "real_run_ffmpeg", None)
    popen_class = cast(Any, getattr(ffmpeg_pp, "Popen", None))

    if not (pp_class and original_run and popen_class and hasattr(pp_class, "_hook_progress")):
        logger.warning("yt-dlp has moved: ffmpeg postprocessing will run without progress")
        return False

    def real_run_ffmpeg(self, input_path_opts, output_path_opts, *, expected_retcodes=(0,)):
        inputs = [path for path, _ in input_path_opts if path]
        output = next((path for path, _ in output_path_opts if path), "")
        _current.context = _Context(self, *_measure(self, inputs), filename=output)
        try:
            return original_run(self, input_path_opts, output_path_opts, expected_retcodes=expected_retcodes)
        finally:
            _current.context = None

    class _ProgressPopen(popen_class):  # type: ignore[misc, valid-type]
        """Stands in for yt-dlp's Popen inside the ffmpeg postprocessor module.

        Only `run` is overridden, and only when a real_run_ffmpeg call is in
        flight on this thread. Every other use of Popen in that module, ffprobe
        included, behaves exactly as before.
        """

        @classmethod
        def run(cls, args, *pargs, **kwargs):
            context = getattr(_current, "context", None)
            if context is None or not context.duration:
                return popen_class.run(args, *pargs, **kwargs)
            return _run_with_progress(context, list(args), kwargs.get("stdin"), kwargs.get("env"))

    pp_class.real_run_ffmpeg = real_run_ffmpeg
    ffmpeg_pp.Popen = _ProgressPopen
    _ORIGINAL_POPEN = popen_class
    _installed = True
    logger.debug("ffmpeg postprocessing progress installed")
    return True


def _measure(pp, inputs: list[str]) -> tuple[float, int]:
    """Duration in seconds and size in bytes of what ffmpeg is about to read."""
    total_bytes = 0
    duration = 0.0
    for path in inputs:
        with contextlib.suppress(OSError):
            total_bytes += os.path.getsize(path)
        if duration:
            continue
        try:
            metadata = pp.get_metadata_object(path)
            duration = float(metadata.get("format", {}).get("duration") or 0)
        except Exception as e:
            # An unreadable duration only costs the progress bar, so never raise.
            logger.debug(f"could not probe {path} for its duration: {e}")
    return duration, total_bytes


def _run_with_progress(context: _Context, args: list[str], stdin, env) -> tuple[str, str, int]:
    """Run one ffmpeg command, reporting to the postprocessor's progress hooks."""

    def on_progress(status: dict) -> None:
        context.pp._hook_progress(status, {})

    tracker = FFmpegProgressTracker(
        args,
        on_progress,
        duration=context.duration,
        total_bytes=context.total_bytes,
        filename=context.filename,
        stdin=stdin,
        env=env,
    )
    return tracker.run()
