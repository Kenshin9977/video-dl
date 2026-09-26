"""Helpers the UI tests share. The fixtures live in conftest.py."""

import asyncio
import re
import time
from pathlib import Path

import pytest

# Everything the app does in these tests is local and small: a 3-second clip over
# localhost. A few seconds is plenty, and a short wait is what keeps a red run from
# taking twenty minutes.
TIMEOUT = 10

# A failed wait saves what the window showed at that moment. build/ is ignored by git.
SCREENSHOTS = Path("build/ui-screenshots")


async def _fail(message: str) -> None:
    # flet only screenshots the app itself on Android and iOS, so grab the whole
    # screen. Best effort: a missing screenshot must never hide the real failure.
    shot = SCREENSHOTS / f"{re.sub(r'[^A-Za-z0-9]+', '_', message)[:80]}.png"
    try:
        from PIL import ImageGrab

        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab().save(shot)
        message += f" (screenshot: {shot})"
    except Exception as e:
        message += f" (no screenshot: {e})"
    pytest.fail(message)


async def wait_for(tester, pattern: str, timeout: float = TIMEOUT) -> None:
    """Pump the UI until some text matching `pattern` shows, or fail."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await tester.pump()
        if (await tester.find_by_text_containing(pattern)).count:
            return
        await asyncio.sleep(0.25)
    await _fail(f"nothing matching {pattern!r} showed within {timeout:.0f}s")


async def wait_gone(tester, pattern: str, timeout: float = TIMEOUT) -> None:
    """Pump the UI until no text matches `pattern` any more, or fail."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await tester.pump()
        if not (await tester.find_by_text_containing(pattern)).count:
            return
        await asyncio.sleep(0.25)
    await _fail(f"{pattern!r} was still showing after {timeout:.0f}s")


async def enter_url(tester, url: str) -> None:
    """Type `url` into the link field, and check it took.

    The app disables the field while it downloads, and typing into a disabled field
    is silently ignored: the next test then downloads the previous test's link.
    Fail here instead.
    """
    await tester.enter_text(await tester.find_by_key("media_link"), url)
    await tester.pump_and_settle()
    if not (await tester.find_by_text(url)).count:
        await _fail(f"the link field did not take {url!r}; is a download still running?")


def exact(text: str) -> str:
    return f"^{re.escape(text)}$"


async def wait_for_file(tester, folder: Path, suffixes: set[str], timeout: float = 15) -> Path:
    """Wait for a finished file with one of `suffixes` in `folder`, or fail.

    Watching the disk rather than the status line: the app is shared between tests,
    so "Download finished." can still be on screen from the previous one.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await tester.pump()
        done = [f for f in folder.iterdir() if f.suffix in suffixes and not f.name.endswith(".part")]
        if done:
            return done[0]
        await asyncio.sleep(0.25)
    await _fail(
        f"no {sorted(suffixes)} file in {folder} after {timeout:.0f}s: {sorted(f.name for f in folder.iterdir())}"
    )
    raise AssertionError  # unreachable, pytest.fail raises
