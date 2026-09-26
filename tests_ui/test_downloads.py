"""Download it, change your mind, watch it fail.

Not blocking in CI yet. Every assertion here passes, but a run that downloads
makes the Flutter side of `flet test` fail now and then with no exception printed,
only on non-verbose runs. Until that is understood (flet 0.86 harness, likely to
move with the flet 1.x migration), the UI workflow runs this file as its own
allowed-to-fail job, so the rest of the suite can gate.
"""

import pytest
from ui import enter_url, exact, wait_for, wait_for_file, wait_gone, wait_idle

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_a_download_lands_on_disk(tester, server, download_dir):
    await enter_url(tester, f"{server}/sample.mp4")
    await tester.tap(await tester.find_by_key("download_button"))
    await wait_for_file(tester, download_dir, {".mp4"})
    await wait_for(tester, exact("Download finished."))
    await wait_idle(tester)


async def test_cancel_stops_a_download(tester, server):
    await enter_url(tester, f"{server}/slow.mp4")
    await tester.tap(await tester.find_by_key("download_button"))
    await wait_for(tester, r"^Download \d+%")
    await tester.tap(await tester.find_by_text("Cancel"))
    await wait_for(tester, exact("Download cancelled."))
    await wait_idle(tester)


async def test_a_failed_download_explains_itself(tester, server):
    await enter_url(tester, f"{server}/nothing-here.mp4")
    await tester.tap(await tester.find_by_key("download_button"))
    await wait_for(tester, "HTTP Error 404")
    await tester.tap(await tester.find_by_tooltip("Click for details"))
    await wait_for(tester, exact("Open log"))
    assert (await tester.find_by_text("Copy")).count == 1
    await tester.tap(await tester.find_by_text("Close"))
    await wait_gone(tester, exact("Open log"))


async def test_audio_only_keeps_just_the_sound(tester, server, download_dir):
    await tester.tap(await tester.find_by_text("Audio only"))
    try:
        await enter_url(tester, f"{server}/sample.mp4")
        await tester.tap(await tester.find_by_key("download_button"))
        await wait_for_file(tester, download_dir, {".m4a", ".mp3", ".aac", ".opus", ".ogg"})
        # Let it finish post-processing: until then the controls stay disabled.
        await wait_for(tester, exact("Download finished."))
        await wait_idle(tester)
        assert not [f for f in download_dir.iterdir() if f.suffix == ".mp4"]
    finally:
        await tester.tap(await tester.find_by_text("Audio only"))
