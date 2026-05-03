"""Server unit tests using ephemeral ports."""

import json
import threading
import time
import urllib.request

import pytest

from tome.server import build_handler, ThreadingHTTPServer


@pytest.fixture
def running_server(tmp_path):
    scan = {"files": [], "edges": [], "metadata": {"scanned_path": "/tmp"}}

    handler_cls = build_handler(scan_data=scan)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    yield port
    server.shutdown()
    server.server_close()


def _get(port, path):
    return urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2)


def test_api_route_returns_scan_json(running_server):
    r = _get(running_server, "/api/scan-data.json")
    assert r.status == 200
    assert r.headers.get_content_type() == "application/json"
    data = json.loads(r.read())
    assert data["metadata"]["scanned_path"] == "/tmp"


def test_root_returns_index_html(running_server):
    r = _get(running_server, "/")
    assert r.status == 200
    body = r.read().decode()
    assert "<html" in body.lower() or "<!doctype" in body.lower()


def test_unknown_path_falls_back_to_index_html(running_server):
    """SPA fallback: any non-static, non-API route returns index.html so client routing works."""
    r = _get(running_server, "/some/spa/route")
    assert r.status == 200
    body = r.read().decode()
    assert "<html" in body.lower() or "<!doctype" in body.lower()


def test_missing_asset_returns_404_not_html(running_server):
    """Paths with extensions (e.g. /missing.css) should 404, not silently fall back to index.html."""
    import urllib.error
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{running_server}/missing.css", timeout=2)
        assert False, "should have raised HTTPError 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404
