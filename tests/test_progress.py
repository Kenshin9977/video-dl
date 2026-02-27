from __future__ import annotations

import pytest
from core.progress import compute_progress, parse_quantity, parse_speed, timecodes_are_valid, validate_timecode
from quantiphy import Quantity


class TestParseSpeed:
    def test_download_bytes(self):
        result = parse_speed({"speed": 1_000_000}, "downloaded_bytes")
        assert "B/s" in result
        assert result != "-"

    def test_process_bytes_divides_by_8(self):
        result = parse_speed({"speed": 800}, "processed_bytes")
        # 800 / 8 = 100 B/s
        assert "100" in result

    def test_none_speed_returns_dash(self):
        assert parse_speed({"speed": None}, "downloaded_bytes") == "-"

    def test_zero_speed_returns_dash(self):
        assert parse_speed({"speed": 0}, "downloaded_bytes") == "-"

    def test_missing_speed_returns_dash(self):
        assert parse_speed({}, "downloaded_bytes") == "-"


class TestParseQuantity:
    def test_valid_bytes(self):
        q = parse_quantity(1024)
        assert isinstance(q, Quantity)

    def test_none_returns_none(self):
        assert parse_quantity(None) is None

    def test_invalid_returns_none(self):
        assert parse_quantity("not_a_number") is None


class TestComputeProgress:
    def test_progress_float_provided(self):
        result = compute_progress(0.5, None, None, 0.3)
        assert result == (0.5, 0.3)

    def test_calculated_from_downloaded_total(self):
        downloaded = Quantity(50, "B")
        total = Quantity(100, "B")
        progress, last = compute_progress(None, downloaded, total, 0.0)
        assert progress == 0.5
        assert last == 0.5

    def test_clamped_to_099(self):
        downloaded = Quantity(200, "B")
        total = Quantity(100, "B")
        progress, _ = compute_progress(None, downloaded, total, 0.0)
        assert progress == 0.99

    def test_zero_total_returns_last(self):
        downloaded = Quantity(50, "B")
        total = Quantity(0, "B")
        progress, last = compute_progress(None, downloaded, total, 0.42)
        assert progress == 0.42
        assert last == 0.42

    def test_none_total_returns_last(self):
        progress, last = compute_progress(None, None, None, 0.7)
        assert progress == 0.7
        assert last == 0.7


class TestValidateTimecode:
    def test_valid(self):
        assert validate_timecode("1", "30", "45") == (1, 30, 45)

    def test_zero(self):
        assert validate_timecode("0", "0", "0") == (0, 0, 0)

    def test_minutes_too_high(self):
        assert validate_timecode("0", "60", "0") == (-1, -1, -1)

    def test_seconds_too_high(self):
        assert validate_timecode("0", "0", "60") == (-1, -1, -1)

    def test_non_numeric(self):
        assert validate_timecode("a", "0", "0") == (-1, -1, -1)


class TestTimecodesAreValid:
    def test_both_disabled(self):
        assert timecodes_are_valid(False, ("0", "0", "0"), False, ("0", "0", "0")) is True

    def test_start_only_valid(self):
        assert timecodes_are_valid(True, ("0", "1", "0"), False, ("0", "0", "0")) is True

    def test_start_only_invalid(self):
        assert timecodes_are_valid(True, ("a", "0", "0"), False, ("0", "0", "0")) is False

    def test_end_only_valid(self):
        assert timecodes_are_valid(False, ("0", "0", "0"), True, ("0", "5", "0")) is True

    def test_end_only_invalid(self):
        assert timecodes_are_valid(False, ("0", "0", "0"), True, ("0", "60", "0")) is False

    def test_start_before_end(self):
        assert timecodes_are_valid(True, ("0", "1", "0"), True, ("0", "2", "0")) is True

    def test_start_equals_end(self):
        assert timecodes_are_valid(True, ("0", "1", "0"), True, ("0", "1", "0")) is False

    def test_start_after_end(self):
        assert timecodes_are_valid(True, ("0", "5", "0"), True, ("0", "2", "0")) is False

    @pytest.mark.parametrize(
        ("start_hms", "end_hms"),
        [
            (("0", "0", "0"), ("0", "0", "1")),  # seconds differ
            (("0", "0", "0"), ("0", "1", "0")),  # minutes differ
            (("0", "0", "0"), ("1", "0", "0")),  # hours differ
        ],
    )
    def test_start_less_than_end_edge_cases(self, start_hms, end_hms):
        assert timecodes_are_valid(True, start_hms, True, end_hms) is True
