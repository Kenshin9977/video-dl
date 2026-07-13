"""Teach yt-dlp to read VK's new embed page.

VK stopped putting `playerParams` in its embed pages (`video_ext.php`) and now
prefetches the API response into `window.cur.apiPrefetchCache`. Upstream yt-dlp
still looks for `playerParams`, so every VK embed fails. The fix is Kenshin9977's,
sitting in yt-dlp PR #16066, open since February.

It used to reach video-dl through a fork of the whole of yt-dlp. It reaches it here
through `YoutubeDL.add_info_extractor`, which replaces an extractor by its key: the
subclass below is named VKIE, so its key is VK, so it takes the built-in one's place.

Not through yt-dlp's plugin system, deliberately. That loader scans sys.path for
real directories named `yt_dlp_plugins`, and inside a PyInstaller binary this code
lives in an archive, not on disk. The plugin would work in development and silently
vanish from the release, which is the worst of both worlds.

Only the embed path is overridden. Everything else, including every error message
and every other kind of VK URL, is still upstream's job: a subclass that copied
`_real_extract` wholesale would rot against every yt-dlp release.
"""

from __future__ import annotations

import logging

from yt_dlp.extractor.vk import VKIE as UpstreamVKIE
from yt_dlp.utils import clean_html, int_or_none, unescapeHTML, url_or_none
from yt_dlp.utils.traversal import traverse_obj

logger = logging.getLogger("videodl")

# The blob VK now prefetches the API response into.
_API_CACHE = r"window\.cur\s*=\s*Object\.assign\(window\.cur\s*\|\|\s*\{\}\s*,"


class VKIE(UpstreamVKIE):  # type: ignore[misc, valid-type]
    def _real_extract(self, url):
        match = self._match_valid_url(url)

        # Only the embed page changed. Anything with a video id is upstream's.
        if match.group("videoid"):
            return super()._real_extract(url)

        info = self._extract_from_api_cache(url, match)
        if info:
            return info

        # No prefetched API response: an older embed page, or an error page. Let
        # upstream have it, so its error messages are the ones the user sees.
        return super()._real_extract(url)

    def _extract_from_api_cache(self, url, match):
        video_id = "{}_{}".format(match.group("oid"), match.group("id"))
        page = self._download_webpage("https://vk.com/video_ext.php?" + match.group("embed_query"), video_id)

        api_data = traverse_obj(
            self._search_json(_API_CACHE, page, "api data", video_id, default=None),
            ("apiPrefetchCache", lambda _, v: v["method"] == "video.get", "response", "items", 0, any),
        )
        if not api_data:
            return None

        formats, subtitles = self._extract_formats(api_data, video_id)
        return {
            "id": video_id,
            "formats": formats,
            "subtitles": subtitles,
            **traverse_obj(
                api_data,
                {
                    "title": ("title", {str}, {unescapeHTML}),
                    "description": ("description", {clean_html}, filter),
                    "thumbnail": ("image", -1, "url", {url_or_none}),
                    "duration": ("duration", {int_or_none}),
                    "timestamp": ("date", {int_or_none}),
                    "view_count": ("views", {int_or_none}),
                    "like_count": ("likes", "count", {int_or_none}),
                },
            ),
        }

    def _extract_formats(self, api_data, video_id):
        formats: list[dict] = []
        subtitles: dict = {}

        for format_id, raw_url in (api_data.get("files") or {}).items():
            format_url = url_or_none(raw_url)
            if not format_url:
                continue

            if format_id.startswith("mp4_"):
                formats.append(
                    {
                        "format_id": format_id,
                        "url": format_url,
                        "ext": "mp4",
                        "height": int_or_none(format_id[4:]),
                    }
                )
            elif format_id.startswith("hls"):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, "mp4", "m3u8_native", m3u8_id=format_id, fatal=False
                )
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif format_id.startswith("dash"):
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id=format_id, fatal=False
                )
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

        return formats, subtitles


def register(ydl) -> bool:
    """Put our VK extractor in the built-in one's place. Never fails the download."""
    try:
        ydl.add_info_extractor(VKIE())
    except Exception as e:
        logger.warning(f"could not install the VK extractor, VK embeds will fail: {e}")
        return False
    return True
