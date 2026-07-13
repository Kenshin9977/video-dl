"""Make yt-dlp report download progress when ffmpeg is the one downloading.

When the user trims a video (`core/ydl_opts.py` sets `download_ranges`), yt-dlp does
not download the file itself: it hands the whole job to ffmpeg, through `FFmpegFD`.
Upstream reports nothing while that runs, so the download bar sits at zero for the
entire download and jumps to 100% at the end. Same for anything else that routes
through FFmpegFD, live streams included.

The seam is `FFmpegFD._call_downloader`, which builds its own ffmpeg command and
runs it through the `Popen` in its module. We do not rebuild that command: a Popen
that stands in for yt-dlp's appends `-progress` to whatever it was given.

It writes to a file rather than to `pipe:1`, unlike everywhere else we do this.
FFmpegFD's stdout is not ours to take: it is where ffmpeg writes the media itself
when yt-dlp asks for output on stdout. A file touches nothing.

Guarded like the rest: a moved seam costs the bar, never the download.
tests/test_ffmpegfd_progress.py checks the seams against the installed yt-dlp.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import threading
import time
from typing import Any, cast

from core.ffmpeg_progress import FFmpegProgressReporter

logger = logging.getLogger("videodl")

_installed = False
_ORIGINAL_POPEN: type | None = None

# Set only around one _call_downloader call, on the thread making it, so the Popen
# stand-in only ever touches the ffmpeg command we mean it to.
_current: threading.local = threading.local()

_POLL_INTERVAL = 0.1
# Long enough for the follower to notice ffmpeg is gone and read what it left behind,
# short enough that a wedged reader can never hold the download open.
_FOLLOWER_TIMEOUT = 5


class _Context:
    def __init__(self, downloader, info_dict: dict) -> None:
        self.downloader = downloader
        self.info_dict = info_dict
        self.duration = float(info_dict.get("duration") or 0)
        self.total_bytes = int(info_dict.get("filesize") or info_dict.get("filesize_approx") or 0)
        self.filename = info_dict.get("_filename") or ""
        # The threads reading ffmpeg's progress. They have to be waited on: ffmpeg's
        # last report, the one that fills the bar, lands after it has exited, and
        # _call_downloader returning is what tells the app the download is done.
        self.followers: list[threading.Thread] = []


def install() -> bool:
    """Teach yt-dlp's ffmpeg downloader to report progress. Idempotent."""
    global _installed, _ORIGINAL_POPEN
    if _installed:
        return True

    try:
        from yt_dlp.downloader import external as external_fd
    except ImportError as e:
        logger.warning(f"yt-dlp has moved: ffmpeg downloads will run without progress ({e})")
        return False

    fd_class = getattr(external_fd, "FFmpegFD", None)
    original_call = getattr(fd_class, "_call_downloader", None)
    popen_class = cast(Any, getattr(external_fd, "Popen", None))

    if not (fd_class and original_call and popen_class and hasattr(fd_class, "_hook_progress")):
        logger.warning("yt-dlp has moved: ffmpeg downloads will run without progress")
        return False

    def _call_downloader(self, tmpfilename, info_dict):
        context = _Context(self, info_dict)
        _current.context = context
        try:
            return original_call(self, tmpfilename, info_dict)
        finally:
            _current.context = None
            for follower in context.followers:
                follower.join(timeout=_FOLLOWER_TIMEOUT)

    class _ProgressPopen(popen_class):  # type: ignore[misc, valid-type]
        """Stands in for yt-dlp's Popen inside the external downloader module.

        Only adds `-progress`, and only while an FFmpegFD download is in flight on
        this thread. Every other external downloader that goes through this class,
        aria2c and wget and curl, is untouched.
        """

        def __init__(self, args, *pargs, **kwargs):
            context = getattr(_current, "context", None)
            reporter, path = _prepare(context, args)
            if path:
                args = [*args, "-progress", path]

            super().__init__(args, *pargs, **kwargs)

            if reporter and path and context:
                follower = threading.Thread(target=_follow, args=(self, reporter, path), daemon=True)
                context.followers.append(follower)
                follower.start()

    fd_class._call_downloader = _call_downloader
    external_fd.Popen = _ProgressPopen
    _ORIGINAL_POPEN = popen_class
    _installed = True
    logger.debug("ffmpeg download progress installed")
    return True


def _prepare(context: _Context | None, args) -> tuple[FFmpegProgressReporter | None, str | None]:
    """A reporter and a file for ffmpeg to write its progress to, if this is a run we follow."""
    if context is None:
        return None, None

    def on_progress(status: dict) -> None:
        context.downloader._hook_progress(status, context.info_dict)

    reporter = FFmpegProgressReporter(
        on_progress,
        args=list(args),
        duration=context.duration,
        total_bytes=context.total_bytes,
        filename=context.filename,
        bytes_key="downloaded_bytes",
        status="downloading",
        # ffmpeg is the downloader here: the bytes it writes are the bytes it fetched.
        bytes_from_output=True,
    )
    if not reporter.reports_anything:
        # No duration means no ratio to report, so do not even ask ffmpeg for it.
        return None, None

    handle, path = tempfile.mkstemp(prefix="video-dl-progress-")
    os.close(handle)
    return reporter, path


def _follow(process, reporter: FFmpegProgressReporter, path: str) -> None:
    """Tail the progress file until ffmpeg is done, then clean it up."""
    try:
        with open(path, encoding="utf-8", errors="replace") as progress:
            while True:
                finished = process.poll() is not None
                reporter.feed(progress.read())
                if finished:
                    return
                time.sleep(_POLL_INTERVAL)
    except Exception as e:
        # A progress bar is never worth taking a download down with it.
        logger.debug(f"ffmpeg download progress stopped: {e}")
    finally:
        with contextlib.suppress(OSError):
            os.remove(path)
