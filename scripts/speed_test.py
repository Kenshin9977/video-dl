"""How fast does the app download this link, and why? Run by hand: `make speed-test URL=...`.

Not a CI test, and cannot be: YouTube asks GitHub's runners to sign in (see ci.yml),
and a throughput check against a third-party host measures that host as much as the
app. It exists for "downloads are slow" reports: it goes through the app's own path
(the options VideodlApp builds, create_ydl, download(), the post-processing), prints
the YouTube client, format and downloader yt-dlp used, and the speed of both bars,
and fails below --min-mbps.

On a phone, the same lines land in /sdcard/Download/video-dl-debug.log for every
download (core/download.py, main_android.py).
"""

import argparse
import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gui.config  # noqa: E402
import sys_vars  # noqa: E402


class _Meter:
    """Bytes and time per bar, from the same status dicts the app's bars get."""

    def __init__(self):
        self.started: dict[str, float] = {}
        self.per_file: dict[str, dict[str, int]] = {}
        self.ended: dict[str, float] = {}
        # What the app's bar shows. For a remux that takes a second, the span between
        # the first and last report is too short to measure anything by.
        self.last_speed: dict[str, float] = {}

    def update(self, bar: str, status: dict, field: str) -> None:
        # Video and audio download one after the other, each counting from zero.
        now = time.monotonic()
        self.started.setdefault(bar, now)
        files = self.per_file.setdefault(bar, {})
        name = status.get("filename") or ""
        files[name] = max(files.get(name, 0), status.get(field) or 0)
        self.ended[bar] = now
        if status.get("speed"):
            self.last_speed[bar] = status["speed"]

    def total(self, bar: str) -> int:
        return sum(self.per_file.get(bar, {}).values())

    def mbps(self, bar: str) -> float:
        seconds = self.ended.get(bar, 0) - self.started.get(bar, 0)
        return self.total(bar) / 1e6 / seconds if seconds > 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="How fast does the app download this link, and why?")
    parser.add_argument("url")
    parser.add_argument("--min-mbps", type=float, default=1.0, help="fail if the download averages less (MB/s)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="video-dl-speed-") as workdir:
        # The app saves its settings as it is built; keep them away from the user's.
        gui.config._config_filename = os.path.join(workdir, "videodl-config.toml")
        sys_vars.FF_PATH = {
            "ffmpeg": shutil.which("ffmpeg") or "ffmpeg",
            "ffprobe": shutil.which("ffprobe") or "ffprobe",
        }
        sys_vars.ARIA2C_PATH = shutil.which("aria2c")
        sys_vars.QJS_PATH = shutil.which("qjs")

        from core.config_types import DownloadConfig
        from core.download import create_ydl, download
        from gui.app import VideodlApp

        page = MagicMock()
        page.services, page.overlay, page.controls = [], [], []
        app = VideodlApp(page)
        app.media_link.value = args.url
        app.download_path_text.value = workdir
        opts = app._gen_ydl_opts()

        meter = _Meter()
        opts["progress_hooks"] = [lambda d: meter.update("download", d, "downloaded_bytes")]
        progress_cb = MagicMock()
        progress_cb.on_process_progress.side_effect = lambda d: meter.update("process", d, "processed_bytes")

        trace = logging.StreamHandler(sys.stdout)
        trace.setFormatter(logging.Formatter("  %(message)s"))
        trace.addFilter(lambda r: r.getMessage().startswith(("yt-dlp:", "download:")))
        logging.getLogger("videodl").addHandler(trace)
        logging.getLogger("videodl").setLevel(logging.INFO)

        print(f"{args.url}\n  QuickJS: {sys_vars.QJS_PATH or 'none'}, aria2c: {sys_vars.ARIA2C_PATH or 'none'}")
        cancel = MagicMock()
        cancel.is_cancelled.return_value = False
        config = DownloadConfig(
            url=args.url,
            audio_only=False,
            target_vcodec=app._get_effective_vcodec(),
            ff_path=sys_vars.FF_PATH,
            ydl_opts=opts,
        )
        started = time.monotonic()
        download(create_ydl(opts, MagicMock(), sys_vars.FF_PATH), config, cancel, progress_cb)

    download_mbps = meter.mbps("download")
    print(
        f"download {meter.total('download') / 1e6:.1f} MB at {download_mbps:.2f} MB/s, "
        f"processing at {meter.last_speed.get('process', 0) / 1e6:.2f} MB/s, {time.monotonic() - started:.0f} s in all"
    )
    if download_mbps < args.min_mbps:
        print(f"FAIL: under {args.min_mbps} MB/s")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
