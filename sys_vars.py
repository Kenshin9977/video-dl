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
    """Initialize binary paths on Android — native libs bundled in APK."""
    global FF_PATH, QJS_PATH, ARIA2C_PATH, _initialized
    if _initialized:
        return
    import os

    FF_PATH = android_paths.get_ff_path()
    # qjs and aria2c are bundled as .so in the same native lib dir
    ffmpeg_path = FF_PATH.get("ffmpeg", "")
    if ffmpeg_path and ffmpeg_path != "ffmpeg":
        native_dir = os.path.dirname(ffmpeg_path)
        qjs = os.path.join(native_dir, "libqjs.so")
        if os.path.isfile(qjs):
            QJS_PATH = qjs
        aria2c = os.path.join(native_dir, "libaria2c.so")
        if os.path.isfile(aria2c):
            ARIA2C_PATH = aria2c
    _initialized = True
