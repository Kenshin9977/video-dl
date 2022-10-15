from unittest.mock import MagicMock, patch

from pytest_mock import MockFixture
import pytest
from gen_new_version import GenUpdate


@pytest.mark.parametrize(
    ("expected_result", "current_version"),
    (
        (False, "0.0.0"),
        (False, "0.0.1"),
        (False, "0.0.2"),
        (False, "0.1.0"),
        (False, "0.1.1"),
        (False, "0.1.2"),
        (False, "0.2.0"),
        (False, "0.2.1"),
        (False, "0.2.2"),
        (False, "1.0.0"),
        (False, "1.0.1"),
        (False, "1.0.2"),
        (False, "1.1.0"),
        (False, "1.1.1"),
        (True, "1.1.2"),
        (True, "1.2.0"),
        (True, "1.2.1"),
        (True, "1.2.2"),
        (True, "2.0.0"),
        (True, "2.0.1"),
        (True, "2.0.2"),
        (True, "2.1.0"),
        (True, "2.1.1"),
        (True, "2.1.2"),
        (True, "2.2.0"),
        (True, "2.2.1"),
        (True, "2.2.2"),
    ),
    ids=(
        "major_minor_patch_lt",
        "patch_eq_major_minor_lt",
        "patch_ht_major_minor_lt",
        "minor_eq_major_patch_lt",
        "minor_patch_eq_major_lt",
        "patch_ht_minor_eq_major_lt",
        "minor_ht_major_patch_lt",
        "minor_ht_patch_eq_major_lt",
        "minor_patch_ht_major_lt",
        "major_eq_minor_patch_lt",
        "major_patch_eq_minor_lt",
        "patch_ht_major_eq_minor_lt",
        "major_minor_eq_patch_lt",
        "major_minor_patch_eq",
        "patch_ht_major_minor_eq",
        "minor_ht_major_eq_patch_lt",
        "minor_ht_major_patch_eq",
        "minor_patch_ht_major_eq",
        "major_ht_minor_patch_lt",
        "major_ht_patch_eq_minor_lt",
        "patch_major_ht_minor_lt",
        "major_ht_minor_eq_patch_lt",
        "major_ht_minor_patch_eq",
        "major_patch_ht_minor",
        "major_minor_ht_patch_lt",
        "major_minor_ht_patch_eq",
        "major_minor_patch_ht_major",
    ),
)
def test_path(
    mocker: MockFixture, expected_result: int, current_version: dict
):
    mocker.patch("gen_new_version.Bs3client", return_value=MagicMock())
    with patch.object(GenUpdate, "__init__", return_value=None):
        gen_update = GenUpdate()
        gen_update.app_version = current_version
        assert (
            gen_update._check_version_number_validity("1.1.1")
            == expected_result
        )
