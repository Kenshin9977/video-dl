import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from core.update_check import newer_release, version_tuple


class TestVersionTuple:
    def test_compares_as_numbers_not_strings(self):
        assert version_tuple("v2.3.12") == (2, 3, 12)
        assert (2, 3, 12) > (2, 3, 9)  # where "2.3.12" > "2.3.9" is False as strings

    @pytest.mark.parametrize("tag", ["nightly", "", "v2.3.x", "2.3.12-rc1"])
    def test_anything_else_is_not_a_version(self, tag):
        assert version_tuple(tag) is None


def _github_says(tag):
    return patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps({"tag_name": tag}).encode()))


class TestNewerRelease:
    def test_a_newer_release_is_reported_without_its_v(self):
        with _github_says("v2.3.12"):
            assert newer_release("2.3.9") == "2.3.12"

    @pytest.mark.parametrize("installed", ["2.3.12", "2.3.13"])
    def test_the_same_or_an_older_release_is_not(self, installed):
        """2.3.13 covers someone ahead of the latest release: no nagging them back."""
        with _github_says("v2.3.12"):
            assert newer_release(installed) is None

    def test_a_tag_that_is_not_a_version_is_ignored(self):
        with _github_says("nightly"):
            assert newer_release("2.3.9") is None

    def test_no_network_means_no_banner_not_a_crash(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            assert newer_release("2.3.9") is None
