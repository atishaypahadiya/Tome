"""HTTP server for the Tome visualizer.

Serves the bundled React app from `tome/_bundled/visualizer/`, with one
special-case route for the scan data the visualizer should display.
"""

import importlib.resources
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_PORT = 7474
PORT_ATTEMPTS = 10


def _bundle_root() -> Path:
    """Filesystem path to the bundled visualizer assets."""
    return Path(str(importlib.resources.files("tome").joinpath("_bundled/visualizer")))


def build_handler(scan_data: dict):
    """Construct a request handler class closed over the loaded scan data."""
    bundle_root = _bundle_root()
    encoded_scan = json.dumps(scan_data).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_GET(self):
            if self.path == "/api/scan-data.json":
                self._send(200, "application/json", encoded_scan)
                return
            self._serve_static(self.path)

        def _serve_static(self, raw_path: str):
            path = raw_path.split("?", 1)[0].lstrip("/")
            if not path:
                path = "index.html"

            target = (bundle_root / path).resolve()
            try:
                target.relative_to(bundle_root.resolve())
            except ValueError:
                self._send(404, "text/plain", b"not found")
                return

            if target.is_file():
                ctype, _ = mimetypes.guess_type(str(target))
                self._send(200, ctype or "application/octet-stream", target.read_bytes())
                return

            index = bundle_root / "index.html"
            if index.is_file():
                self._send(200, "text/html", index.read_bytes())
                return
            self._send(404, "text/plain", b"not found")

        def _send(self, status: int, ctype: str, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _bind(port_request, handler_cls):
    """Bind a server, with auto-increment fallback when port_request is None."""
    if port_request is not None:
        return ThreadingHTTPServer(("127.0.0.1", port_request), handler_cls)

    last_err = None
    for offset in range(PORT_ATTEMPTS):
        try:
            return ThreadingHTTPServer(("127.0.0.1", DEFAULT_PORT + offset), handler_cls)
        except OSError as e:
            last_err = e
    raise RuntimeError(
        f"Could not bind to any port in [{DEFAULT_PORT}, {DEFAULT_PORT + PORT_ATTEMPTS - 1}]: {last_err}"
    )


def serve(scan_path: str, port: int | None = None, open_browser: bool = True):
    """Load `scan_path`, start the server, optionally open a browser, block until Ctrl+C."""
    with open(scan_path) as f:
        scan_data = json.load(f)

    handler_cls = build_handler(scan_data=scan_data)
    server = _bind(port, handler_cls)
    actual_port = server.server_address[1]
    url = f"http://localhost:{actual_port}"

    print(f"Tome viewer ready at {url}  (Ctrl+C to stop)")
    print(f"Scan: {scan_path}")
    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()
        server.server_close()
        sys.exit(0)
