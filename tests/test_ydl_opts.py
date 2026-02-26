from __future__ import annotations

from core.ydl_opts import (
    build_av_opts,
    build_browser_opts,
    build_ffmpeg_opts,
    build_file_opts,
    build_original_opts,
    build_sponsor_block_opts,
    build_subtitles_opts,
    determine_encode_state,
    filter_formats,
    get_effective_vcodec,
)


class TestBuildFileOpts:
    def _hook(self, d):
        pass

    def test_playlist_off(self):
        opts = build_file_opts(
            playlist=False,
            dest_folder="/tmp",
            indices_enabled=False,
            indices_value=None,
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["noplaylist"] is True
        assert opts["ignoreerrors"] is False

    def test_playlist_on(self):
        opts = build_file_opts(
            playlist=True,
            dest_folder="/tmp",
            indices_enabled=False,
            indices_value=None,
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["noplaylist"] is False
        assert opts["ignoreerrors"] == "only_download"

    def test_indices_enabled(self):
        opts = build_file_opts(
            playlist=True,
            dest_folder="/tmp",
            indices_enabled=True,
            indices_value="1-5",
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["playlist_items"] == "1-5"

    def test_indices_enabled_no_value_defaults_to_1(self):
        opts = build_file_opts(
            playlist=True,
            dest_folder="/tmp",
            indices_enabled=True,
            indices_value=None,
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["playlist_items"] == 1

    def test_custom_ffmpeg_location(self):
        opts = build_file_opts(
            playlist=False,
            dest_folder="/tmp",
            indices_enabled=False,
            indices_value=None,
            ff_path={"ffmpeg": "/usr/local/bin/ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["ffmpeg_location"] == "/usr/local/bin/ffmpeg"

    def test_default_ffmpeg_no_location(self):
        opts = build_file_opts(
            playlist=False,
            dest_folder="/tmp",
            indices_enabled=False,
            indices_value=None,
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert "ffmpeg_location" not in opts

    def test_outtmpl_uses_dest_folder(self):
        opts = build_file_opts(
            playlist=False,
            dest_folder="/my/path",
            indices_enabled=False,
            indices_value=None,
            ff_path={"ffmpeg": "ffmpeg"},
            progress_hook=self._hook,
            postprocessor_hook=self._hook,
        )
        assert opts["outtmpl"].startswith("/my/path")


class TestBuildAvOpts:
    def test_audio_only_auto_codec(self):
        opts = build_av_opts(audio_only=True, acodec="Auto", quality="1080p", framerate="60")
        assert opts["format"] == "ba/ba*"
        assert opts["extract_audio"] is True
        assert opts["postprocessors"][0]["key"] == "FFmpegExtractAudio"
        assert "preferredcodec" not in opts["postprocessors"][0]

    def test_audio_only_specific_codec(self):
        opts = build_av_opts(audio_only=True, acodec="mp3", quality="1080p", framerate="60")
        assert "acodec*=mp3" in opts["format"]
        assert opts["postprocessors"][0]["preferredcodec"] == "mp3"

    def test_video_mode(self):
        opts = build_av_opts(audio_only=False, acodec="Auto", quality="1080p", framerate="60")
        assert "height=1080" in opts["format"]
        assert opts["merge_output_format"] == "mp4"
        assert opts["format_sort"] == ["res:1080", "fps:60"]

    def test_video_720p_30fps(self):
        opts = build_av_opts(audio_only=False, acodec="Auto", quality="720p", framerate="30")
        assert "height=720" in opts["format"]
        assert opts["format_sort"] == ["res:720", "fps:30"]


class TestBuildOriginalOpts:
    def test_video_and_audio(self):
        opts = build_original_opts(video_id="137", audio_id="140", audio_only=False)
        assert opts["format"] == "137+140"
        assert opts["merge_output_format"] == "mp4"

    def test_audio_only_with_audio_id(self):
        opts = build_original_opts(video_id="137", audio_id="140", audio_only=True)
        assert opts["format"] == "140"

    def test_video_only(self):
        opts = build_original_opts(video_id="137", audio_id=None, audio_only=False)
        assert opts["format"] == "137+ba"

    def test_audio_id_only(self):
        opts = build_original_opts(video_id=None, audio_id="140", audio_only=False)
        assert opts["format"] == "bv+140"

    def test_no_ids_fallback(self):
        opts = build_original_opts(video_id=None, audio_id=None, audio_only=False)
        assert opts["format"] == "bv+ba/b"


class TestBuildFfmpegOpts:
    def test_no_trim(self):
        opts = build_ffmpeg_opts(
            start_enabled=False,
            start_timecode="00:00:00",
            end_enabled=False,
            end_timecode="00:00:00",
            platform="Darwin",
            ff_path={"ffmpeg": "ffmpeg"},
        )
        assert opts == {}

    def test_start_only(self):
        opts = build_ffmpeg_opts(
            start_enabled=True,
            start_timecode="00:01:30",
            end_enabled=False,
            end_timecode="00:00:00",
            platform="Darwin",
            ff_path={"ffmpeg": "ffmpeg"},
        )
        assert opts["external_downloader"] == "ffmpeg"
        assert opts["external_downloader_args"] == {"ffmpeg_i": ["-ss", "00:01:30"]}

    def test_end_only(self):
        opts = build_ffmpeg_opts(
            start_enabled=False,
            start_timecode="00:00:00",
            end_enabled=True,
            end_timecode="00:05:00",
            platform="Darwin",
            ff_path={"ffmpeg": "ffmpeg"},
        )
        assert opts["external_downloader_args"] == {"ffmpeg_i": ["-ss", "00:00:00", "-to", "00:05:00"]}

    def test_start_and_end(self):
        opts = build_ffmpeg_opts(
            start_enabled=True,
            start_timecode="00:01:00",
            end_enabled=True,
            end_timecode="00:05:00",
            platform="Darwin",
            ff_path={"ffmpeg": "ffmpeg"},
        )
        assert opts["external_downloader_args"] == {"ffmpeg_i": ["-ss", "00:01:00", "-to", "00:05:00"]}

    def test_windows_adds_ffmpeg_location(self):
        opts = build_ffmpeg_opts(
            start_enabled=True,
            start_timecode="00:01:00",
            end_enabled=False,
            end_timecode="00:00:00",
            platform="Windows",
            ff_path={"ffmpeg": "C:\\ffmpeg.exe"},
        )
        assert opts["ffmpeg_location"] == "C:\\ffmpeg.exe"

    def test_non_windows_no_ffmpeg_location(self):
        opts = build_ffmpeg_opts(
            start_enabled=True,
            start_timecode="00:01:00",
            end_enabled=False,
            end_timecode="00:00:00",
            platform="Darwin",
            ff_path={"ffmpeg": "/usr/bin/ffmpeg"},
        )
        assert "ffmpeg_location" not in opts


class TestBuildSubtitlesOpts:
    def test_enabled(self):
        opts = build_subtitles_opts(True)
        assert opts["subtitleslangs"] == ["all"]
        assert opts["writesubtitles"] is True

    def test_disabled(self):
        assert build_subtitles_opts(False) == {}


class TestBuildBrowserOpts:
    def test_with_browser(self):
        opts = build_browser_opts("Chrome", "None")
        assert opts["cookiesfrombrowser"] == ["chrome"]

    def test_none_label_returns_empty(self):
        assert build_browser_opts("None", "None") == {}

    def test_empty_returns_empty(self):
        assert build_browser_opts(None, "None") == {}


class TestBuildSponsorBlockOpts:
    def test_enabled(self):
        categories = ["sponsor", "selfpromo"]
        opts = build_sponsor_block_opts(True, categories)
        assert len(opts["postprocessors"]) == 2
        assert opts["postprocessors"][0]["key"] == "SponsorBlock"
        assert opts["postprocessors"][1]["key"] == "ModifyChapters"

    def test_disabled(self):
        assert build_sponsor_block_opts(False, []) == {}


class TestGetEffectiveVcodec:
    def test_original(self):
        assert get_effective_vcodec(True, "Auto", False) == "Original"

    def test_specific_codec(self):
        assert get_effective_vcodec(False, "h264", False) == "h264"

    def test_nle_ready(self):
        assert get_effective_vcodec(False, None, True) == "NLE"

    def test_auto_no_nle(self):
        assert get_effective_vcodec(False, "Auto", False) == "Best"

    def test_best_fallback(self):
        assert get_effective_vcodec(False, None, False) == "Best"


class TestDetermineEncodeState:
    def test_original_remux(self):
        icon, color, state, visible = determine_encode_state(True, "Auto", False)
        assert icon == "check_circle"
        assert color == "green"
        assert state == "remux"
        assert visible is True

    def test_auto_no_nle_hidden(self):
        icon, color, state, visible = determine_encode_state(False, "Auto", False)
        assert visible is False

    def test_auto_nle_remux(self):
        icon, color, state, visible = determine_encode_state(False, "Auto", True)
        assert icon == "check_circle"
        assert color == "green"
        assert state == "remux"
        assert visible is True

    def test_specific_codec_reencode(self):
        icon, color, state, visible = determine_encode_state(False, "h264", False)
        assert icon == "warning_amber"
        assert color == "orange"
        assert state == "reencode"
        assert visible is True


class TestFilterFormats:
    def test_basic_filtering(self):
        formats = [
            {"vcodec": "avc1.640028", "acodec": "none", "format_id": "137", "height": 1080},
            {"vcodec": "vp9", "acodec": "none", "format_id": "248", "height": 1080},
            {"vcodec": "none", "acodec": "mp4a.40.2", "format_id": "140", "abr": 128},
            {"vcodec": "none", "acodec": "opus", "format_id": "251", "abr": 160},
        ]
        video, audio = filter_formats(formats)
        assert len(video) == 2
        assert len(audio) == 2

    def test_deduplication_keeps_highest_quality(self):
        formats = [
            {"vcodec": "avc1.640028", "acodec": "none", "format_id": "134", "height": 360},
            {"vcodec": "avc1.640028", "acodec": "none", "format_id": "137", "height": 1080},
        ]
        video, audio = filter_formats(formats)
        assert len(video) == 1
        assert video[0]["format_id"] == "137"
        assert "1080p" in video[0]["label"]

    def test_audio_deduplication_keeps_highest_bitrate(self):
        formats = [
            {"vcodec": "none", "acodec": "mp4a.40.2", "format_id": "139", "abr": 48},
            {"vcodec": "none", "acodec": "mp4a.40.2", "format_id": "140", "abr": 128},
        ]
        video, audio = filter_formats(formats)
        assert len(audio) == 1
        assert audio[0]["format_id"] == "140"

    def test_mixed_av_formats_excluded_from_audio(self):
        formats = [
            {"vcodec": "avc1", "acodec": "mp4a", "format_id": "18", "height": 360, "abr": 96},
        ]
        video, audio = filter_formats(formats)
        assert len(video) == 1
        assert len(audio) == 0

    def test_empty_formats(self):
        video, audio = filter_formats([])
        assert video == []
        assert audio == []

    def test_sorted_by_quality_descending(self):
        formats = [
            {"vcodec": "avc1", "acodec": "none", "format_id": "134", "height": 360},
            {"vcodec": "vp9", "acodec": "none", "format_id": "248", "height": 1080},
        ]
        video, _ = filter_formats(formats)
        assert "1080p" in video[0]["label"]
        assert "360p" in video[1]["label"]
