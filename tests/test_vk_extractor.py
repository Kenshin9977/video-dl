import json
import sys
from unittest.mock import MagicMock, patch

import pytest

for _name in [
    name for name, mod in list(sys.modules.items()) if name.startswith("yt_dlp") and isinstance(mod, MagicMock)
]:
    del sys.modules[_name]

from yt_dlp import YoutubeDL  # noqa: E402
from yt_dlp.extractor.vk import VKIE as UpstreamVKIE  # noqa: E402

from core import vk_extractor  # noqa: E402
from core.vk_extractor import VKIE  # noqa: E402

EMBED_URL = "https://vk.com/video_ext.php?oid=-77521&id=162222515&hash=87b046504ccd8bfa"


def _embed_page(**overrides) -> str:
    """A VK embed page in the shape VK actually serves now: the API response, prefetched."""
    video = {
        "title": "ProtivoGunz &mdash; Хуёвая песня",
        "description": "<b>Видео</b> из официальной группы",
        "duration": 195,
        "date": 1329049880,
        "views": 1234,
        "likes": {"count": 56},
        "image": [{"url": "https://sun.vk.com/small.jpg"}, {"url": "https://sun.vk.com/large.jpg"}],
        "files": {
            "mp4_240": "https://vk.com/240.mp4",
            "mp4_720": "https://vk.com/720.mp4",
            "failover_host": "https://vk.com",
        },
        **overrides,
    }
    blob = json.dumps({"apiPrefetchCache": [{"method": "video.get", "response": {"items": [video]}}]})
    return f"<html><script>window.cur = Object.assign(window.cur || {{}}, {blob});</script></html>"


@pytest.fixture
def extractor():
    ie = VKIE()
    ie.set_downloader(YoutubeDL({"quiet": True}))
    return ie


class TestSeams:
    """Guard what core/vk_extractor.py assumes about yt-dlp."""

    def test_it_still_takes_the_place_of_the_built_in_extractor(self):
        """add_info_extractor replaces by key, and our key has to be the one VK uses."""
        assert VKIE.ie_key() == UpstreamVKIE.ie_key() == "VK"

    def test_the_url_still_tells_an_embed_from_a_normal_video(self):
        groups = VKIE._match_valid_url(EMBED_URL).groupdict()
        assert groups["videoid"] is None
        assert groups["oid"] == "-77521"
        assert groups["id"] == "162222515"
        assert "embed_query" in groups

    def test_registering_puts_ours_in_front(self):
        with YoutubeDL({"quiet": True}) as ydl:
            assert vk_extractor.register(ydl)
            assert isinstance(ydl._ies["VK"], VKIE)


class TestTheNewEmbedPage:
    def test_reads_the_prefetched_api_response(self, extractor):
        with patch.object(VKIE, "_download_webpage", return_value=_embed_page()):
            info = extractor._real_extract(EMBED_URL)

        assert info["id"] == "-77521_162222515"
        assert info["title"] == "ProtivoGunz — Хуёвая песня"
        assert info["description"] == "Видео из официальной группы"
        assert info["duration"] == 195
        assert info["timestamp"] == 1329049880
        assert info["view_count"] == 1234
        assert info["like_count"] == 56
        # The last image is the largest one.
        assert info["thumbnail"] == "https://sun.vk.com/large.jpg"

    def test_builds_the_progressive_formats_and_skips_what_is_not_one(self, extractor):
        with patch.object(VKIE, "_download_webpage", return_value=_embed_page()):
            info = extractor._real_extract(EMBED_URL)

        assert [(f["format_id"], f["height"]) for f in info["formats"]] == [("mp4_240", 240), ("mp4_720", 720)]
        assert all(f["ext"] == "mp4" for f in info["formats"])

    def test_hands_an_old_style_embed_back_to_upstream(self, extractor):
        """No prefetched response means upstream's page, and upstream's error messages."""
        with (
            patch.object(VKIE, "_download_webpage", return_value="<html>an old embed page</html>"),
            patch.object(UpstreamVKIE, "_real_extract", return_value={"id": "upstream"}) as upstream,
        ):
            info = extractor._real_extract(EMBED_URL)

        assert info == {"id": "upstream"}
        upstream.assert_called_once()

    def test_a_normal_video_url_is_upstream_s_business(self, extractor):
        with patch.object(UpstreamVKIE, "_real_extract", return_value={"id": "upstream"}) as upstream:
            info = extractor._real_extract("https://vk.com/video-77521_162222515")

        assert info == {"id": "upstream"}
        upstream.assert_called_once()


class TestRegistration:
    def test_a_broken_extractor_never_takes_the_download_down(self, caplog):
        ydl = MagicMock()
        ydl.add_info_extractor.side_effect = RuntimeError("yt-dlp moved")

        assert vk_extractor.register(ydl) is False
        assert "VK embeds will fail" in caplog.text
