from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.base import PlatformPaths, ProcessRunner

_is_android: bool | None = None


def is_android() -> bool:
    """Detect if running on Android (Flet + pyjnius)."""
    global _is_android
    if _is_android is not None:
        return _is_android
    try:
        from jnius import autoclass

        autoclass("org.kivy.android.PythonActivity")
        _is_android = True
    except Exception:
        _is_android = False
    return _is_android


def get_process_runner() -> ProcessRunner:
    """Return the appropriate ProcessRunner for the current platform."""
    if is_android():
        from runtime.android import AndroidProcessRunner

        return AndroidProcessRunner()

    from runtime.desktop import DesktopProcessRunner

    return DesktopProcessRunner()


def get_paths() -> PlatformPaths:
    """Return the appropriate PlatformPaths for the current platform."""
    if is_android():
        from runtime.android import AndroidPaths

        return AndroidPaths()

    from runtime.desktop import DesktopPaths

    return DesktopPaths()
