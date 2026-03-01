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
        """Return ffmpeg/ffprobe paths — assumes bundled in app's native lib dir."""
        # Flet bundles .so files in the app's native library directory
        native_lib = os.environ.get("FLET_APP_STORAGE_DATA", "")
        if native_lib:
            native_lib = os.path.dirname(native_lib)  # go up from files/ to app dir
        return {
            "ffmpeg": "ffmpeg",  # fallback to PATH for now
            "ffprobe": "ffprobe",
        }
