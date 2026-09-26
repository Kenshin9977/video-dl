import logging
import os

import pytest

from videodl_logger import add_log_file


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs a file this user cannot write")
def test_a_log_file_that_cannot_be_written_is_skipped_not_raised(tmp_path):
    """v2.4.1 would not start on a phone where the log file belonged to another install."""
    locked = tmp_path / "video-dl-debug.log"
    locked.write_text("someone else's")
    locked.chmod(0o444)
    logger = logging.getLogger("test_locked_log")

    assert add_log_file(locked, logger) is False
    assert logger.handlers == []


def test_a_writable_log_file_gets_the_records(tmp_path):
    path = tmp_path / "video-dl-debug.log"
    logger = logging.getLogger("test_writable_log")
    logger.setLevel(logging.INFO)

    assert add_log_file(path, logger) is True
    logger.info("download: 66.3 MB/s")
    for handler in logger.handlers:
        handler.close()

    assert "download: 66.3 MB/s" in path.read_text()
