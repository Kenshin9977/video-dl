"""Android entry point - no updater, no argparse, no desktop binary auto-install."""

from __future__ import annotations

import os
import sys
import traceback

# Must be first - before any module imports gui/ or runtime.get_paths()
import runtime

runtime.set_android()

# Write debug log to public Downloads folder (readable via adb without root)
_log_path = "/sdcard/Download/video-dl-debug.log"


def _log(msg):
    try:
        with open(_log_path, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def main():
    # yt-dlp caches what it learns about a YouTube player (the solved JS challenges)
    # under $XDG_CACHE_HOME/yt-dlp, else ~/.cache/yt-dlp. On Android HOME is unset, ~
    # is /data and not writable, so every extraction redid the work and every write
    # failed as a warning nobody saw. flet hands the app a cache dir; use it.
    if cache := os.environ.get("FLET_APP_STORAGE_CACHE"):
        os.environ.setdefault("XDG_CACHE_HOME", cache)

    _log(f"[1] Starting. CWD={os.getcwd()}")
    _log(f"[2] FLET_APP_STORAGE_DATA={os.environ.get('FLET_APP_STORAGE_DATA', 'NOT SET')}")
    _log(f"[3] sys.path={sys.path[:5]}")

    try:
        import warnings

        warnings.filterwarnings("ignore", message="urllib3.*doesn't match a supported version")
        _log("[4] Imports OK")

        from videodl_logger import videodl_logger

        videodl_logger(debug=False, verbose=False)
        _log("[5] Logger OK")

        from runtime.android import AndroidPaths
        from sys_vars import init_paths_android

        paths = AndroidPaths()
        ff = paths.get_ff_path()
        _log(f"[5b] FF_PATH={ff}")
        for name, path in ff.items():
            exists = os.path.isfile(path)
            _log(f"[5c] {name}: {path} exists={exists}")
            if exists:
                st = os.stat(path)
                _log(f"[5d] {name}: mode={oct(st.st_mode)} size={st.st_size}")
        _log(f"[5i] LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH', 'NOT SET')}")

        # Try running ffmpeg to verify execution works
        import subprocess

        ffmpeg_bin = ff.get("ffmpeg", "ffmpeg")
        try:
            result = subprocess.run(
                [ffmpeg_bin, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            _log(f"[5j] ffmpeg -version rc={result.returncode}")
            _log(f"[5k] stdout={result.stdout[:200]}")
            _log(f"[5l] stderr={result.stderr[:300]}")
        except Exception as e:
            _log(f"[5j] ffmpeg exec FAILED: {type(e).__name__}: {e}")

        init_paths_android(paths)
        _log("[6] Paths initialized")

        # QuickJS solves YouTube's JS challenges, and it failed silently for as long
        # as it was bundled: it crashed on launch and yt-dlp just did without it.
        # yt-dlp reads its version from the first line of --help; log that line.
        import sys_vars

        try:
            result = subprocess.run([sys_vars.QJS_PATH or "qjs", "--help"], capture_output=True, text=True, timeout=10)
            _log(f"[6b] qjs --help: {(result.stdout or result.stderr).splitlines()[:1]}")
        except Exception as e:
            _log(f"[6b] qjs exec FAILED: {type(e).__name__}: {e}")

        from gui.app import videodl_gui_android

        _log("[7] gui.app imported, calling ft.run()...")
        videodl_gui_android()
        _log("[8] ft.run() returned (should not happen)")

    except Exception:
        _log(f"[ERROR]\n{traceback.format_exc()}")
        raise


main()
