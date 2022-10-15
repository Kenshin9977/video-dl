from unittest.mock import MagicMock

from pytest_mock import MockFixture
import pytest
from gui import _run_video_dl


@pytest.mark.parametrize(
    ("expected_call_count", "values"),
    (
        (1, {"Start": False, "End": True}),
        (1, {"Start": True, "End": False}),
        (1, {"Start": False, "End": False}),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "00",
                "eM": "00",
                "eS": "01",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "00",
                "eM": "01",
                "eS": "00",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "01",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "00",
                "eM": "01",
                "eS": "01",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "01",
                "eM": "00",
                "eS": "01",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "01",
                "eM": "01",
                "eS": "00",
            },
        ),
        (
            1,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "01",
                "eM": "01",
                "eS": "01",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "00",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "00",
                "sS": "01",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "01",
                "sS": "00",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "01",
                "sM": "00",
                "sS": "00",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "00",
                "sM": "01",
                "sS": "01",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "01",
                "sM": "00",
                "sS": "01",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "01",
                "sM": "01",
                "sS": "00",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
        (
            0,
            {
                "Start": True,
                "End": True,
                "sH": "01",
                "sM": "01",
                "sS": "01",
                "eH": "00",
                "eM": "00",
                "eS": "00",
            },
        ),
    ),
    ids=(
        "no start",
        "no end",
        "no end and no start",
        "end_s_sup_start",
        "end_m_sup_start",
        "end_h_sup_start",
        "end_ms_sup_start",
        "end_hs_sup_start",
        "end_hm_sup_start",
        "end_hms_sup_start",
        "end_eq_start",
        "end_s_inf_start",
        "end_m_inf_start",
        "end_h_inf_start",
        "end_ms_inf_start",
        "end_hs_inf_start",
        "end_hm_inf_start",
        "end_hms_inf_start",
    ),
)
def test_timecodes(
    mocker: MockFixture, expected_call_count: int, values: dict
):
    values["path"] = "/"
    video_dl = mocker.patch("gui.video_dl")
    _run_video_dl({"error": MagicMock()}, values)
    assert video_dl.call_count == expected_call_count


@pytest.mark.parametrize(
    ("expected_call_count", "values"),
    (
        (0, {"path": ""}),
        (0, {"path": None}),
        (0, {}),
        (0, {"path": "dummy"}),
        (1, {"path": "/"}),
    ),
    ids=(
        "no_path_given",
        "path_is_none",
        "no_path_key",
        "invalid_path_given",
        "path_given",
    ),
)
def test_path(mocker: MockFixture, expected_call_count: int, values: dict):
    video_dl = mocker.patch("gui.video_dl")
    _run_video_dl({"error": MagicMock()}, values)
    assert video_dl.call_count == expected_call_count
