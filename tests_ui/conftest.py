"""One app for the whole run, and a local server for it to download from.

flet's own `flet_app` fixture launches a fresh app per test, which costs about a
minute each: `flutter test` starts over every time. Sharing one app keeps the suite
usable, at the price that each test has to put the window back the way it found it.

Nothing here touches the internet. YouTube refuses CI runners, and a test that
depends on a third-party host goes red for reasons that have nothing to do with us
(the Big Buck Bunny 404 held CI red for seven weeks). The app downloads from a
server on localhost instead, serving a clip ffmpeg makes on the spot.
"""

import os
import shutil
import subprocess
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import flet.testing as ftt
import pytest
import pytest_asyncio

# How long a slow download dribbles for. Long enough to press Cancel mid-way.
SLOW_SECONDS = 60


class _Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/slow.mp4":
            # A real Content-Length and a trickle of bytes: yt-dlp sees a download
            # in progress that will not finish on its own any time soon.
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(1024 * SLOW_SECONDS * 10))
            self.end_headers()
            try:
                for _ in range(SLOW_SECONDS * 10):
                    self.wfile.write(b"\0" * 1024)
                    self.wfile.flush()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        super().do_GET()


@pytest.fixture(scope="session")
def media_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("media")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.fail("ffmpeg must be on PATH to make the sample clip")
    subprocess.run(
        [
            ffmpeg, "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(root / "sample.mp4"),
        ],
        check=True,
    )  # fmt: skip
    return root


@pytest.fixture(scope="session")
def server(media_root):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=str(media_root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(scope="session")
def download_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("downloads")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app(download_dir, server, tmp_path_factory):
    # The app is a separate process started by `flutter test`, which inherits this
    # environment. uitest_main.py reads the download folder from it.
    os.environ["VIDEODL_UITEST_DOWNLOAD_DIR"] = str(download_dir)
    os.environ["VIDEODL_UITEST_CONFIG_DIR"] = str(tmp_path_factory.mktemp("config"))
    for tool in ("ffmpeg", "ffprobe"):
        os.environ[f"VIDEODL_UITEST_{tool.upper()}"] = shutil.which(tool) or pytest.fail(f"{tool} must be on PATH")
    # `flet test` builds the app, starts it with embedded Python, and says where.
    flet_app = ftt.FletTestApp(flutter_app_dir=Path(os.environ["FLET_TEST_FLUTTER_APP_DIR"]), device_mode=True)
    await flet_app.start()
    yield flet_app
    await flet_app.teardown()


@pytest_asyncio.fixture(loop_scope="session")
async def tester(app, download_dir):
    """The shared app, with an empty link field and an empty download folder."""
    tester = app.tester
    await tester.enter_text(await tester.find_by_key("media_link"), "")
    await tester.pump_and_settle()
    for entry in download_dir.iterdir():
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    return tester
