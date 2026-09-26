import pytest
from ui import exact, wait_for, wait_gone

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_the_queue_keeps_only_valid_links(tester, server):
    await tester.tap(await tester.find_by_tooltip("Add URLs to queue"))
    await wait_for(tester, exact("Download queue"))
    await tester.enter_text(
        await tester.find_by_key("queue_urls"), f"{server}/sample.mp4\nnot a url\n{server}/sample.mp4?2"
    )
    await tester.tap(await tester.find_by_text("OK"))
    await wait_gone(tester, exact("Download queue"))
    await wait_for(tester, exact("2"))

    await tester.tap(await tester.find_by_tooltip("Add URLs to queue"))
    await wait_for(tester, exact("Download queue"))
    await tester.tap(await tester.find_by_text("Clear"))
    await tester.tap(await tester.find_by_text("OK"))
    await wait_gone(tester, exact("Download queue"))
