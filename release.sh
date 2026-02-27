#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 2.1.0"
    exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

# Validate semver-ish format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: version must be in X.Y.Z format (got: $VERSION)"
    exit 1
fi

# Check clean working tree
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Error: working tree is not clean. Commit or stash changes first."
    exit 1
fi

# Check tag doesn't already exist
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: tag $TAG already exists"
    exit 1
fi

# Update version in pyproject.toml
sed -i '' "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml

# Update version in utils/sys_utils.py
sed -i '' "s/^APP_VERSION = \".*\"/APP_VERSION = \"${VERSION}\"/" utils/sys_utils.py

# Update version in macOS spec (CFBundleShortVersionString)
sed -i '' "s/'CFBundleShortVersionString': '.*'/'CFBundleShortVersionString': '${VERSION}'/" specs/macOS-video-dl.spec

# Verify changes
echo "Updated versions:"
grep "^version" pyproject.toml
grep "APP_VERSION" utils/sys_utils.py
grep "CFBundleShortVersionString" specs/macOS-video-dl.spec

# Commit, tag, push
git add pyproject.toml utils/sys_utils.py specs/macOS-video-dl.spec
git commit -m "Bump version to ${VERSION}"
git tag "$TAG"
git push origin master "$TAG"

echo ""
echo "Released ${TAG} — CI build will start automatically."
