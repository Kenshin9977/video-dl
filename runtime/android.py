from __future__ import annotations

import logging
import os
import subprocess

from runtime.base import ProcessResult

logger = logging.getLogger("videodl")


class AndroidProcessRunner:
    """Android implementation — delegates to subprocess (same as desktop on Flet)."""

    def run(
        self,
        args: list[str],
        capture_output: bool = False,
        text: bool = False,
        timeout: float | None = None,
    ) -> ProcessResult:
        result = subprocess.run(
            args,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
        )
        stdout = result.stdout if isinstance(result.stdout, str) else (result.stdout or b"").decode("utf-8")
        stderr = result.stderr if isinstance(result.stderr, str) else (result.stderr or b"").decode("utf-8")
        return ProcessResult(returncode=result.returncode, stdout=stdout, stderr=stderr)

    def popen_communicate(self, args: list[str]) -> ProcessResult:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        return ProcessResult(
            returncode=p.returncode,
            stdout=out.decode("utf-8") if out else "",
            stderr=err.decode("utf-8") if err else "",
        )


class AndroidPaths:
    """Android path resolution using Flet environment variables."""

    def get_config_dir(self) -> str:
        # Flet sets FLET_APP_STORAGE_DATA to the app's private data dir
        base = os.environ.get("FLET_APP_STORAGE_DATA", "")
        if not base:
            # Fallback: standard Android app data path
            base = "/data/data/com.videodl.video_dl/files"
        config_dir = os.path.join(base, "video-dl")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def get_default_download_dir(self) -> str:
        # Use a subfolder in public Downloads
        dl_dir = "/storage/emulated/0/Download/video-dl"
        os.makedirs(dl_dir, exist_ok=True)
        return dl_dir

    def open_folder(self, path: str) -> None:
        # No-op on Android — can't open file manager from Flet easily
        logger.debug(f"open_folder not supported on Android: {path}")

    def get_ff_path(self) -> dict[str, str]:
        """Return ffmpeg/ffprobe paths from the bundled android_libs directory.

        The gpl-shared build needs LD_LIBRARY_PATH set so the .so libs are found.
        """
        # Flet copies the python app into FLET_APP_STORAGE_DATA/app
        base = os.environ.get("FLET_APP_STORAGE_DATA", "")
        candidates = []
        if base:
            candidates.append(os.path.join(base, "app", "android_libs", "arm64-v8a"))
        # Fallback: look relative to this file (for local testing)
        candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "android_libs", "arm64-v8a")
        )

        lib_dir = ""
        for d in candidates:
            if os.path.isfile(os.path.join(d, "ffmpeg")):
                lib_dir = d
                break

        if lib_dir:
            # Ensure shared libs are discoverable by the dynamic linker
            ld_path = os.environ.get("LD_LIBRARY_PATH", "")
            if lib_dir not in ld_path:
                os.environ["LD_LIBRARY_PATH"] = lib_dir + (":" + ld_path if ld_path else "")
            return {
                "ffmpeg": os.path.join(lib_dir, "ffmpeg"),
                "ffprobe": os.path.join(lib_dir, "ffprobe"),
            }

        logger.warning("FFmpeg binaries not found in bundled android_libs")
        return {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}
