"""Make yt-dlp report download progress while aria2c is doing the downloading.

yt-dlp hands the download to aria2c and then simply waits for it to exit, so the
download bar sits at zero for the whole download and jumps to 100% at the end.
That matters here: video-dl sets aria2c as the external downloader for `http`,
which yt-dlp also uses for `https`, so aria2c handles most downloads.

aria2c can expose a JSON-RPC server. We give it a port and a secret, poll it while
it runs, and feed what it reports into yt-dlp's normal progress hooks.

Upstream carried a version of this until 2026-05-28, when it was deleted along
with aria2c's m3u8/dash support (advisory GHSA-vx4q-3cr2-7cg2). We do not bring
any of that back: no fragments, no manifests, just the single file download that
video-dl actually asks aria2c for.

Like core/ytdlp_patch.py, this reaches into yt-dlp and is guarded: if a seam has
moved, install() logs and returns, downloads still work, the bar just does not
move. tests/test_aria2c_progress.py checks the seams against the installed yt-dlp.
"""

from __future__ import annotations

import contextlib
import functools
import json
import logging
import subprocess
import time
import uuid

logger = logging.getLogger("videodl")

_installed = False

# How long to wait for aria2c's RPC server to accept a connection, and how long to
# let it claim it has nothing to download before concluding it is wedged.
_RPC_STARTUP_ATTEMPTS = 20
_RPC_POLL_INTERVAL = 0.1
_IDLE_TIMEOUT = 10


def install() -> bool:
    """Teach yt-dlp's aria2c downloader to report progress. Idempotent."""
    global _installed
    if _installed:
        return True

    try:
        from yt_dlp.downloader import external as external_fd
        from yt_dlp.utils import Popen, find_available_port, traverse_obj
    except ImportError as e:
        logger.warning(f"yt-dlp has moved: aria2c will download without progress ({e})")
        return False

    aria2c_class = getattr(external_fd, "Aria2cFD", None)
    seams = ("_call_downloader", "_call_process", "_make_cmd", "_hook_progress")
    if not aria2c_class or not all(hasattr(aria2c_class, seam) for seam in seams):
        logger.warning("yt-dlp has moved: aria2c will download without progress")
        return False

    original_call_downloader = aria2c_class._call_downloader
    original_call_process = aria2c_class._call_process
    original_make_cmd = aria2c_class._make_cmd

    def _call_downloader(self, tmpfilename, info_dict):
        allocate_rpc(self, info_dict, find_available_port)
        return original_call_downloader(self, tmpfilename, info_dict)

    def _make_cmd(self, tmpfilename, info_dict):
        return original_make_cmd(self, tmpfilename, info_dict) + rpc_flags(info_dict)

    def _call_process(self, cmd, info_dict):
        if "__rpc" not in info_dict:
            return original_call_process(self, cmd, info_dict)
        return _download_with_progress(self, cmd, info_dict, Popen, traverse_obj)

    aria2c_class._call_downloader = _call_downloader
    aria2c_class._make_cmd = _make_cmd
    aria2c_class._call_process = _call_process
    _installed = True
    logger.debug("aria2c download progress installed")
    return True


def allocate_rpc(downloader, info_dict: dict, find_available_port) -> dict | None:
    """Reserve a port and a secret for aria2c's RPC server, on the info dict.

    Honours the same compat opt yt-dlp uses to turn external downloader progress
    off. No free port means no progress, not a failed download.
    """
    if "no-external-downloader-progress" in downloader.params.get("compat_opts", []):
        return None

    port = find_available_port()
    if not port:
        return None

    info_dict["__rpc"] = {"port": port, "secret": str(uuid.uuid4())}
    return info_dict["__rpc"]


def rpc_flags(info_dict: dict) -> list[str]:
    """The aria2c flags that open the RPC server, if one was reserved.

    Appended after everything else, so that neither yt-dlp's own pinned flags nor
    a user's --downloader-args can take the port out from under us.
    """
    rpc = info_dict.get("__rpc")
    if not rpc:
        return []
    return [
        "--enable-rpc",
        f"--rpc-listen-port={rpc['port']}",
        f"--rpc-secret={rpc['secret']}",
    ]


