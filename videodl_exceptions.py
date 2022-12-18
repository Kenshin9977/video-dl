class DownloadCancelled(Exception):
    "Raised when the download is cancelled"
    pass


class FFmpegNoValidEncoderFound(Exception):
    "Raised when no valid encoder is found"
    pass
