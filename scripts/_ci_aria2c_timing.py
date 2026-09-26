"""TEMPORARY CI diagnostic, removed before merge."""
import json, os, signal, subprocess, threading, time, urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

os.makedirs("/tmp/srv", exist_ok=True)
open("/tmp/srv/clip.mp4", "wb").write(os.urandom(4_000_000))
class Q(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Q, directory="/tmp/srv"))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{httpd.server_address[1]}/clip.mp4"
print(subprocess.run(["aria2c", "--version"], capture_output=True, text=True).stdout.splitlines()[0])
def rpc(m, p=()):
    req = urllib.request.Request("http://127.0.0.1:6899/jsonrpc", data=json.dumps({"jsonrpc": "2.0", "id": "1", "method": m, "params": ["token:x", *p]}).encode())
    return json.load(urllib.request.urlopen(req, timeout=2))["result"]
for how in ("rpc-shutdown", "sigterm"):
    t0 = time.monotonic()
    p = subprocess.Popen(["aria2c", "--enable-rpc", "--rpc-listen-port=6899", "--rpc-secret=x", "-d", "/tmp", "--allow-overwrite=true", url], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for _ in range(100):
        try:
            rpc("aria2.getVersion"); break
        except Exception:
            time.sleep(0.1)
    t_rpc = time.monotonic() - t0
    while not (rpc("aria2.tellStopped", [0, 1]) and not rpc("aria2.tellActive")):
        time.sleep(0.1)
    t_done = time.monotonic() - t0
    t = time.monotonic()
    if how == "sigterm":
        p.send_signal(signal.SIGTERM)
    else:
        rpc("aria2.shutdown")
    p.wait()
    print(f"{how}: rpc up {t_rpc:.2f}s, done {t_done:.2f}s, exit {time.monotonic() - t:.2f}s after stop, rc={p.returncode}")
