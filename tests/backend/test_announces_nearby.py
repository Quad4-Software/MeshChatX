# SPDX-License-Identifier: 0BSD

"""Regression tests for GET /api/v1/announces/nearby.

The endpoint feeds the mobile compose "nearby peers" section: it must
return lxmf.delivery announces sorted by hop distance (known hops first,
ascending; unknown paths last) and trimmed to the requested limit.
"""

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False

        real_id = RNS.Identity()
        yield real_id


def _route_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _seed_lxmf_announces(app, rows):
    db = app.database
    with db.provider:
        for i, (dest_hash, identity_hash) in enumerate(rows):
            db.announces.upsert_announce(
                {
                    "destination_hash": dest_hash,
                    "aspect": "lxmf.delivery",
                    "identity_hash": identity_hash,
                    "identity_public_key": "",
                    "rssi": None,
                    "snr": None,
                    "quality": None,
                },
            )
            db.provider.execute(
                "UPDATE announces SET updated_at = ? WHERE destination_hash = ?",
                (f"2024-01-01T00:{i:02d}:00Z", dest_hash),
            )


@pytest.mark.asyncio
async def test_announces_nearby_sorts_by_hops_and_limits(
    mock_rns_minimal,
    temp_dir,
):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    handler = _route_handler(app_instance, "/api/v1/announces/nearby", "GET")
    assert handler is not None

    # destination_hash values are 32 hex chars; map each to a hop count.
    hops_by_dest = {
        "a" * 32: 5,
        "b" * 32: 1,
        "c" * 32: 128,  # PATHFINDER_M: unknown path
        "d" * 32: 3,
        "e" * 32: 1,
    }
    _seed_lxmf_announces(
        app_instance,
        [(dest, f"id{i:031x}") for i, dest in enumerate(hops_by_dest)],
    )

    RNS.Transport.PATHFINDER_M = 128
    RNS.Transport.hops_to.side_effect = lambda dest: hops_by_dest.get(dest.hex(), 128)

    request = MagicMock()
    request.query = {"limit": "3"}
    response = await handler(request)

    assert response.status == 200
    data = json.loads(response.body)
    peers = data["peers"]
    assert len(peers) == 3

    # Known hops ascending first; equal hops keep updated_at DESC order
    # (e was seeded after b, so e ranks ahead of b).
    assert [p["destination_hash"] for p in peers] == ["e" * 32, "b" * 32, "d" * 32]
    assert peers[0]["hops"] == 1
    assert peers[2]["hops"] == 3
    for peer in peers:
        assert peer["identity_hash"]
        assert "display_name" in peer
        assert "custom_display_name" in peer
        assert "lxmf_user_icon" in peer
        assert "created_at" in peer
        assert "updated_at" in peer


@pytest.mark.asyncio
async def test_announces_nearby_unknown_hops_sort_last(
    mock_rns_minimal,
    temp_dir,
):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    handler = _route_handler(app_instance, "/api/v1/announces/nearby", "GET")
    assert handler is not None

    _seed_lxmf_announces(
        app_instance,
        [("f" * 32, "id0".ljust(32, "0")), ("0" * 32, "id1".ljust(32, "0"))],
    )

    # "0"*32 is the numerically smallest hash and would sort first if hops
    # were ignored; it must land last because its path is unknown.
    RNS.Transport.PATHFINDER_M = 128
    RNS.Transport.hops_to.side_effect = lambda dest: (
        2 if dest.hex() == "f" * 32 else 128
    )

    request = MagicMock()
    request.query = {}
    response = await handler(request)

    assert response.status == 200
    data = json.loads(response.body)
    peers = data["peers"]
    assert [p["destination_hash"] for p in peers] == ["f" * 32, "0" * 32]


@pytest.mark.asyncio
async def test_announces_nearby_empty(mock_rns_minimal, temp_dir):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    handler = _route_handler(app_instance, "/api/v1/announces/nearby", "GET")
    assert handler is not None

    request = MagicMock()
    request.query = {}
    response = await handler(request)

    assert response.status == 200
    data = json.loads(response.body)
    assert data["peers"] == []
