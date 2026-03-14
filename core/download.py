from __future__ import annotations

import base64
import contextvars
import ctypes
import ctypes.wintypes
import json
import logging
import os
import re
import signal
import subprocess
import threading
import time

from yt_dlp import YoutubeDL
from yt_dlp.downloader.external import FFmpegFD
from yt_dlp.postprocessor import FFmpegPostProcessor
from yt_dlp.utils import DownloadCancelled as YtdlpDownloadCancelled

import runtime
from core.callbacks import CancelToken, ProgressCallback, StatusCallback
from core.config_types import DownloadConfig
from core.encode import post_process_dl
from core.exceptions import DownloadCancelled, DownloadTimeout, PlaylistNotFound
from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

logger = logging.getLogger("videodl")


def _unlock_cookie_db(database_path: str) -> None:
    """Use Windows Restart Manager to release any process lock on the cookie DB.

    Adapted from https://gist.github.com/csm10495/e89e660ffee0030e8ef410b793ad6a7e
    by Charles Machalow (MIT License).
    """
    from ctypes import WINFUNCTYPE, byref, c_wchar_p, windll
    from ctypes.wintypes import DWORD, UINT, WCHAR

    error_success = 0
    error_more_data = 234
    rm_force_shutdown = 1

    @WINFUNCTYPE(None, UINT)
    def _cb(pct: UINT) -> None:  # noqa: ARG001
        pass

    rstrtmgr = windll.LoadLibrary("Rstrtmgr")
    session_handle = DWORD(0)
    session_key = (WCHAR * 256)()

    if DWORD(rstrtmgr.RmStartSession(byref(session_handle), DWORD(0), session_key)).value != error_success:
        return
    try:
        rstrtmgr.RmRegisterResources(
            session_handle, 1,
            (c_wchar_p * 1)(database_path),
            0, None, 0, None,
        )
        proc_info_needed = DWORD(0)
        proc_info = DWORD(0)
        reboot_reasons = DWORD(0)
        result = DWORD(rstrtmgr.RmGetList(
            session_handle, byref(proc_info_needed),
            byref(proc_info), None, byref(reboot_reasons),
        )).value
        if result in (error_success, error_more_data) and proc_info_needed.value:
            logger.debug("Unlocking cookie DB held by %d process(es)", proc_info_needed.value)
            rstrtmgr.RmShutdown(session_handle, rm_force_shutdown, _cb)
    finally:
        rstrtmgr.RmEndSession(session_handle)


def _patch_cookie_db_copy() -> None:
    """On Windows, patch yt-dlp's _open_database_copy to release any browser
    lock on the cookie DB via Windows Restart Manager, then retry."""
    if os.name != "nt":
        return
    import yt_dlp.cookies as _ydl_cookies

    _original = _ydl_cookies._open_database_copy

    def _patched(database_path, tmpdir):
        try:
            return _original(database_path, tmpdir)
        except OSError:
            logger.debug("Cookie DB locked, attempting unlock via Restart Manager")
            _unlock_cookie_db(str(database_path))
            return _original(database_path, tmpdir)

    _ydl_cookies._open_database_copy = _patched


_patch_cookie_db_copy()


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_uint8 * 8),
    ]

    @classmethod
    def from_str(cls, s: str) -> "_GUID":
        s = s.strip("{}")
        p = s.split("-")
        g = cls()
        g.Data1 = int(p[0], 16)
        g.Data2 = int(p[1], 16)
        g.Data3 = int(p[2], 16)
        for i, b in enumerate(bytes.fromhex(p[3] + p[4])):
            g.Data4[i] = b
        return g


def _com_decrypt_app_bound_key(ciphertext: bytes) -> bytes | None:
    """Call IElevationService::DecryptData via COM vtable to decrypt Chrome's
    App-Bound Encryption key (Chrome 127+).

    CLSID: {708860E0-F641-4611-8895-7D867DD3675B} (Google Chrome Elevation Service)
    IID:   {A13E07E4-E324-4C66-9B80-E7DBE3D49494} (IElevator)
    vtable[5] = DecryptData(BSTR ciphertext, BSTR* plaintext, DWORD* last_error)
    """
    ole32 = ctypes.windll.ole32
    oleaut32 = ctypes.windll.oleaut32
    oleaut32.SysAllocStringByteLen.restype = ctypes.c_void_p
    oleaut32.SysAllocStringByteLen.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]

    clsid = _GUID.from_str("{708860E0-F641-4611-8895-7D867DD3675B}")
    iid = _GUID.from_str("{A13E07E4-E324-4C66-9B80-E7DBE3D49494}")

    ole32.CoInitialize(None)
    ppv = ctypes.c_void_p(0)
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid), None, 4,  # CLSCTX_LOCAL_SERVER
        ctypes.byref(iid), ctypes.byref(ppv),
    )
    if hr != 0 or not ppv.value:
        logger.debug("CoCreateInstance failed: hr=0x%08X", hr & 0xFFFFFFFF)
        return None

    try:
        buf = ctypes.create_string_buffer(ciphertext)
        bstr_in = oleaut32.SysAllocStringByteLen(buf, len(ciphertext))
        if not bstr_in:
            return None

        bstr_out = ctypes.c_void_p(0)
        last_error = ctypes.wintypes.DWORD(0)

        vtable_ptr = ctypes.c_size_t.from_address(ppv.value).value
        decrypt_fn_ptr = ctypes.c_size_t.from_address(
            vtable_ptr + 5 * ctypes.sizeof(ctypes.c_size_t)
        ).value
        decrypt_data = ctypes.WINFUNCTYPE(
            ctypes.HRESULT,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.wintypes.DWORD),
        )(decrypt_fn_ptr)

        hr = decrypt_data(ppv.value, bstr_in, ctypes.byref(bstr_out), ctypes.byref(last_error))
        oleaut32.SysFreeString(bstr_in)

        if hr != 0 or not bstr_out.value:
            logger.debug(
                "IElevationService::DecryptData failed: hr=0x%08X last_error=%d",
                hr & 0xFFFFFFFF, last_error.value,
            )
            return None

        byte_len = ctypes.c_uint32.from_address(bstr_out.value - 4).value
        result = bytes((ctypes.c_uint8 * byte_len).from_address(bstr_out.value))
        oleaut32.SysFreeString(bstr_out)
        # AES-256 key is 32 bytes; strip any leading metadata if result is longer
        return result[-32:] if len(result) >= 32 else None
    finally:
        vtable_ptr = ctypes.c_size_t.from_address(ppv.value).value
        release_ptr = ctypes.c_size_t.from_address(
            vtable_ptr + 2 * ctypes.sizeof(ctypes.c_size_t)
        ).value
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(release_ptr)(ppv.value)


