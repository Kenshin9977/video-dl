from __future__ import annotations

from typing import Protocol


class ProgressCallback(Protocol):
    """Called by download/encode to report progress updates."""

    def on_download_progress(self, status: dict) -> None: ...
    def on_process_progress(self, status: dict) -> None: ...


class CancelToken(Protocol):
    """Checked by download/encode to see if cancellation was requested."""

    def is_cancelled(self) -> bool: ...


class StatusCallback(Protocol):
    """Called to update status text (e.g. 'Extracting cookies...')."""

    def on_status(self, message: str) -> None: ...
