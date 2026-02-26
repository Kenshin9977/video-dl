from __future__ import annotations

from quantiphy import InvalidNumber, Quantity


def parse_speed(d: dict, bytes_fieldname: str) -> str:
    """Format download/process speed as a human-readable string."""
    try:
        raw_speed: float | None = d.get("speed")
        if not raw_speed:
            return "-"
        if bytes_fieldname == "downloaded_bytes":
            return Quantity(raw_speed, "B/s").render(prec=2)
        return Quantity(raw_speed / 8, "B/s").render(prec=2)
    except (InvalidNumber, TypeError):
        return "-"


def parse_quantity(value: float | str | None) -> Quantity | None:
    """Convert a raw byte value to a Quantity, or None if invalid."""
    if value is None:
        return None
    try:
        return Quantity(value, "B")
    except (InvalidNumber, TypeError):
        return None


def compute_progress(
    progress_float: float | None,
    downloaded: Quantity | None,
    total: Quantity | None,
    last_progress_percent: float,
) -> tuple[float, float]:
    """Compute progress bar value and last known percentage."""
    if progress_float is not None:
        return progress_float, last_progress_percent
    try:
        progress_float = downloaded / total  # type: ignore[operator]
        progress_float = max(0, min(progress_float, 0.99))
        return progress_float, progress_float
    except (ZeroDivisionError, TypeError):
        return last_progress_percent, last_progress_percent


def validate_timecode(h_str: str, m_str: str, s_str: str) -> tuple[int, int, int]:
    """Validate h/m/s strings. Returns (h, m, s) or (-1, -1, -1) if invalid."""
    try:
        h_int, m_int, s_int = int(h_str), int(m_str), int(s_str)
    except ValueError:
        return -1, -1, -1
    if m_int >= 60 or s_int >= 60:
        return -1, -1, -1
    return h_int, m_int, s_int


def timecodes_are_valid(
    start_enabled: bool,
    start_hms: tuple[str, str, str],
    end_enabled: bool,
    end_hms: tuple[str, str, str],
) -> bool:
    """Check that enabled timecodes are valid and start < end."""
    if start_enabled:
        sh, sm, ss = validate_timecode(*start_hms)
        if (sh, sm, ss) == (-1, -1, -1):
            return False
    if end_enabled:
        eh, em, es = validate_timecode(*end_hms)
        if (eh, em, es) == (-1, -1, -1):
            return False
    if start_enabled and end_enabled:
        return sh < eh or (sh == eh and sm < em) or (sh == eh and sm == em and ss < es)
    return True
