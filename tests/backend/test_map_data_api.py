# SPDX-License-Identifier: 0BSD

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.src.backend.map_data_manager import MapDataError

HASH = "c" * 32


def _find_handler(app, method, path):
    for route in app.get_routes():
        if getattr(route, "method", None) == method and route.path == path:
            return route.handler
    raise AssertionError(f"missing route {method} {path}")


@pytest.mark.asyncio
async def test_map_data_routes_with_mock_manager(mock_app):
    app = mock_app
    mgr = MagicMock()
    mgr.status.return_value = {
        "aspect": "map-data-v1",
        "running": True,
        "published_count": 1,
    }
    mgr.list_published.return_value = [{"map_id": "aaaaaaaaaaaaaaaa", "name": "Camp"}]
    mgr.list_heard.return_value = [
        {"destination_hash": HASH, "map_name": "Camp", "map_count": 1}
    ]
    mgr.publish_bytes.return_value = {
        "map": {"map_id": "aaaaaaaaaaaaaaaa", "name": "Camp"},
        "stripped": [],
    }
    mgr.unpublish.return_value = True
    mgr.announce.return_value = {"running": True}
    mgr.update_settings.return_value = {"display_name": "Camp maps"}
    mgr.fetch_catalog = AsyncMock(return_value={"destination_hash": HASH, "maps": []})
    mgr.fetch_map_bytes = AsyncMock(return_value=b'{"type":"Point"}')
    mgr.add_as_overlay = AsyncMock(
        return_value={"overlay": {"id": 1, "kind": "map_data"}}
    )
    app.map_data_manager = mgr

    status = await _find_handler(app, "GET", "/api/v1/map/data/status")(MagicMock())
    assert status.status == 200

    published = await _find_handler(app, "GET", "/api/v1/map/data/published")(
        MagicMock()
    )
    assert published.status == 200
    body = json.loads(published.text)
    assert body["maps"][0]["name"] == "Camp"

    heard_req = MagicMock()
    heard_req.query = {"search": "camp", "limit": "10"}
    heard = await _find_handler(app, "GET", "/api/v1/map/data/heard")(heard_req)
    assert heard.status == 200

    pub_req = MagicMock()
    pub_req.json = AsyncMock(
        return_value={
            "name": "Camp",
            "format": "geojson",
            "data_b64": "eyJ0eXBlIjoiUG9pbnQifQ==",
        },
    )
    pub = await _find_handler(app, "POST", "/api/v1/map/data/publish")(pub_req)
    assert pub.status == 200
    mgr.publish_bytes.assert_called_once()

    del_req = MagicMock()
    del_req.match_info = {"map_id": "aaaaaaaaaaaaaaaa"}
    deleted = await _find_handler(
        app,
        "DELETE",
        "/api/v1/map/data/published/{map_id}",
    )(del_req)
    assert deleted.status == 200

    announced = await _find_handler(app, "POST", "/api/v1/map/data/announce")(
        MagicMock()
    )
    assert announced.status == 200

    cfg_req = MagicMock()
    cfg_req.json = AsyncMock(
        return_value={"display_name": "Camp maps", "announce_enabled": True}
    )
    patched = await _find_handler(app, "PATCH", "/api/v1/map/data/config")(cfg_req)
    assert patched.status == 200

    cat_req = MagicMock()
    cat_req.json = AsyncMock(return_value={"destination_hash": HASH})
    catalog = await _find_handler(app, "POST", "/api/v1/map/data/catalog")(cat_req)
    assert catalog.status == 200

    fetch_req = MagicMock()
    fetch_req.json = AsyncMock(
        return_value={"destination_hash": HASH, "map_id": "aaaaaaaaaaaaaaaa"}
    )
    fetched = await _find_handler(app, "POST", "/api/v1/map/data/fetch")(fetch_req)
    assert fetched.status == 200

    add_req = MagicMock()
    add_req.json = AsyncMock(
        return_value={"destination_hash": HASH, "map_id": "aaaaaaaaaaaaaaaa"}
    )
    added = await _find_handler(app, "POST", "/api/v1/map/data/add-overlay")(add_req)
    assert added.status == 200
    mgr.add_as_overlay.assert_awaited()


@pytest.mark.asyncio
async def test_map_data_catalog_missing_path_is_recoverable(mock_app):
    mgr = MagicMock()
    mgr.fetch_catalog = AsyncMock(side_effect=MapDataError("missing_path"))
    mock_app.map_data_manager = mgr
    req = MagicMock()
    req.json = AsyncMock(return_value={"destination_hash": HASH})
    resp = await _find_handler(mock_app, "POST", "/api/v1/map/data/catalog")(req)
    assert resp.status == 503
    body = json.loads(resp.text)
    assert body["error"] == "missing_path"
