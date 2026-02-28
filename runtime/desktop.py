from __future__ import annotations

import os
import subprocess
from platform import system

from runtime.base import ProcessResult

PLATFORM = system()


class DesktopProcessRunner:
    """Desktop implementation — delegates to subprocess."""

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


class DesktopPaths:
    """Desktop path resolution for Windows, macOS, and Linux."""

    def get_config_dir(self) -> str:
        plat = PLATFORM
        if plat == "Windows":
            base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        elif plat == "Darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
        else:
            base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
        config_dir = os.path.join(base, "video-dl")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def get_default_download_dir(self) -> str:
        if PLATFORM != "Windows":
            download_path = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.isdir(download_path):
                return download_path
            return ""

        import winreg

        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as sub_key:  # type: ignore[attr-defined]
            location = winreg.QueryValueEx(sub_key, downloads_guid)[0]  # type: ignore[attr-defined]
        return location

    def open_folder(self, path: str) -> None:
        if PLATFORM == "Darwin":
            subprocess.Popen(["open", path])
        elif PLATFORM == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
