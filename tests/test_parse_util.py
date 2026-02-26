import pytest

from utils.parse_util import simple_traverse, validate_url


class TestSimpleTraverse:
    def test_dict_single_key(self):
        assert simple_traverse({"a": 1}, ("a",)) == 1

    def test_dict_nested_keys(self):
        assert simple_traverse({"a": {"b": {"c": 42}}}, ("a", "b", "c")) == 42

    def test_dict_missing_key_returns_default(self):
        assert simple_traverse({"a": 1}, ("b",)) is None

    def test_dict_missing_key_custom_default(self):
        assert simple_traverse({"a": 1}, ("b",), default="N/A") == "N/A"

    def test_list_by_index(self):
        assert simple_traverse([10, 20, 30], (1,)) == 20

    def test_list_out_of_bounds_returns_default(self):
        assert simple_traverse([10, 20], (5,)) is None

    def test_list_negative_index_returns_default(self):
        assert simple_traverse([10, 20], (-1,)) is None

    def test_mixed_dict_and_list(self):
        obj = {"items": [{"name": "first"}, {"name": "second"}]}
        assert simple_traverse(obj, ("items", 1, "name")) == "second"

    def test_empty_path_returns_obj(self):
        obj = {"a": 1}
        assert simple_traverse(obj, ()) == obj

    def test_traverse_non_dict_non_list_returns_default(self):
        assert simple_traverse("string", ("key",)) is None

    def test_traverse_none_obj(self):
        assert simple_traverse(None, ("key",)) is None


class TestValidateUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "https://www.youtube.com/watch?v=abc123",
            "ftp://files.example.com/data",
        ],
    )
    def test_valid_urls(self, url):
        assert validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "youtube.com/watch?v=abc",  # no scheme
            "https://",  # no netloc
            "",  # empty
            "not-a-url",  # random text
            "://missing-scheme",  # malformed
        ],
    )
    def test_invalid_urls(self, url):
        assert validate_url(url) is False
