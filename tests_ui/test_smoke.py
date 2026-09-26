import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_the_window_opens(tester):
    assert (await tester.find_by_key("media_link")).count == 1
    assert (await tester.find_by_key("download_button")).count == 1


async def test_an_invalid_url_is_refused(tester):
    await tester.enter_text(await tester.find_by_key("media_link"), "not a url")
    await tester.pump_and_settle()
    assert (await tester.find_by_tooltip("Enter a valid URL")).count == 1
