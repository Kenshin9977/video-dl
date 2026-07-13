#!/usr/bin/env bash
# Cut a release by hand. A yt-dlp bump releases itself, see .github/workflows/auto-release.yml.
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 2.1.0"
    exit 1
fi

VERSION="$1"
TAG="v${VERSION}"

if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: version must be in X.Y.Z format (got: $VERSION)"
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Error: working tree is not clean. Commit or stash changes first."
    exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: tag $TAG already exists"
    exit 1
fi

# version.py is the only place the version is written down. It used to be in three,
# synced by a sed that only worked on macOS, and they had already drifted apart.
python3 - "$VERSION" <<'PY'
import pathlib
import sys

path = pathlib.Path("version.py")
path.write_text(
    path.read_text(encoding="utf-8").replace(
        f'__version__ = "{__import__("version").__version__}"',
        f'__version__ = "{sys.argv[1]}"',
    ),
    encoding="utf-8",
)
PY

# uv.lock records the project's own version, so it has to follow.
uv lock

echo "Releasing:"
grep "^__version__" version.py

git add version.py uv.lock
git commit -m "Bump version to ${VERSION}"
git tag "$TAG"
git push origin master "$TAG"

echo ""
echo "Released ${TAG}. The build starts on its own."
