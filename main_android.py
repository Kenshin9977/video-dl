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

        init_paths_android(AndroidPaths())
        _log("[6] Paths initialized")

        from gui.app import videodl_gui_android

        _log("[7] gui.app imported, calling ft.run()...")
        videodl_gui_android()
        _log("[8] ft.run() returned (should not happen)")

    except Exception:
        _log(f"[ERROR]\n{traceback.format_exc()}")
        raise


main()
