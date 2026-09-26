"""Put the Flet desktop client inside the frozen app, the way flet 0.81 did.

From 0.83 the flet-desktop wheel no longer carries the client. Left alone, the
frozen app downloads it (tens of MB) from GitHub on first launch and runs it, and
a machine with no network gets no window at all. v2.3.10 shipped exactly that.

flet still looks for a client archive in flet_desktop/app/ before it downloads
anything (flet_desktop.ensure_client_cached), which is how `flet pack` bundles it.
This fetches the archive for the Flet version installed here, checks it against
the SHA-256 GitHub publishes for that release asset, and hands it to PyInstaller
as data for flet_desktop/app/.

Called from the specs; also runnable on its own to warm the cache.
"""

import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "build" / "flet-client"


def _github(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    # Runners share IPs, and unauthenticated API calls are capped at 60 an hour.
    if token := os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(request, timeout=60)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bundled_flet_client() -> list[tuple[str, str]]:
    """The PyInstaller `datas` entry that bundles the Flet client for this platform."""
    import flet_desktop
    from flet_desktop.version import version

    artifact = flet_desktop.get_artifact_filename()
    with _github(f"https://api.github.com/repos/flet-dev/flet/releases/tags/v{version}") as response:
        assets = {asset["name"]: asset for asset in json.load(response)["assets"]}
    if artifact not in assets:
        raise SystemExit(f"flet v{version} has no release asset named {artifact}")
    asset = assets[artifact]
    algorithm, _, expected = (asset.get("digest") or "").partition(":")
    if algorithm != "sha256" or not expected:
        raise SystemExit(f"GitHub published no SHA-256 for {artifact}; refusing to bundle it unchecked")

    target = CACHE / version / artifact
    if not target.exists() or _sha256(target) != expected:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        with urllib.request.urlopen(asset["browser_download_url"], timeout=300) as response, partial.open("wb") as f:
            shutil.copyfileobj(response, f)
        if (actual := _sha256(partial)) != expected:
            partial.unlink()
            raise SystemExit(f"{artifact}: SHA-256 {actual} does not match the published {expected}")
        partial.replace(target)
    print(f"Bundling the Flet client: {target}")
    return [(str(target), "flet_desktop/app")]


if __name__ == "__main__":
    bundled_flet_client()
