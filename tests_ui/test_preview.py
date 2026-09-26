"""Paste a link and see what it is."""

import pytest
from ui import enter_url, exact, wait_for, wait_gone

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_a_link_shows_its_title_and_length(tester, server):
    await enter_url(tester, f"{server}/sample.mp4")
    await wait_for(tester, exact("sample"))


async def test_a_dead_link_does_not_leave_the_preview_spinning(tester, server):
    await enter_url(tester, f"{server}/nothing-here.mp4")
    await wait_gone(tester, "Fetching video info")
