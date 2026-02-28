from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DownloadConfig:
    """All user options needed by the download/encode pipeline.

    Populated by the GUI, consumed by core functions.
    """

    url: str
    audio_only: bool
    target_vcodec: str  # "Best", "NLE", "Original", "x264", etc.
    ff_path: dict[str, str] = field(default_factory=dict)
    ydl_opts: dict = field(default_factory=dict)
