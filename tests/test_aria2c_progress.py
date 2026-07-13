import inspect
import sys
from unittest.mock import MagicMock, patch

import pytest

# tests/test_download.py leaves MagicMocks in place of the yt_dlp package tree.
# This module has to see the real thing: it exists to check our assumptions
# against the yt-dlp that is actually installed.
for _name in [
    name for name, mod in list(sys.modules.items()) if name.startswith("yt_dlp") and isinstance(mod, MagicMock)
]:
    del sys.modules[_name]

from yt_dlp.downloader.external import Aria2cFD, ExternalFD  # noqa: E402

from core import aria2c_progress  # noqa: E402
from core.aria2c_progress import _download_with_progress  # noqa: E402


def _fake_process(poll_sequence, returncode=0):
    """A Popen whose poll() follows a script, then keeps repeating its last answer.

    A process that has exited stays exited, one that is still running stays
    running. Handing poll() a fixed list instead makes the test encode exactly how
    many times the downloader happens to call it, and it breaks the day it calls
    it once more.
    """
    answers = iter(poll_sequence)
    last = None

    def poll():
        nonlocal last
        last = next(answers, last)
        return last

    process = MagicMock()
    process.__enter__ = MagicMock(return_value=process)
    process.__exit__ = MagicMock(return_value=False)
    process.poll = MagicMock(side_effect=poll)
    process.returncode = returncode
    process.wait = MagicMock(return_value=returncode)
    process.communicate = MagicMock(return_value=("", ""))
    return process


def _popen_returning(process):
    return MagicMock(return_value=process)


def _downloader():
    downloader = MagicMock()
    downloader.params = {}
    return downloader


def _active(completed, total, speed=50_000):
    return [{"completedLength": str(completed), "totalLength": str(total), "downloadSpeed": str(speed)}]


def _done(total):
    return [{"totalLength": str(total), "completedLength": str(total)}]


class TestSeams:
    """Guard the yt-dlp internals core/aria2c_progress.py reaches into."""

    def test_aria2c_still_exposes_the_methods_we_wrap(self):
        for seam in ("_call_downloader", "_call_process", "_make_cmd", "_hook_progress"):
            assert hasattr(Aria2cFD, seam), f"Aria2cFD.{seam} is gone"

    def test_call_process_still_has_the_signature_we_replace(self):
        params = inspect.signature(ExternalFD._call_process).parameters
        assert list(params) == ["self", "cmd", "info_dict"]

    def test_the_utils_we_borrow_are_still_there(self):
        from yt_dlp.networking import Request  # noqa: F401
        from yt_dlp.utils import Popen, find_available_port, traverse_obj  # noqa: F401


class TestInstall:
    def test_is_idempotent(self):
        assert aria2c_progress.install()
        patched = Aria2cFD._call_process
        assert aria2c_progress.install()
        assert Aria2cFD._call_process is patched

    def test_allocates_an_rpc_endpoint_and_passes_it_to_aria2c(self):
        from yt_dlp.utils import find_available_port

        downloader = _downloader()
        info_dict = {"url": "https://example.com/video.mp4"}

        rpc = aria2c_progress.allocate_rpc(downloader, info_dict, find_available_port)

        assert rpc and rpc["port"] and rpc["secret"]
        assert info_dict["__rpc"] is rpc

        flags = aria2c_progress.rpc_flags(info_dict)
        assert flags == ["--enable-rpc", f"--rpc-listen-port={rpc['port']}", f"--rpc-secret={rpc['secret']}"]

    def test_respects_the_compat_opt_that_turns_progress_off(self):
        from yt_dlp.utils import find_available_port

        downloader = _downloader()
        downloader.params = {"compat_opts": {"no-external-downloader-progress"}}
        info_dict = {"url": "https://example.com/video.mp4"}

        assert aria2c_progress.allocate_rpc(downloader, info_dict, find_available_port) is None
        assert "__rpc" not in info_dict
        assert aria2c_progress.rpc_flags(info_dict) == []

    def test_no_free_port_costs_the_bar_not_the_download(self):
        downloader = _downloader()
        info_dict = {"url": "https://example.com/video.mp4"}

        assert aria2c_progress.allocate_rpc(downloader, info_dict, lambda: None) is None
        assert "__rpc" not in info_dict


