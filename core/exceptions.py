class DownloadCancelled(Exception):
    "Raised when the download is cancelled"

    pass


class FFmpegNoValidEncoderFound(Exception):
    "Raised when no valid encoder is found"

    pass


class DownloadTimeout(Exception):
    "Raised when extract_info times out after all retries"

    def __init__(self, url: str = ""):
        self.url = url
        super().__init__(f"Download timed out for {url}")


class PlaylistNotFound(Exception):
    "Raised when the playlist doesn't seem to exist"

    pass