def _get_app_bound_key(browser_root: str) -> bytes | None:
    """Read Chrome's app_bound_encrypted_key from Local State and decrypt via COM."""
    local_state_path = os.path.join(browser_root, "Local State")
    if not os.path.isfile(local_state_path):
        return None
    try:
        with open(local_state_path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None

    key_b64 = state.get("os_crypt", {}).get("app_bound_encrypted_key")
    if not key_b64:
        return None

    encrypted = base64.b64decode(key_b64)
    if not encrypted.startswith(b"APPB"):
        return None

    logger.debug("Found App-Bound Encryption key, attempting COM decryption")
    try:
        return _com_decrypt_app_bound_key(encrypted[4:])
    except Exception as e:
        logger.debug("App-Bound COM decryption failed: %s", e)
        return None


def _patch_v20_decryptor() -> None:
    """Patch WindowsChromeCookieDecryptor to support Chrome 127+ v20 cookies
    by decrypting the app-bound key via IElevationService COM."""
    if os.name != "nt":
        return
    try:
        import yt_dlp.cookies as _ydl_cookies

        _orig_init = _ydl_cookies.WindowsChromeCookieDecryptor.__init__
        _orig_decrypt = _ydl_cookies.WindowsChromeCookieDecryptor.decrypt
        _decrypt_aes_gcm = _ydl_cookies._decrypt_aes_gcm

        def _new_init(self, browser_root, ydl_logger, meta_version=None):
            _orig_init(self, browser_root, ydl_logger, meta_version)
            self._v20_key = _get_app_bound_key(browser_root)

        def _new_decrypt(self, encrypted_value):
            if encrypted_value[:3] == b"v20":
                if not getattr(self, "_v20_key", None):
                    self._logger.warning(
                        "cannot decrypt v20 cookies: App-Bound key unavailable",
                        only_once=True,
                    )
                    return None
                nonce_len, tag_len = 12, 16
                raw = encrypted_value[3:]
                nonce = raw[:nonce_len]
                ciphertext = raw[nonce_len:-tag_len]
                auth_tag = raw[-tag_len:]
                self._cookie_counts["v20"] = self._cookie_counts.get("v20", 0) + 1
                return _decrypt_aes_gcm(
                    ciphertext, self._v20_key, nonce, auth_tag, self._logger,
                    hash_prefix=self._meta_version >= 24,
                )
            return _orig_decrypt(self, encrypted_value)

        _ydl_cookies.WindowsChromeCookieDecryptor.__init__ = _new_init
        _ydl_cookies.WindowsChromeCookieDecryptor.decrypt = _new_decrypt
    except Exception as e:
        logger.debug("Could not patch v20 cookie decryptor: %s", e)


_patch_v20_decryptor()


STALL_TIMEOUT = 120  # seconds without any progress before considered hung
MAX_RETRIES = 3
BASE_BACKOFF = 5  # seconds, doubles each retry

_STATUS_PATTERNS = [
    (re.compile(r"Extracting cookies from", re.IGNORECASE), GF.extracting_cookies),
    (re.compile(r"Solving JS challenge|\[jsc", re.IGNORECASE), GF.solving_js),
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
        self._update_status(msg)

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
    ffmpeg_path = ff_path.get("ffmpeg", "ffmpeg")
    if ffmpeg_path != "ffmpeg":
        FFmpegPostProcessor._ffmpeg_location.set(ffmpeg_path)
        # Patch FFmpegFD.available so it finds our custom ffmpeg binary
        FFmpegFD.available = classmethod(lambda cls, path=None: True)
    else:
        FFmpegPostProcessor._ffmpeg_location.set(None)
    if runtime.is_android() and ffmpeg_path != "ffmpeg":
        qjs_path = os.path.join(os.path.dirname(ffmpeg_path), "libqjs.so")
        if os.path.isfile(qjs_path):
            ydl_opts["js_runtimes"] = {"quickjs": {"path": qjs_path}}
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
                result.append(ydl.extract_info(config.url))  # noqa: B023
            except BaseException as e:
                error.append(e)  # noqa: B023

        ctx = contextvars.copy_context()
        t = threading.Thread(target=ctx.run, args=(target,), daemon=True)
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