def rpc_call(downloader, port: int, secret: str, method: str, params=()) -> object:
    """One JSON-RPC call to the local aria2c. Raises ConnectionError on any failure."""
    from yt_dlp.networking import Request

    call_id = str(uuid.uuid4())
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": call_id,
            "method": method,
            "params": [f"token:{secret}", *params],
        }
    ).encode()

    request = Request(
        f"http://localhost:{port}/jsonrpc",
        data=payload,
        headers={"Content-Type": "application/json", "Content-Length": f"{len(payload)}"},
        # aria2c is on localhost. Sending this through the user's proxy would fail.
        proxies={"all": None},
    )
    try:
        with downloader.ydl.urlopen(request) as response:
            answer = json.load(response)
    except Exception as e:
        raise ConnectionError(f"aria2c RPC {method} failed: {e}") from e

    if answer.get("id") != call_id:
        raise ConnectionError("aria2c RPC answered a different call")
    return answer["result"]


def _download_with_progress(downloader, cmd, info_dict, popen_class, traverse_obj):
    """Run aria2c, polling its RPC server, reporting into yt-dlp's progress hooks."""
    rpc = info_dict["__rpc"]
    call = functools.partial(rpc_call, downloader, rpc["port"], rpc["secret"])
    started = time.time()

    status = {
        "filename": info_dict.get("_filename"),
        "status": "downloading",
        "elapsed": 0,
        "downloaded_bytes": 0,
    }

    def stat(key, *sources, average=False):
        values = tuple(float(v) for v in traverse_obj(sources, (..., ..., key)) if v is not None) or (0,)
        return sum(values) / (len(values) if average else 1)

    with popen_class(cmd, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as process:
        if not _wait_for_rpc(downloader, call, process):
            _, stderr = process.communicate()
            return "", stderr, process.returncode

        try:
            downloader._hook_progress(status, info_dict)
            returncode = process.poll()
            idle_since = None

            while returncode is None:
                try:
                    # https://aria2.github.io/manual/en/html/aria2c.html#aria2.tellActive
                    active = call("aria2.tellActive")
                    done = call("aria2.tellStopped", [0, 1])
                except ConnectionError:
                    # The download itself is still going. Let it finish, just blind.
                    downloader.to_screen("[aria2c] RPC connection lost, waiting for the download to finish")
                    _, stderr = process.communicate()
                    return "", stderr, process.returncode

                downloaded = stat("totalLength", done) + stat("completedLength", active)
                speed = stat("downloadSpeed", active)
                total = stat("totalLength", active, done, average=True)
                if total < downloaded:
                    total = 0

                status.update(
                    {
                        "downloaded_bytes": int(downloaded),
                        "speed": speed or None,
                        "total_bytes": total or None,
                        "total_bytes_estimate": total or None,
                        "eta": (total - downloaded) / speed if total and speed else None,
                        "elapsed": time.time() - started,
                    }
                )
                downloader._hook_progress(status, info_dict)

                if not active and done:
                    with contextlib.suppress(ConnectionError):
                        call("aria2.shutdown")
                    returncode = process.wait()
                    break

                # Nothing active and nothing finished means aria2c is wedged. Without
                # this it would sit there and the download would hang forever.
                if not active and not done:
                    idle_since = idle_since or time.time()
                    if time.time() - idle_since > _IDLE_TIMEOUT:
                        downloader.to_screen("[aria2c] RPC reports no download at all, shutting it down")
                        with contextlib.suppress(ConnectionError):
                            call("aria2.shutdown")
                        returncode = process.wait()
                        break
                else:
                    idle_since = None

                time.sleep(_RPC_POLL_INTERVAL)
                returncode = process.poll()
        except Exception:
            # Including the cancel path: never leave an orphan aria2c behind.
            process.kill()
            process.wait()
            raise

        _, stderr = process.communicate()
        return "", stderr, returncode


def _wait_for_rpc(downloader, call, process) -> bool:
    """Poll aria2c's RPC server until it answers. False means carry on without progress."""
    for attempt in range(_RPC_STARTUP_ATTEMPTS):
        if process.poll() is not None:
            downloader.to_screen(f"[aria2c] exited immediately with code {process.returncode}")
            return False
        try:
            call("aria2.getVersion")
            return True
        except ConnectionError:
            downloader.write_debug(f"[aria2c] waiting for the RPC server ({attempt + 1}/{_RPC_STARTUP_ATTEMPTS})")
            time.sleep(_RPC_POLL_INTERVAL)

    downloader.to_screen("[aria2c] RPC server never came up, downloading without progress")
    return False
