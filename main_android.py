"""Android entry point — no updater, no argparse, no desktop binary auto-install."""

from __future__ import annotations

import os
import sys
import traceback

# Must be first — before any module imports gui/ or runtime.get_paths()
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
    _log(f"[1] Starting. CWD={os.getcwd()}")
    _log(f"[2] FLET_APP_STORAGE_DATA={os.environ.get('FLET_APP_STORAGE_DATA', 'NOT SET')}")
    _log(f"[3] sys.path={sys.path[:5]}")

    try:
        import logging
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
                import stat
                st = os.stat(path)
                _log(f"[5d] {name}: mode={oct(st.st_mode)} size={st.st_size}")
        _log(f"[5i] LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH', 'NOT SET')}")

        # Try running ffmpeg to verify execution works
        import subprocess
        ffmpeg_bin = ff.get("ffmpeg", "ffmpeg")
        try:
            result = subprocess.run(
                [ffmpeg_bin, "-version"],
                capture_output=True, text=True, timeout=10,
            )
            _log(f"[5j] ffmpeg -version rc={result.returncode}")
            _log(f"[5k] stdout={result.stdout[:200]}")
            _log(f"[5l] stderr={result.stderr[:300]}")
        except Exception as e:
            _log(f"[5j] ffmpeg exec FAILED: {type(e).__name__}: {e}")

        init_paths_android(paths)
        _log("[6] Paths initialized")

        from gui.app import videodl_gui_android

        _log("[7] gui.app imported, calling ft.run()...")
        videodl_gui_android()
        _log("[8] ft.run() returned (should not happen)")

    except Exception:
        _log(f"[ERROR]\n{traceback.format_exc()}")
        raise


main()
