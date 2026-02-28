from __future__ import annotations

import logging
import os

from runtime.base import ProcessResult

logger = logging.getLogger("videodl")


def _get_activity():
    """Get the current Android PythonActivity via pyjnius."""
    from jnius import autoclass

    return autoclass("org.kivy.android.PythonActivity").mActivity


class AndroidProcessRunner:
    """Android implementation — delegates to Java ProcessBuilder via pyjnius."""

    def run(
        self,
        args: list[str],
        capture_output: bool = False,
        text: bool = False,
        timeout: float | None = None,
    ) -> ProcessResult:
        return self._exec(args)

    def popen_communicate(self, args: list[str]) -> ProcessResult:
        return self._exec(args)

    @staticmethod
    def _exec(args: list[str]) -> ProcessResult:
        from jnius import autoclass

        ArrayList = autoclass("java.util.ArrayList")
        ProcessBuilder = autoclass("java.lang.ProcessBuilder")
        BufferedReader = autoclass("java.io.BufferedReader")
        InputStreamReader = autoclass("java.io.InputStreamReader")

        cmd = ArrayList()
        for a in args:
            cmd.add(a)

        pb = ProcessBuilder(cmd)
        pb.redirectErrorStream(False)
        proc = pb.start()

        # Read stdout
        stdout_reader = BufferedReader(InputStreamReader(proc.getInputStream()))
        stdout_lines = []
        while True:
            line = stdout_reader.readLine()
            if line is None:
                break
            stdout_lines.append(str(line))
        stdout_reader.close()

        # Read stderr
        stderr_reader = BufferedReader(InputStreamReader(proc.getErrorStream()))
        stderr_lines = []
        while True:
            line = stderr_reader.readLine()
            if line is None:
                break
            stderr_lines.append(str(line))
        stderr_reader.close()

        retcode = proc.waitFor()
        return ProcessResult(
            returncode=retcode,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
        )


class AndroidPaths:
    """Android path resolution via pyjnius."""

    def get_config_dir(self) -> str:
        activity = _get_activity()
        config_dir = os.path.join(str(activity.getFilesDir().getAbsolutePath()), "video-dl")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def get_default_download_dir(self) -> str:
        from jnius import autoclass

        Environment = autoclass("android.os.Environment")
        return str(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath())

    def open_folder(self, path: str) -> None:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        File = autoclass("java.io.File")

        intent = Intent(Intent.ACTION_VIEW)
        uri = Uri.fromFile(File(path))
        intent.setDataAndType(uri, "resource/folder")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try:
            _get_activity().startActivity(intent)
        except Exception:
            logger.warning(f"Could not open folder: {path}")

    def get_ffmpeg_path(self) -> str:
        """Return path to the bundled FFmpeg binary in the APK's native lib dir."""
        activity = _get_activity()
        native_lib_dir = str(activity.getApplicationInfo().nativeLibraryDir)
        return os.path.join(native_lib_dir, "libffmpeg.so")

    def get_ffprobe_path(self) -> str:
        """Return path to the bundled FFprobe binary in the APK's native lib dir."""
        activity = _get_activity()
        native_lib_dir = str(activity.getApplicationInfo().nativeLibraryDir)
        return os.path.join(native_lib_dir, "libffprobe.so")

    def get_ff_path(self) -> dict[str, str]:
        """Return ffmpeg/ffprobe paths dict compatible with core/ functions."""
        return {"ffmpeg": self.get_ffmpeg_path(), "ffprobe": self.get_ffprobe_path()}
