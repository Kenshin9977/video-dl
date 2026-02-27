"""
One-time TUF repository initialization.

Run this once on your dev machine to generate signing keys and initial metadata:

    python -m tools.repo_init

Keys are stored in keys/ (DO NOT commit private keys to git).
Metadata is stored in tuf_repo/ and the root.json is copied to the project root
for bundling with PyInstaller.
"""

import logging
import pathlib
import shutil

from tufup.repo import (
    DEFAULT_KEY_MAP,
    DEFAULT_KEYS_DIR_NAME,
    DEFAULT_REPO_DIR_NAME,
    Repository,
)
from utils.sys_utils import APP_NAME, APP_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
KEYS_DIR = PROJECT_DIR / DEFAULT_KEYS_DIR_NAME
REPO_DIR = PROJECT_DIR / DEFAULT_REPO_DIR_NAME

# Single key for all roles (acceptable for a small project)
KEY_NAME = "video_dl_key"
KEY_MAP = {role_name: [KEY_NAME] for role_name in DEFAULT_KEY_MAP}
ENCRYPTED_KEYS = []
THRESHOLDS = dict(root=1, targets=1, snapshot=1, timestamp=1)
EXPIRATION_DAYS = dict(root=365, targets=7, snapshot=7, timestamp=1)


if __name__ == "__main__":
    logger.info(f"Initializing tufup repo for {APP_NAME} v{APP_VERSION}")
    repo = Repository(
        app_name=APP_NAME,
        app_version_attr="utils.sys_utils.APP_VERSION",
        repo_dir=REPO_DIR,
        keys_dir=KEYS_DIR,
        key_map=KEY_MAP,
        expiration_days=EXPIRATION_DAYS,
        encrypted_keys=ENCRYPTED_KEYS,
        thresholds=THRESHOLDS,
    )
    repo.save_config()
    repo.initialize()

    # Copy root.json to project root for PyInstaller bundling
    root_src = REPO_DIR / "metadata" / "root.json"
    root_dst = PROJECT_DIR / "root.json"
    if root_src.exists():
        shutil.copy2(root_src, root_dst)
        logger.info(f"Copied root.json to {root_dst}")
    else:
        logger.warning(f"root.json not found at {root_src}")

    logger.info("Done. Add keys/ to .gitignore and keep private keys secure.")
