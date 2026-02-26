"""
CI-only: sign all platform binaries and update tufup metadata.

Usage:
    python -m tools.ci_sign \
        --version 2.0.0 \
        --artifacts-dir ./artifacts \
        --keys-dir ./keystore \
        --repo-dir ./repository
"""

import argparse
import logging
import pathlib
import shutil
import sys

from tufup.repo import Repository, make_gztar_archive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARTIFACT_MAP = {
    "video-dl-windows.exe": "video-dl-windows",
    "video-dl-linux": "video-dl-linux",
    "video-dl-macos": "video-dl-macos",
}


def main():
    parser = argparse.ArgumentParser(description="Sign platform artifacts for tufup")
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts-dir", required=True, type=pathlib.Path)
    parser.add_argument("--keys-dir", required=True, type=pathlib.Path)
    parser.add_argument("--repo-dir", default=pathlib.Path("repository"), type=pathlib.Path)
    args = parser.parse_args()

    config = Repository.load_config()

    # Single Repository instance — metadata is cumulative across all platforms
    repo = Repository(
        app_name="video-dl",
        repo_dir=args.repo_dir,
        keys_dir=args.keys_dir,
        key_map=config.get("key_map"),
        encrypted_keys=config.get("encrypted_keys", []),
        expiration_days=config.get("expiration_days"),
        thresholds=config.get("thresholds"),
    )
    repo._load_keys_and_roles(create_keys=False)

    for artifact_name, platform_app_name in ARTIFACT_MAP.items():
        artifact_path = args.artifacts_dir / artifact_name
        if not artifact_path.exists():
            logger.error(f"Artifact not found: {artifact_path}")
            sys.exit(1)

        # tufup expects a directory as bundle source
        bundle_dir = args.artifacts_dir / f"bundle-{platform_app_name}"
        bundle_dir.mkdir(exist_ok=True)
        shutil.copy2(artifact_path, bundle_dir / artifact_name)

        # Remove existing archive to avoid input() prompt in make_gztar_archive
        expected_archive = repo.targets_dir / f"{platform_app_name}-{args.version}.tar.gz"
        expected_archive.unlink(missing_ok=True)

        # Bypass add_bundle() which compares versions globally across all targets
        archive_meta = make_gztar_archive(
            src_dir=bundle_dir,
            dst_dir=repo.targets_dir,
            app_name=platform_app_name,
            version=args.version,
        )
        repo.roles.add_or_update_target(local_path=archive_meta.path)
        logger.info(f"Registered {platform_app_name} v{args.version}")

    repo.publish_changes(private_key_dirs=[args.keys_dir])
    logger.info("All platforms signed and metadata published.")


if __name__ == "__main__":
    main()
