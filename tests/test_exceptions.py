from __future__ import annotations

import pytest

from core.exceptions import DownloadCancelled, FFmpegNoValidEncoderFound, PlaylistNotFound

_ALL_EXCEPTIONS = [DownloadCancelled, FFmpegNoValidEncoderFound, PlaylistNotFound]


class TestExceptionHierarchy:
    @pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
    def test_inherits_from_exception(self, exc_class):
        assert issubclass(exc_class, Exception)

    @pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
    def test_can_be_raised_and_caught(self, exc_class):
        with pytest.raises(exc_class):
            raise exc_class()

    @pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
    def test_has_docstring(self, exc_class):
        assert exc_class.__doc__ is not None

    def test_exceptions_are_distinct(self):
        for i, exc_a in enumerate(_ALL_EXCEPTIONS):
            for exc_b in _ALL_EXCEPTIONS[i + 1 :]:
                with pytest.raises(exc_a):
                    try:
                        raise exc_a()
                    except exc_b:
                        pytest.fail(f"{exc_a.__name__} should not be caught by {exc_b.__name__}")
