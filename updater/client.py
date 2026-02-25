import logging
import pathlib
import shutil
import sys

from utils.sys_utils import APP_NAME, APP_VERSION

logger = logging.getLogger("videodl")

# GitHub Releases URLs for metadata and targets
METADATA_BASE_URL = "https://github.com/Kenshin9977/video-dl/releases/latest/download/"
TARGET_BASE_URL = METADATA_BASE_URL

FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
MODULE_DIR = pathlib.Path(__file__).resolve().parent


def _get_install_dir():
    if FROZEN:
        return pathlib.Path(sys.executable).parent
    return MODULE_DIR.parent


def _get_update_cache_dir():
    if sys.platform == "win32":
        base = pathlib.Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library"
    else:
        base = pathlib.Path.home() / ".local" / "share"
    return base / APP_NAME / "update_cache"


def check_for_updates():
    try:
        from tufup.client import Client

        cache_dir = _get_update_cache_dir()
        metadata_dir = cache_dir / "metadata"
        target_dir = cache_dir / "targets"

        for d in [metadata_dir, target_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Bootstrap: copy bundled root.json to cache if not yet present
        trusted_root_src = _get_install_dir() / "root.json" if FROZEN else MODULE_DIR.parent / "root.json"
        trusted_root_dst = metadata_dir / "root.json"
        if trusted_root_src.exists() and not trusted_root_dst.exists():
            shutil.copy2(trusted_root_src, trusted_root_dst)

        client = Client(
            app_name=APP_NAME,
            app_install_dir=_get_install_dir(),
            current_version=APP_VERSION,
            metadata_dir=metadata_dir,
            metadata_base_url=METADATA_BASE_URL,
            target_dir=target_dir,
            target_base_url=TARGET_BASE_URL,
            refresh_required=False,
        )
        new_update = client.check_for_updates()
        if new_update:
            logger.info(f"Update available: {new_update}")
            client.download_and_apply_update(
                skip_confirmation=True,
                purge_dst_dir=False,
            )
            return True
    except Exception as e:
        logger.info(f"Update check failed (non-fatal): {e}")
    return False
