"""
Build a new release and publish it via tufup + GitHub Releases.

Usage:
    python -m tools.gen_new_version

Steps:
    1. Build the binary with PyInstaller
    2. Add the bundle to the tufup repository (creates metadata + archive)
    3. Upload to GitHub Releases via `gh release create`
"""

import logging
import pathlib
import subprocess
import sys

import PyInstaller.__main__
from tufup.repo import Repository

from utils.sys_architecture import ARCHITECTURE
from utils.sys_utils import APP_NAME, APP_VERSION, PLATFORM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_DIR = pathlib.Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_DIR / "dist"
SPECS_DIR = PROJECT_DIR / "specs"
KEYS_DIR = PROJECT_DIR / "keystore"


def build_binary():
    """Build the binary using the platform-appropriate spec/tool."""
    if PLATFORM == "Windows":
        spec = SPECS_DIR / "Windows-video-dl.spec"
        PyInstaller.__main__.run([str(spec)])
    elif PLATFORM == "Linux":
        spec = SPECS_DIR / "Linux-video-dl.spec"
        PyInstaller.__main__.run([str(spec)])
    elif PLATFORM == "Darwin":
        macos_setup = PROJECT_DIR / "MACOS-video-dl.py"
        subprocess.run(
            [sys.executable, str(macos_setup), "py2app"],
            check=True,
        )
    else:
        sys.exit(f"Unsupported platform: {PLATFORM}")


def add_bundle_to_repo():
    """Add the built bundle to the tufup repository and publish metadata."""
    try:
        bundle_dirs = [p for p in DIST_DIR.iterdir() if p.is_dir()]
    except FileNotFoundError:
        sys.exit(f"Directory not found: {DIST_DIR}\nDid you run the build step?")

    if len(bundle_dirs) != 1:
        sys.exit(f"Expected one bundle dir in dist/, found {len(bundle_dirs)}.")

    bundle_dir = bundle_dirs[0]
    logger.info(f"Adding bundle: {bundle_dir}")

    repo = Repository.from_config()
    repo.add_bundle(new_bundle_dir=bundle_dir)
    repo.publish_changes(private_key_dirs=[KEYS_DIR])
    logger.info("tufup metadata updated.")


def upload_to_github():
    """Create a GitHub Release and upload tufup metadata + targets."""
    tag = f"v{APP_VERSION}"
    repo_dir = PROJECT_DIR / "my_repo"

    metadata_dir = repo_dir / "metadata"
    targets_dir = repo_dir / "targets"

    # Collect all files to upload
    files_to_upload = []
    if metadata_dir.exists():
        for f in metadata_dir.iterdir():
            if f.is_file():
                files_to_upload.append(str(f))
    if targets_dir.exists():
        for f in targets_dir.iterdir():
            if f.is_file():
                files_to_upload.append(str(f))

    if not files_to_upload:
        sys.exit("No files found to upload. Did add_bundle_to_repo succeed?")

    cmd = [
        "gh",
        "release",
        "create",
        tag,
        "--title",
        f"{APP_NAME} {APP_VERSION}",
        "--notes",
        f"Release {APP_VERSION} ({PLATFORM}-{ARCHITECTURE})",
    ] + files_to_upload

    logger.info(f"Creating GitHub release {tag}...")
    subprocess.run(cmd, check=True)
    logger.info(f"Release {tag} created successfully.")


if __name__ == "__main__":
    logger.info(f"Building {APP_NAME} v{APP_VERSION} for {PLATFORM}-{ARCHITECTURE}")
    build_binary()
    add_bundle_to_repo()
    upload_to_github()
    logger.info("Done.")
