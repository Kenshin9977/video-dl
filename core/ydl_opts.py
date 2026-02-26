from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


def build_file_opts(
    *,
    playlist: bool,
    dest_folder: str,
    indices_enabled: bool,
    indices_value: str | None,
    ff_path: dict[str, str],
    progress_hook: Callable[[dict], Any],
    postprocessor_hook: Callable[[dict], Any],
) -> dict[str, Any]:
    """Build yt-dlp file/playlist options."""
    opts: dict[str, Any] = {
        "noplaylist": not playlist,
        "ignoreerrors": "only_download" if playlist else False,
        "overwrites": True,
        "trim_file_name": 250,
        "outtmpl": os.path.join(dest_folder, "%(title).100s - %(uploader)s.%(ext)s"),
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
    }
    if indices_enabled:
        opts["playlist_items"] = indices_value or 1
    if ff_path.get("ffmpeg") != "ffmpeg":
        opts["ffmpeg_location"] = ff_path.get("ffmpeg")
    return opts


def build_av_opts(
    audio_only: bool,
    acodec: str,
    quality: str,
    framerate: str,
) -> dict[str, Any]:
    """Build yt-dlp audio/video format options."""
    opts: dict[str, Any] = {}
    if audio_only:
        format_opt = "ba/ba*"
        if acodec != "Auto":
            format_opt = f"ba[acodec*={acodec}]/{format_opt}"
        postprocessor: dict[str, str] = {"key": "FFmpegExtractAudio"}
        if acodec != "Auto":
            postprocessor["preferredcodec"] = acodec
        opts["extract_audio"] = True
        opts["postprocessors"] = [postprocessor]
    else:
        resolution = quality[:-1] if quality.endswith("p") else quality
        vcodec_re_str = "vcodec~='avc1|h264'"
        acodec_re_str = "acodec~='aac|mp3|mp4a'"
        format_opt = (
            f"((bv[{vcodec_re_str}][height={resolution}]/bv[height={resolution}]/bv)+(ba[{acodec_re_str}]/ba))/b"
        )
        opts["format_sort"] = [f"res:{resolution}", f"fps:{framerate}"]
        opts["merge_output_format"] = "mp4"
    opts["format"] = format_opt
    return opts


def build_original_opts(
    video_id: str | None,
    audio_id: str | None,
    audio_only: bool,
) -> dict[str, Any]:
    """Build yt-dlp options for Original mode with specific stream selection."""
    if audio_only and audio_id:
        format_opt = audio_id
    elif video_id and audio_id:
        format_opt = f"{video_id}+{audio_id}"
    elif video_id:
        format_opt = f"{video_id}+ba"
    elif audio_id:
        format_opt = f"bv+{audio_id}"
    else:
        format_opt = "bv+ba/b"
    return {"format": format_opt, "merge_output_format": "mp4"}


def build_ffmpeg_opts(
    *,
    start_enabled: bool,
    start_timecode: str,
    end_enabled: bool,
    end_timecode: str,
    platform: str,
    ff_path: dict[str, str],
) -> dict[str, Any]:
    """Build yt-dlp FFmpeg trim options."""
    opts: dict[str, Any] = {}
    if start_enabled or end_enabled:
        start = start_timecode if start_enabled else "00:00:00"
        ffmpeg_args = ["-ss", start]
        if end_enabled:
            ffmpeg_args.extend(["-to", end_timecode])
        opts["external_downloader"] = "ffmpeg"
        opts["external_downloader_args"] = {"ffmpeg_i": ffmpeg_args}
        if platform == "Windows":
            opts["ffmpeg_location"] = ff_path.get("ffmpeg")
    return opts


def build_subtitles_opts(enabled: bool) -> dict[str, Any]:
    """Build yt-dlp subtitle options."""
    if enabled:
        return {"subtitleslangs": ["all"], "writesubtitles": True}
    return {}


def build_browser_opts(cookies_value: str | None, none_label: str) -> dict[str, Any]:
    """Build yt-dlp cookie/browser options."""
    if cookies_value and cookies_value != none_label:
        return {"cookiesfrombrowser": [cookies_value.lower()]}
    return {}


def build_sponsor_block_opts(song_only: bool, categories: Any) -> dict[str, Any]:
    """Build yt-dlp SponsorBlock options."""
    if song_only:
        return {
            "postprocessors": [
                {"key": "SponsorBlock", "when": "pre_process"},
                {"key": "ModifyChapters", "SponsorBlock": categories},
            ]
        }
    return {}


def get_effective_vcodec(original_on: bool, vcodec: str | None, nle_ready: bool) -> str:
    """Determine the effective video codec based on user choices."""
    if original_on:
        return "Original"
    if vcodec and vcodec != "Auto":
        return vcodec
    if nle_ready:
        return "NLE"
    return "Best"


def determine_encode_state(original_on: bool, vcodec: str | None, nle_ready: bool) -> tuple[str, str, str, bool]:
    """Determine encode indicator state: (icon, color, state, visible).

    state is "remux", "reencode", or "none".
    """
    if original_on:
        return "check_circle", "green", "remux", True
    if vcodec == "Auto" and not nle_ready:
        return "", "", "none", False
    if vcodec == "Auto" and nle_ready:
        return "check_circle", "green", "remux", True
    return "warning_amber", "orange", "reencode", True


def filter_formats(formats: list[dict]) -> tuple[list[dict], list[dict]]:
    """Filter and organize video/audio formats from yt-dlp format list.

    Returns (video_formats, audio_formats) where each is a list of
    {"format_id": str, "label": str}.
    """
    video_seen: dict[str, dict] = {}
    audio_seen: dict[str, dict] = {}

    for fmt in formats:
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")
        fmt_id = fmt.get("format_id", "")

        if vcodec not in ("none", None):
            height = fmt.get("height") or 0
            key = vcodec.split(".")[0]
            if key not in video_seen or height > video_seen[key]["height"]:
                video_seen[key] = {"format_id": fmt_id, "height": height, "codec": vcodec}

        if acodec not in ("none", None) and vcodec in ("none", None):
            abr = fmt.get("abr") or 0
            key = acodec.split(".")[0]
            if key not in audio_seen or abr > audio_seen[key]["abr"]:
                audio_seen[key] = {"format_id": fmt_id, "abr": abr, "codec": acodec}

    video_formats = []
    for key, v in sorted(video_seen.items(), key=lambda x: x[1]["height"], reverse=True):
        label = f"{key} — {v['height']}p"
        video_formats.append({"format_id": v["format_id"], "label": label})

    audio_formats = []
    for key, a in sorted(audio_seen.items(), key=lambda x: x[1]["abr"], reverse=True):
        abr_str = f"{int(a['abr'])}kbps" if a["abr"] else ""
        label = f"{key} — {abr_str}" if abr_str else key
        audio_formats.append({"format_id": a["format_id"], "label": label})

    return video_formats, audio_formats
