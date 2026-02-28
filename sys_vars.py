from __future__ import annotations

# Module-level vars — populated by init_paths(), read after startup.
FF_PATH: dict[str, str] = {}
QJS_PATH: str | None = None
ARIA2C_PATH: str | None = None

_initialized = False


def init_paths() -> None:
    """Initialize binary paths. Call once at app startup, before GUI launch."""
    global FF_PATH, QJS_PATH, ARIA2C_PATH, _initialized
    if _initialized:
        return
    from utils.sys_utils import get_aria2c_path, get_ff_components_path, get_quickjs_path

    FF_PATH = get_ff_components_path()
    QJS_PATH = get_quickjs_path()
    ARIA2C_PATH = get_aria2c_path()
    _initialized = True


def init_paths_android(android_paths) -> None:
    """Initialize binary paths on Android — FFmpeg bundled in APK, no QuickJS/aria2c."""
    global FF_PATH, _initialized
    if _initialized:
        return
    FF_PATH = android_paths.get_ff_path()
    _initialized = True
