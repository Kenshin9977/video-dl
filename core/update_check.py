"""Tell Android users when a newer release exists.

The desktop app updates itself (tufup, updater/client.py). An Android app cannot
replace its own APK, and ours is installed from GitHub releases, with no store to
announce new versions, so Android users stayed on whatever they first installed
until someone told them otherwise. This only asks GitHub for the latest release
and compares versions; installing stays with the user and the system installer.

One unauthenticated request per launch: the limit is 60 an hour per IP.
"""

import json
import re
import ssl
import urllib.request

REPO = "Kenshin9977/video-dl"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
LATEST_APK_URL = f"https://github.com/{REPO}/releases/latest/download/video-dl-arm64-v8a.apk"


def version_tuple(version: str) -> tuple[int, ...] | None:
    """(2, 3, 12) for "v2.3.12" or "2.3.12"; None for anything else.

    Numbers, not strings: as strings "2.3.9" sorts after "2.3.12".
    """
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", version.strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def newer_release(current: str, timeout: float = 10) -> str | None:
    """The latest release's version if it is newer than `current`, else None.

    Never raises: no network, a GitHub hiccup or an odd tag just means no banner.
    """
    try:
        import certifi

        # The Python embedded on Android may have no system CA store to find.
        context = ssl.create_default_context(cafile=certifi.where())
        request = urllib.request.Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            tag = json.load(response)["tag_name"]
    except Exception:
        return None
    latest, installed = version_tuple(tag), version_tuple(current)
    if latest and installed and latest > installed:
        return tag.removeprefix("v")
    return None
