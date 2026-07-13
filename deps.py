"""Every external binary this project pins, and the only place they are written down.

The Python dependencies live in pyproject.toml and uv.lock. These are the ones that
do not: binaries fetched from GitHub releases at build time or at first run.

Renovate opens the pull requests that bump them (see .github/renovate.json). The
runtime installers import this module, the workflows and the Makefile read it with
`python deps.py <NAME>`, and tests/test_deps.py fails if a pin reappears anywhere
else. A pin written down twice is a pin that will drift: aria2c was pinned to
release-2.0.0 for the desktop and floated to 2.0.1 for Android, and the NDK was
27.2 in CI and 28.2 in the Makefile.

Keep this module free of imports at module level: the workflows run it with a bare
python, before any dependency is installed.

Deliberately not pinned here:
  yt-dlp, flet, tufup   pyproject.toml + uv.lock
  yt-dlp-ejs            comes with yt-dlp; the solver lib version is read back out
                        of the installed package, so it cannot disagree with it
  QuickJS on desktop    resolved from bellard.org at first run, not at build time
"""

# The FFmpeg build bundled into the Android APK. Upstream (yt-dlp/FFmpeg-Builds)
# publishes no androidarm64 asset, hence the fork. Pinned to an immutable autobuild
# tag: the `latest` tag these projects also publish is mutable, so a release could
# never be rebuilt byte for byte.
# renovate: datasource=github-releases depName=Kenshin9977/FFmpeg-Builds versioning=loose
FFMPEG_ANDROID_TAG = "autobuild-2026-06-15-18-44"
FFMPEG_ANDROID_REPO = "Kenshin9977/FFmpeg-Builds"
FFMPEG_ANDROID_ASSET = "ffmpeg-master-latest-androidarm64-gpl-shared.tar.xz"

# aria2c, both bundled into the APK and downloaded on first run on desktop. The
# same tag for both, or the two platforms ship different binaries.
# renovate: datasource=github-releases depName=Kenshin9977/aria2 versioning=loose
ARIA2_TAG = "release-2.0.1"
ARIA2_REPO = "Kenshin9977/aria2"

# QuickJS, compiled from source for Android. Pinned to a commit: the project has no
# releases, and a moving master would make two builds of the same tag differ.
# renovate: datasource=git-refs depName=quickjs packageName=https://github.com/bellard/quickjs currentValue=master
QUICKJS_COMMIT = "04be246001599f5995fa2f2d8c91a0f198d3f34c"
QUICKJS_REPO = "https://github.com/bellard/quickjs"

# The Android NDK the APK is built with.
NDK_VERSION = "27.2.12479018"


if __name__ == "__main__":
    import sys

    print(globals()[sys.argv[1]])
