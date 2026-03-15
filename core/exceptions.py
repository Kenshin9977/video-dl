import threading

_tls = threading.local()


def mark_v20_blocked() -> None:
    """Record that Chrome v20 cookie decryption was blocked this thread."""
    _tls._v20_blocked = True


def v20_was_blocked() -> bool:
    """Return True if Chrome v20 decryption was blocked on this thread."""
    return getattr(_tls, "_v20_blocked", False)


def reset_v20_flag() -> None:
    """Clear the v20 flag (call before each download attempt)."""
    _tls._v20_blocked = False


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
