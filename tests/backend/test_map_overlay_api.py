# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

HASH = "c" * 32


def _find_handler(app, method, path):
    for route in app.get_routes():
        if getattr(route, "method", None) == method and route.path == path:
            return route.handler
    raise AssertionError(f"missing route {method} {path}")


@pytest.mark.asyncio
async def test_map_overlay_routes_with_mock_manager(mock_app):
    app = mock_app
    mgr = MagicMock()
    mgr.list_overlays.return_value = []
    mgr.create_overlays = AsyncMock(
        return_value={"job_id": "abc", "overlays": [{"id": 1, "status": "pending"}]},
    )
    mgr.export_overlay.return_value = (
        b'{"type":"Point","coordinates":[0,0]}',
        "application/geo+json",
        "layer.geojson",
    )
    mgr.read_cache_bytes.return_value = (
        b'{"type":"Point","coordinates":[0,0]}',
        "geojson",
    )
    mgr.get_job.return_value = {
        "job_id": "abc",
        "status": "running",
        "phase": "finding_path",
    }
    mgr.cancel_job.return_value = True
    mgr.refresh_overlay = AsyncMock(
        return_value={"job_id": "def", "overlay": {"id": 1}},
    )
    mgr.patch_overlay.return_value = {"id": 1, "visible": 0}
    mgr.delete_overlay.return_value = True
    mgr.export_many.return_value = (
        b"{}",
        "application/geo+json",
        "overlays.geojson",
    )

    app.map_overlay_manager = mgr
    if app.identity is None:
        app.identity = MagicMock()
        app.identity.hash.hex.return_value = "idhash"
    else:
        app.identity.hash = MagicMock()
        app.identity.hash.hex.return_value = "idhash"

    list_handler = _find_handler(app, "GET", "/api/v1/map/overlays")
    resp = await list_handler(MagicMock())
    assert resp.status == 200

    create_handler = _find_handler(app, "POST", "/api/v1/map/overlays")
    req = MagicMock()
    req.json = AsyncMock(
        return_value={"kind": "nomadnet_file", "url": f"{HASH}:/file/a.geojson"},
    )
    resp = await create_handler(req)
    assert resp.status == 200
    mgr.create_overlays.assert_awaited()

    export_handler = _find_handler(
        app,
        "GET",
        "/api/v1/map/overlays/{overlay_id}/export",
    )
    req = MagicMock()
    req.match_info = {"overlay_id": "1"}
    req.rel_url = MagicMock()
    req.rel_url.query = {"format": "geojson"}
    resp = await export_handler(req)
    assert resp.status == 200

    job_handler = _find_handler(app, "GET", "/api/v1/map/overlays/jobs/{job_id}")
    req = MagicMock()
    req.match_info = {"job_id": "abc"}
    resp = await job_handler(req)
    body = json.loads(resp.text)
    assert body["phase"] == "finding_path"

    cancel_handler = _find_handler(
        app,
        "POST",
        "/api/v1/map/overlays/jobs/{job_id}/cancel",
    )
    req = MagicMock()
    req.match_info = {"job_id": "abc"}
    resp = await cancel_handler(req)
    assert resp.status == 200

    multi_handler = _find_handler(app, "POST", "/api/v1/map/overlays/export")
    req = MagicMock()
    req.json = AsyncMock(return_value={"format": "geojson", "ids": [1]})
    resp = await multi_handler(req)
    assert resp.status == 200
