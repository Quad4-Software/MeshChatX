# SPDX-License-Identifier: 0BSD

"""Tests for update transports.

Covers HTTP mirrors/ETag/Range/redirects and the RNS request/reply
transport against an in-process fake session.
"""

import hashlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import pytest
import RNS

_REAL_IDENTITY = RNS.Identity

from meshchatx.src.backend import update_peer as up
from meshchatx.src.backend.update_transports import (
    HttpTransport,
    RnsTransport,
    build_transports,
    transport_kind,
)
from meshchatx.src.backend.update_types import (
    HTTP_MAX_REDIRECTS,
    UpdateSettings,
    UpdateVerifyError,
)
from meshchatx.src.update_rsm import sign_manifest

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _manifest(version="9.9.9", channel="stable", artifacts=None):
    now = time.time()
    return {
        "schema": 2,
        "app": "reticulum-meshchatx",
        "channel": channel,
        "version": version,
        "issued_at": now - 60,
        "valid_until": now + 86400,
        "min_supported_version": "0.0.1",
        "artifacts": artifacts
        if artifacts is not None
        else [
            {
                "name": "pkg-9.9.9.whl",
                "size": 100,
                "sha256": "00" * 32,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    }


class _RangeHandler(BaseHTTPRequestHandler):
    """Static file server with ETag, If-None-Match and Range support."""

    files: ClassVar[dict] = {}
    etags: ClassVar[dict] = {}
    requests: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).requests.append(
            (
                self.path,
                self.headers.get("Range"),
                self.headers.get("User-Agent"),
                self.headers.get("Cookie"),
            )
        )
        body = type(self).files.get(self.path)
        if body is None:
            self.send_error(404)
            return
        etag = type(self).etags.get(self.path)
        inm = self.headers.get("If-None-Match")
        if etag and inm == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        rng = self.headers.get("Range")
        status = 200
        if rng and rng.startswith("bytes="):
            spec = rng[6:].split("-", 1)
            start = int(spec[0]) if spec[0] else 0
            end = int(spec[1]) if len(spec) > 1 and spec[1] else len(body) - 1
            end = min(end, len(body) - 1)
            body = body[start : end + 1]
            status = 206
        self.send_response(status)
        if etag:
            self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def http_server():
    _RangeHandler.files = {}
    _RangeHandler.etags = {}
    _RangeHandler.requests = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _static_mirror(base):
    return {"name": "test", "kind": "static", "base": base}


def _rns_server(tmp_path, artifacts, channel="stable", signer=None):
    """Build a PeerUpdateServer seeded with a signed manifest.

    Covers the given {name: bytes} artifacts. Returns the server.
    """
    signer = signer or _REAL_IDENTITY()
    entries = []
    for name, data in artifacts.items():
        p = tmp_path / name
        p.write_bytes(data)
        entries.append(
            {
                "name": name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        )
    manifest = _manifest(artifacts=entries, channel=channel)
    rsm = sign_manifest(manifest, signer)
    server = up.PeerUpdateServer()
    server.register_manifest(channel, rsm, manifest)
    for name, data in artifacts.items():
        p = tmp_path / name
        server.register_artifact(name, p, hashlib.sha256(data).hexdigest(), len(data))
    server.enabled = True
    return server, rsm


class _FakeRnsSession:
    """In-process fake of RnsSession; request() feeds PeerUpdateServer._handle."""

    def __init__(self, server):
        self._server = server
        self.requests = []
        self.identity = _REAL_IDENTITY()

    def open_link(self, dh, timeout=60.0):
        return True

    def request(self, dh, path, data, timeout=60.0):
        self.requests.append((dh, path, data))
        return self._server._handle(data)


# ---------------------------------------------------------------------------
# HttpTransport
# ---------------------------------------------------------------------------


def test_http_fetch_manifest_and_etag_304(http_server):
    signer = _REAL_IDENTITY()
    rsm = sign_manifest(_manifest(), signer)
    _RangeHandler.files["/updates/stable/manifest.rsm"] = rsm
    _RangeHandler.etags["/updates/stable/manifest.rsm"] = '"etag-1"'
    t = HttpTransport(mirrors=[_static_mirror(http_server)])

    res = t.fetch_manifest("stable")
    assert res["status"] == "ok"
    assert res["data"] == rsm
    assert res["etag"] == '"etag-1"'

    res2 = t.fetch_manifest("stable")
    assert res2["status"] == "unchanged"


def test_http_fetch_file_range(http_server):
    payload = bytes(range(256)) * 40  # 10240 bytes
    _RangeHandler.files["/updates/stable/1.0.0/pkg-9.9.9.whl"] = payload
    t = HttpTransport(mirrors=[_static_mirror(http_server)])
    part = t.fetch_file("stable", "pkg-9.9.9.whl", version="1.0.0", start=100, end=199)
    assert part == payload[100:200]
    whole = t.fetch_file("stable", "pkg-9.9.9.whl", version="1.0.0")
    assert whole == payload


def test_http_mirror_failover(http_server):
    """First mirror 404s, second serves the manifest."""
    signer = _REAL_IDENTITY()
    rsm = sign_manifest(_manifest(), signer)
    _RangeHandler.files["/updates/stable/manifest.rsm"] = rsm

    class _Always404(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_error(404)

    bad_srv = ThreadingHTTPServer(("127.0.0.1", 0), _Always404)
    threading.Thread(target=bad_srv.serve_forever, daemon=True).start()
    try:
        mirrors = [
            _static_mirror(f"http://127.0.0.1:{bad_srv.server_address[1]}"),
            _static_mirror(http_server),
        ]
        t = HttpTransport(mirrors=mirrors)
        res = t.fetch_manifest("stable")
        assert res["status"] == "ok"
        assert res["source"] == "test"
    finally:
        bad_srv.shutdown()
        bad_srv.server_close()


def test_http_bad_artifact_name_rejected(http_server):
    t = HttpTransport(mirrors=[_static_mirror(http_server)])
    with pytest.raises(UpdateVerifyError):
        t.fetch_file("stable", "../etc/passwd", version="1.0")


def test_http_oversize_manifest_rejected(http_server):
    _RangeHandler.files["/updates/stable/manifest.rsm"] = b"x" * (300 * 1024)
    t = HttpTransport(mirrors=[_static_mirror(http_server)])
    with pytest.raises(UpdateVerifyError):
        t.fetch_manifest("stable")


def test_build_transports_ordering():
    s = UpdateSettings(transport="auto")
    transports, rns = build_transports(s)
    assert len(transports) == 2
    assert transport_kind(transports[0]) == "clearnet"
    assert transport_kind(transports[1]) == "rns"
    assert transport_kind(rns) == "rns"

    s = UpdateSettings(transport="rns")
    transports, _ = build_transports(s)
    assert [transport_kind(t) for t in transports] == ["rns"]

    s = UpdateSettings(transport="clearnet")
    transports, _ = build_transports(s)
    assert [transport_kind(t) for t in transports] == ["clearnet"]


class _RedirectHandler(BaseHTTPRequestHandler):
    """Always answers 302 to a configurable Location."""

    location: ClassVar[str] = "/loop"

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", type(self).location)
        self.send_header("Content-Length", "0")
        self.end_headers()


@pytest.fixture
def redirect_server():
    _RedirectHandler.location = "/loop"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _RedirectHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_redirect_allowlist_rules():
    import email.message
    import urllib.request

    from meshchatx.src.backend.update_transports import (
        FetchFailed,
        _RedirectAllowlist,
    )

    h = _RedirectAllowlist({"127.0.0.1"})
    req = urllib.request.Request("http://127.0.0.1/a")
    hdrs = email.message.Message()
    out = h.redirect_request(req, None, 302, "Found", hdrs, "http://127.0.0.1/b")
    assert out is not None
    with pytest.raises(FetchFailed):
        h.redirect_request(req, None, 302, "Found", hdrs, "http://evil.example.com/b")
    hh = _RedirectAllowlist({"127.0.0.1"})
    for _ in range(HTTP_MAX_REDIRECTS):
        hh.redirect_request(req, None, 302, "Found", hdrs, "http://127.0.0.1/x")
    with pytest.raises(FetchFailed):
        hh.redirect_request(req, None, 302, "Found", hdrs, "http://127.0.0.1/y")


def test_http_redirect_foreign_host_rejected(redirect_server):
    _RedirectHandler.location = "http://foreign.invalid/x"
    t = HttpTransport(
        mirrors=[{"name": "r", "kind": "static", "base": redirect_server}],
        timeout=5.0,
    )
    res = t.fetch_manifest("stable")
    assert res["status"] == "none"


def test_http_redirect_loop_capped(redirect_server):
    _RedirectHandler.location = "/loop"
    t = HttpTransport(
        mirrors=[{"name": "r", "kind": "static", "base": redirect_server}],
        timeout=5.0,
    )
    res = t.fetch_manifest("stable")
    assert res["status"] == "none"


def test_http_user_agent_constant_and_no_cookies(http_server):
    from meshchatx.src.backend.update_types import USER_AGENT

    _RangeHandler.files["/updates/stable/manifest.rsm"] = b"rsm-bytes"
    t = HttpTransport(
        mirrors=[{"name": "m", "kind": "static", "base": http_server}],
        timeout=5.0,
    )
    res = t.fetch_manifest("stable")
    assert res["status"] == "ok"
    assert _RangeHandler.requests
    path, _rng, ua, cookie = _RangeHandler.requests[-1]
    assert ua == USER_AGENT == "MeshChatX-Updater"
    assert cookie is None
    assert "?" not in path


# ---------------------------------------------------------------------------
# RnsTransport with fake session
# ---------------------------------------------------------------------------


def test_rns_manifest_probe_hash_first(tmp_path):
    payload = b"artifact-bytes"
    server, rsm = _rns_server(tmp_path, {"pkg-9.9.9.whl": payload})
    session = _FakeRnsSession(server)
    t = RnsTransport(session=session, seeds=["ab" * 16], rate_kbps=1024)

    res = t.fetch_manifest("stable")
    assert res["status"] == "ok"
    assert res["data"] == rsm
    etag = res["etag"]
    assert etag
    # second fetch: known sha -> server answers "same" -> unchanged
    res2 = t.fetch_manifest("stable")
    assert res2["status"] == "unchanged"
    # the probe carried the manifest sha, not the full manifest twice
    import meshchatx.src.backend.update_transports as ut

    reqs = [ut._mp_unpack(d) for _dh, _p, d in session.requests]
    assert reqs[0]["op"] == "probe"
    assert reqs[-1].get("sha256") == etag


def test_rns_fetch_file_ranges(tmp_path):
    payload = bytes(range(256)) * 12  # 3072 bytes
    server, _rsm = _rns_server(tmp_path, {"pkg-9.9.9.whl": payload})
    session = _FakeRnsSession(server)
    t = RnsTransport(session=session, seeds=["ab" * 16], rate_kbps=1024)
    data = t.fetch_file("stable", "pkg-9.9.9.whl")
    assert data == payload
    part = t.fetch_file("stable", "pkg-9.9.9.whl", start=10, end=99)
    assert part == payload[10:100]


def test_rns_no_destinations_unavailable():
    session = _FakeRnsSession(None)
    session.request = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("no request expected")
    )
    t = RnsTransport(session=session, seeds=[])
    res = t.fetch_manifest("stable")
    assert res["status"] == "none"


def test_rns_identity_is_ephemeral():
    session = _FakeRnsSession(None)
    t = RnsTransport(session=session, seeds=[])
    ident = t.identity
    assert ident is not None
    assert ident is session.identity
    assert ident.get_public_key() is not None
