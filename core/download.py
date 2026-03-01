from __future__ import annotations

import logging
import os
import re
import signal
import subprocess
import threading
import time

from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegPostProcessor
from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

from core.callbacks import CancelToken, ProgressCallback, StatusCallback
from core.config_types import DownloadConfig
from core.encode import post_process_dl
from core.exceptions import DownloadCancelled, DownloadTimeout, PlaylistNotFound
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

logger = logging.getLogger("videodl")

STALL_TIMEOUT = 120  # seconds without any progress before considered hung
MAX_RETRIES = 3
BASE_BACKOFF = 5  # seconds, doubles each retry

_STATUS_PATTERNS = [
    (re.compile(r"Extracting cookies from", re.IGNORECASE), GF.extracting_cookies),
    (re.compile(r"Solving JS challenge", re.IGNORECASE), GF.solving_js),
    (re.compile(r"Extracting URL|Downloading webpage|Downloading player", re.IGNORECASE), GF.fetching_info),
]


class _YdlUiLogger:
    """Bridges yt-dlp log messages to a StatusCallback."""

    def __init__(self, status_cb: StatusCallback):
        self._status_cb = status_cb

    def _update_status(self, msg):
        for pattern, gui_field in _STATUS_PATTERNS:
            if pattern.search(msg):
                self._status_cb.on_status(gt(gui_field))
                return

    def debug(self, msg):
        logger.debug(msg)
        self._update_status(msg)

    def info(self, msg):
        logger.info(msg)
        self._update_status(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def create_ydl(
    ydl_opts: dict,
    status_cb: StatusCallback,
    ff_path: dict[str, str],
) -> YoutubeDL:
    """Create a reusable YoutubeDL instance (cookies extracted once)."""
    logger.debug("ydl options %s", ydl_opts)
    ydl_opts["logger"] = _YdlUiLogger(status_cb)
    FFmpegPostProcessor._ffmpeg_location.set(ff_path.get("ffmpeg"))
    return YoutubeDL(ydl_opts)


def _get_child_pids() -> set[int]:
    """Return PIDs of direct child processes (works on macOS/Linux)."""
    pid = os.getpid()
    try:
        out = subprocess.check_output(["pgrep", "-P", str(pid)], text=True, timeout=5)
        return {int(p) for p in out.split() if p.strip()}
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return set()


def _kill_new_children(before: set[int]) -> None:
    """Kill child processes that were spawned after *before* snapshot."""
    after = _get_child_pids()
    new = after - before
    for pid in new:
        try:
            logger.debug("Killing stuck child process %d", pid)
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


class _StallDetector:
    """Tracks whether yt-dlp is making progress via its progress hooks."""

    def __init__(self, stall_timeout: int = STALL_TIMEOUT):
        self._stall_timeout = stall_timeout
        self._last_activity = time.monotonic()
        self._lock = threading.Lock()

    def tick(self):
        """Called by yt-dlp progress/log hooks to signal activity."""
        with self._lock:
            self._last_activity = time.monotonic()

    def is_stalled(self) -> bool:
        with self._lock:
            return (time.monotonic() - self._last_activity) > self._stall_timeout


def download(
    ydl: YoutubeDL,
    config: DownloadConfig,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
) -> None:
    stall = _StallDetector()

    # Wrap existing progress hooks to also tick the stall detector
    original_hooks = list(ydl.params.get("progress_hooks", []))

    def progress_hook_with_stall(d):
        stall.tick()
        for hook in original_hooks:
            hook(d)

    ydl.params["progress_hooks"] = [progress_hook_with_stall]

    # Also tick on logger activity (covers extraction phase before download)
    ydl_logger = ydl.params.get("logger")
    if ydl_logger and isinstance(ydl_logger, _YdlUiLogger):
        original_debug = ydl_logger.debug

        def debug_with_stall(msg):
            stall.tick()
            original_debug(msg)

        ydl_logger.debug = debug_with_stall

    last_exc: BaseException | None = None
    for attempt in range(MAX_RETRIES):
        if cancel.is_cancelled():
            raise DownloadCancelled
        stall.tick()  # reset before each attempt
        children_before = _get_child_pids()

        result: list = []
        error: list = []

        def target():
            try:
                result.append(ydl.extract_info(config.url))
            except BaseException as e:
                error.append(e)

        t = threading.Thread(target=target, daemon=True)
        t.start()

        # Poll until thread finishes or stall detected
        while t.is_alive():
            t.join(timeout=5)
            if not t.is_alive():
                break
            if cancel.is_cancelled():
                _kill_new_children(children_before)
                t.join(timeout=10)
                raise DownloadCancelled
            if stall.is_stalled():
                logger.warning("No progress for %ds on %s — killing child processes",
                               STALL_TIMEOUT, config.url)
                _kill_new_children(children_before)
                t.join(timeout=10)
                break

        if t.is_alive() or (error and stall.is_stalled()):
            # Stall timeout — retry
            last_exc = error[0] if error else TimeoutError(
                f"stalled for {STALL_TIMEOUT}s on {config.url}")
            backoff = BASE_BACKOFF * (2 ** attempt)
            logger.warning("Attempt %d/%d stalled for %s, retrying in %ds",
                           attempt + 1, MAX_RETRIES, config.url, backoff)
            time.sleep(backoff)
            continue

        if error:
            exc = error[0]
            if isinstance(exc, YtdlpDownloadCancelled):
                raise DownloadCancelled from None
            raise exc

        infos_ydl = result[0] if result else None
        break
    else:
        raise DownloadTimeout(config.url) from last_exc

    # Restore original hooks
    ydl.params["progress_hooks"] = original_hooks

    if cancel.is_cancelled():
        raise DownloadCancelled
    _finish_download(ydl, infos_ydl, config, cancel, progress_cb)


def _finish_download(
    ydl: YoutubeDL,
    infos_ydl: dict | None,
    config: DownloadConfig,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
) -> None:
    if infos_ydl is None:
        raise PlaylistNotFound
    if config.audio_only:
        return
    progress_cb.on_download_progress({"status": "finished", "progress_float": 1.0})
    if infos_ydl.get("_type") == "playlist":
        for infos_ydl_entry in infos_ydl["entries"]:
            if cancel.is_cancelled():
                raise DownloadCancelled
            post_download(
                config.target_vcodec,
                ydl,
                infos_ydl_entry,
                cancel,
                progress_cb,
                config.ff_path,
            )
    else:
        post_download(config.target_vcodec, ydl, infos_ydl, cancel, progress_cb, config.ff_path)
    if cancel.is_cancelled():
        raise DownloadCancelled


def post_download(
    target_vcodec: str,
    ydl: YoutubeDL,
    infos_ydl: dict,
    cancel: CancelToken,
    progress_cb: ProgressCallback,
    ff_path: dict[str, str] | None = None,
) -> None:
    """
    Execute all needed processes after a youtube video download.

    Args:
        target_vcodec: Video codec target ("Best", "NLE", "x264", etc.)
        ydl: YoutubeDL instance
        infos_ydl: Video's infos fetched by yt-dlp
        cancel: Cancellation token
        progress_cb: Progress callback
        ff_path: FFmpeg/FFprobe paths
    """
    ext = infos_ydl["ext"]
    media_filename_formated = ydl.prepare_filename(infos_ydl)
    full_path = f"{os.path.splitext(media_filename_formated)[0]}.{ext}"
    post_process_dl(full_path, target_vcodec, cancel, progress_cb, ff_path)
