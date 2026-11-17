# SPDX-License-Identifier: 0BSD

"""Route-level tests for /api/v1/update/* handlers.

Handlers are invoked directly with stub requests; the manager is a
recording stub so these tests cover wiring, error mapping and payload
shape, not manager internals (covered by test_update_manager.py).
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.http.routes.update import register_update_routes
from meshchatx.src.backend.update_manager import (
    UpdateError,
    UpdateUnavailable,
    UpdateVerifyError,
)
from tests.backend.http_request_stubs import json_request


class _Routes:
    def __init__(self):
        self.table = {}

    def _add(self, method, path):
        def deco(fn):
            self.table[(method, path)] = fn
            return fn

        return deco

    def get(self, path):
        return self._add("GET", path)

    def post(self, path):
        return self._add("POST", path)


class StubManager:
    def __init__(self):
        self.calls = []
        self.status_payload = {
            "enabled": False,
            "current_version": "4.12.0",
            "channel": "stable",
            "settings": {"enabled": False},
            "disclosure": {
                "mirrors": [],
                "rns_destination": "meshchatx.update",
                "signer_hashes": [],
                "channel": "stable",
                "note": "n",
            },
            "last_check": None,
            "progress": {"phase": "idle"},
            "pending": None,
            "peer_relay_active": False,
            "platform": "linux",
            "arch": "x86_64",
        }
        self.pending_payload = {"pending": None}
        self.progress_payload = {"phase": "idle"}

    def status(self):
        self.calls.append("status")
        return self.status_payload

    def get_pending(self):
        return self.pending_payload

    def get_progress(self):
        return self.progress_payload

    def update_settings(self, patch):
        self.calls.append(("settings", patch))
        return self.status_payload

    def check_now(self, manual=True, allow_downgrade=False):
        self.calls.append(("check", manual, allow_downgrade))
        return {"status": "up_to_date", "update": None}

    def download(self, artifact, **kw):
        self.calls.append(("download", artifact))
        return {
            "status": "staged",
            "artifact": "a",
            "path": "/x",
            "size": 1,
            "sha256": "00" * 32,
            "bytes_fetched": 1,
            "bytes_reused": 0,
        }

    def apply_file(self, path, **kw):
        self.calls.append(("apply_file", path, kw))
        return {
            "status": "staged",
            "artifact": "a",
            "path": "/x",
            "size": 1,
            "sha256": "00" * 32,
        }

    def discard(self):
        self.calls.append("discard")
        return {"status": "discarded"}


@pytest.fixture
def routes():
    mgr = StubManager()
    app = SimpleNamespace(update_manager=mgr)
    r = _Routes()
    register_update_routes(r, app)
    return r.table, mgr


def _get_req():
    req = MagicMock()
    req.match_info = {}
    req.query = {}
    return req


async def _call(table, method, path, request=None):
    handler = table[(method, path)]
    resp = await handler(request if request is not None else _get_req())
    return resp.status, json.loads(resp.body)


@pytest.mark.asyncio
async def test_status_route(routes):
    table, mgr = routes
    status, body = await _call(table, "GET", "/api/v1/update/status")
    assert status == 200
    assert body["enabled"] is False
    assert body["current_version"] == "4.12.0"
    assert "status" in mgr.calls


@pytest.mark.asyncio
async def test_pending_and_progress_routes(routes):
    table, _mgr = routes
    status, body = await _call(table, "GET", "/api/v1/update/pending")
    assert status == 200 and body == {"pending": None}
    status, body = await _call(table, "GET", "/api/v1/update/progress")
    assert status == 200 and body["phase"] == "idle"


@pytest.mark.asyncio
async def test_settings_route_valid_and_invalid(routes):
    table, mgr = routes
    status, _body = await _call(
        table,
        "POST",
        "/api/v1/update/settings",
        json_request({"enabled": True, "channel": "beta"}),
    )
    assert status == 200
    assert ("settings", {"enabled": True, "channel": "beta"}) in mgr.calls

    status, _body = await _call(
        table, "POST", "/api/v1/update/settings", json_request({"channel": "bogus"})
    )
    # stub manager does not validate; force a real validation error instead
    mgr.update_settings = lambda patch: (_ for _ in ()).throw(UpdateError("bad patch"))
    status, _body = await _call(
        table, "POST", "/api/v1/update/settings", json_request({"channel": "bogus"})
    )
    assert status == 400


@pytest.mark.asyncio
async def test_check_route(routes):
    table, mgr = routes
    req = json_request({"allow_downgrade": True})
    req.can_read_body = True
    status, body = await _call(table, "POST", "/api/v1/update/check", req)
    assert status == 200
    assert body["status"] == "up_to_date"
    assert ("check", True, True) in mgr.calls


@pytest.mark.asyncio
async def test_download_route_checks_first(routes):
    table, mgr = routes
    mgr.check_now = lambda manual=True, allow_downgrade=False: {
        "status": "update_available",
        "update": {"artifact": {"name": "a.whl"}},
    }
    req = json_request({})
    req.can_read_body = True
    status, body = await _call(table, "POST", "/api/v1/update/download", req)
    assert status == 200
    assert body["status"] == "staged"
    assert ("download", {"name": "a.whl"}) in mgr.calls


@pytest.mark.asyncio
async def test_download_route_verify_error_422(routes):
    table, mgr = routes

    def _boom(artifact, **kw):
        raise UpdateVerifyError("sha mismatch")

    mgr.download = _boom
    status, _body = await _call(
        table,
        "POST",
        "/api/v1/update/download",
        json_request({"artifact": {"name": "a"}}),
    )
    assert status == 422


@pytest.mark.asyncio
async def test_apply_file_json_path(routes, tmp_path):
    table, mgr = routes
    f = tmp_path / "pkg.whl"
    f.write_bytes(b"x")
    req = json_request({"path": str(f)})
    req.content_type = "application/json"
    status, body = await _call(table, "POST", "/api/v1/update/apply-file", req)
    assert status == 200
    assert body["status"] == "staged"
    assert ("apply_file", str(f), {"channel": None}) in mgr.calls


@pytest.mark.asyncio
async def test_apply_file_unavailable_503(routes):
    table, mgr = routes

    def _unavail(path, **kw):
        raise UpdateUnavailable("no manifest")

    mgr.apply_file = _unavail
    req = json_request({"path": "/tmp/x"})
    req.content_type = "application/json"
    status, _body = await _call(table, "POST", "/api/v1/update/apply-file", req)
    assert status == 503


@pytest.mark.asyncio
async def test_discard_route(routes):
    table, mgr = routes
    status, body = await _call(
        table, "POST", "/api/v1/update/discard", json_request({})
    )
    assert status == 200
    assert body["status"] == "discarded"
    assert "discard" in mgr.calls


@pytest.mark.asyncio
async def test_disabled_manager_fallback():
    """With no update_manager on the app, routes return disabled shapes."""
    app = SimpleNamespace()  # no update_manager attribute
    r = _Routes()
    register_update_routes(r, app)
    table = r.table
    status, body = await _call(table, "GET", "/api/v1/update/status")
    assert status == 200
    assert body["enabled"] is False
    assert body.get("unavailable") is True
    status, body = await _call(table, "POST", "/api/v1/update/check", json_request({}))
    assert status == 200
    assert body["status"] == "disabled"
