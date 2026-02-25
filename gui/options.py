from i18n.lang import GuiField as GF
from i18n.lang import get_text as gt

FRAMERATE = ["30", "60"]
BROWSERS = [
    gt(GF.login_from_none),
    "Brave",
    "Chrome",
    "Chromium",
    "Edge",
    "Firefox",
    "Opera",
    "Safari",
    "Vivaldi",
]
QUALITY = [
    "4320p",
    "2160p",
    "1440p",
    "1080p",
    "720p",
    "480p",
    "360p",
    "240p",
    "144p",
]
VCODECS = ["Auto", "x264", "x265", "ProRes", "AV1"]
ACODECS = ["Auto", "AAC", "ALAC", "FLAC", "OPUS", "MP3", "VORBIS", "WAV"]
