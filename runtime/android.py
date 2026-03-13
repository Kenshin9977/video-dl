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
        """Return ffmpeg/ffprobe paths from the APK's native library directory.

        Binaries are packed as libffmpeg.so / libffprobe.so in jniLibs so Android
        extracts them into the app's nativeLibraryDir where they are executable.
        """
        # Find the native lib dir — Android extracts jniLibs .so files here
        native_lib = self._find_native_lib_dir()
        if native_lib:
            ffmpeg = os.path.join(native_lib, "libffmpeg.so")
            ffprobe = os.path.join(native_lib, "libffprobe.so")
            if os.path.isfile(ffmpeg):
                # Shared libs are already in the same dir, LD_LIBRARY_PATH for safety
                ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                if native_lib not in ld_path:
                    os.environ["LD_LIBRARY_PATH"] = native_lib + (":" + ld_path if ld_path else "")
                return {"ffmpeg": ffmpeg, "ffprobe": ffprobe}

        logger.warning("FFmpeg binaries not found in native lib dir")
        return {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}

    @staticmethod
    def _find_native_lib_dir() -> str:
        """Find the app's native library directory.

        The native lib dir is under /data/app/~~<hash>/<app_id>-<hash>/lib/arm64/
        which is not predictable. We find it by reading /proc/self/maps for
        libflutter.so which is always loaded from the same directory.
        """
        # Method 1: parse /proc/self/maps for libflutter.so path
        try:
            with open("/proc/self/maps") as f:
                for line in f:
                    if "libflutter.so" in line:
                        # Line format: addr perms offset dev inode path
                        parts = line.strip().split()
                        if len(parts) >= 6:
                            lib_path = parts[-1]  # e.g. /data/app/.../lib/arm64/libflutter.so
                            native_dir = os.path.dirname(lib_path)
                            if os.path.isdir(native_dir):
                                return native_dir
                        break
        except OSError:
            pass

        # Method 2: well-known symlink paths
        app_id = "com.videodl.video_dl"
        for candidate in [
            f"/data/data/{app_id}/lib",
            f"/data/user/0/{app_id}/lib",
        ]:
            if os.path.isdir(candidate):
                return candidate

        # Method 3: derive from FLET_APP_STORAGE_DATA
        base = os.environ.get("FLET_APP_STORAGE_DATA", "")
        if base:
            app_dir = os.path.dirname(base)
            candidate = os.path.join(app_dir, "lib")
            if os.path.isdir(candidate):
                return candidate

        return ""
