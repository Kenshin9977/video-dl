import pytest


@pytest.mark.asyncio
async def test_the_window_opens(flet_app):
    tester = flet_app.tester
    assert (await tester.find_by_key("media_link")).count == 1
    assert (await tester.find_by_text("Download")).count == 1


@pytest.mark.asyncio
async def test_an_invalid_url_is_refused(flet_app):
    tester = flet_app.tester
    await tester.enter_text(await tester.find_by_key("media_link"), "not a url")
    await tester.pump_and_settle()
    assert (await tester.find_by_tooltip("Enter a valid URL")).count >= 1 or (
        await tester.find_by_text_containing("valid URL")
    ).count >= 1
