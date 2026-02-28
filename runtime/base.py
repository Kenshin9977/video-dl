from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProcessResult:
    """Platform-agnostic result from a completed process."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Abstraction over subprocess for cross-platform process execution."""

    def run(
        self,
        args: list[str],
        capture_output: bool = False,
        text: bool = False,
        timeout: float | None = None,
    ) -> ProcessResult: ...

    def popen_communicate(
        self,
        args: list[str],
    ) -> ProcessResult:
        """Run a process and wait for completion, capturing stdout/stderr."""
        ...


class PlatformPaths(Protocol):
    """Platform-specific path resolution."""

    def get_config_dir(self) -> str: ...

    def get_default_download_dir(self) -> str: ...

    def open_folder(self, path: str) -> None: ...