class TestProgressReporting:
    def setup_method(self):
        from yt_dlp.utils import traverse_obj

        self.traverse_obj = traverse_obj
        self.info_dict = {"_filename": "video.mp4", "__rpc": {"port": 6800, "secret": "s3cret"}}

    def _run(self, downloader, process, rpc):
        with patch.object(aria2c_progress, "rpc_call", side_effect=rpc):
            return _download_with_progress(
                downloader, ["aria2c"], self.info_dict, _popen_returning(process), self.traverse_obj
            )

    def test_reports_progress_while_aria2c_downloads(self):
        downloader = _downloader()
        reports = []
        downloader._hook_progress.side_effect = lambda status, info: reports.append(dict(status))

        answers = [
            None,  # getVersion, the readiness check
            _active(100_000, 1_000_000),
            [],
            _active(500_000, 1_000_000),
            [],
            [],  # nothing active,
            _done(1_000_000),  # and one finished: the download is over
            None,  # shutdown
        ]
        _, _, returncode = self._run(downloader, _fake_process([None, None, None]), answers)

        assert returncode == 0
        progressed = [r for r in reports if r["downloaded_bytes"] > 0]
        assert [r["downloaded_bytes"] for r in progressed] == [100_000, 500_000, 1_000_000]
        assert progressed[0]["total_bytes"] == 1_000_000
        assert progressed[0]["speed"] == 50_000
        assert progressed[0]["eta"] == pytest.approx((1_000_000 - 100_000) / 50_000)
        assert progressed[0]["status"] == "downloading"

    def test_downloads_anyway_when_the_rpc_server_never_answers(self):
        downloader = _downloader()
        rpc = [ConnectionError("refused")] * aria2c_progress._RPC_STARTUP_ATTEMPTS

        with patch("time.sleep"):
            _, _, returncode = self._run(downloader, _fake_process([None]), rpc)

        assert returncode == 0
        downloader._hook_progress.assert_not_called()
        assert any("without progress" in str(c) for c in downloader.to_screen.call_args_list)

    def test_surfaces_an_aria2c_that_dies_on_startup(self):
        downloader = _downloader()
        _, _, returncode = self._run(downloader, _fake_process([1], returncode=1), [ConnectionError("refused")])

        assert returncode == 1
        downloader._hook_progress.assert_not_called()

    def test_lets_the_download_finish_when_the_rpc_dies_mid_way(self):
        downloader = _downloader()
        reports = []
        downloader._hook_progress.side_effect = lambda status, info: reports.append(dict(status))

        answers = [None, ConnectionError("gone")]
        _, _, returncode = self._run(downloader, _fake_process([None, None]), answers)

        assert returncode == 0
        assert len(reports) == 1, "only the initial report, then it goes blind but does not crash"
        assert any("connection lost" in str(c) for c in downloader.to_screen.call_args_list)

    def test_gives_no_eta_when_the_size_is_unknown(self):
        downloader = _downloader()
        reports = []
        downloader._hook_progress.side_effect = lambda status, info: reports.append(dict(status))

        answers = [
            None,
            [{"completedLength": "100", "totalLength": "0", "downloadSpeed": "0"}],
            [],
            [],
            _done(100),
            None,
        ]
        self._run(downloader, _fake_process([None, None]), answers)

        assert reports[1]["eta"] is None
        assert reports[1]["total_bytes"] is None
        assert reports[1]["speed"] is None

    def test_shuts_down_an_aria2c_that_reports_nothing_at_all(self):
        """Without this the download hangs until the user kills the app."""
        downloader = _downloader()
        clock = iter([0, 0, 1, _IDLE := aria2c_progress._IDLE_TIMEOUT + 2])

        answers = [None, [], [], [], [], [], [], None]
        process = _fake_process([None, None, None])

        with patch("time.sleep"), patch("time.time", side_effect=lambda: next(clock, 100)):
            _, _, returncode = self._run(downloader, process, answers)

        assert returncode == 0
        process.wait.assert_called()
        assert any("no download at all" in str(c) for c in downloader.to_screen.call_args_list)
