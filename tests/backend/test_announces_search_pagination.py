# SPDX-License-Identifier: 0BSD

"""Regression test: announce search must scan beyond the requested page size.

Previously the `/api/v1/announces` search path capped the number of rows
fetched from the database to the caller's requested page size (e.g. 50,
used for pagination of already-filtered results) instead of the configured
search scan limit. This meant a match that was not among the most
recently-updated `limit` announces for the aspect would never be found by
search, even though it had briefly been visible client-side because it was
already loaded from an earlier, non-search page.
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

        # Real identity so RNS.Destination.hash checks succeed.
        real_id = RNS.Identity()
        yield real_id


def _route_handler(app: ReticulumMeshChat, path: str, method: str):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


@pytest.mark.asyncio
async def test_announce_search_finds_match_older_than_page_size(
    mock_rns_minimal, temp_dir
):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    handler = _route_handler(app_instance, "/api/v1/announces", "GET")
    assert handler is not None

    db = app_instance.database
    page_size = 5
    target_hash = "ab" + "1" * 30

    # Seed more announces than the page size, with the searched-for node
    # being the *oldest* by updated_at so it would be excluded if the
    # search scan were (incorrectly) capped to `page_size` rows.
    total_announces = page_size + 10
    with db.provider:
        for i in range(total_announces):
            is_target = i == 0
            dest_hash = target_hash if is_target else f"{i:032x}"
            db.announces.upsert_announce(
                {
                    "destination_hash": dest_hash,
                    "aspect": "nomadnetwork.node",
                    "identity_hash": f"{i:032x}",
                    "identity_public_key": "",
                    "rssi": None,
                    "snr": None,
                    "quality": None,
                }
            )
            # oldest updated_at for i == 0 (the target), newest for the
            # highest i, so ordering by updated_at DESC puts the target last.
            db.provider.execute(
                "UPDATE announces SET updated_at = ? WHERE destination_hash = ?",
                (f"2020-01-01T00:{i:02d}:00Z", dest_hash),
            )

    # `RNS.Transport` is patched to a MagicMock by the fixture above, so
    # give `hops_to` a JSON-serialisable return value.
    RNS.Transport.hops_to.return_value = 1

    request = MagicMock()
    request.query = {
        "aspect": "nomadnetwork.node",
        "search": "ab1111",
        "limit": str(page_size),
        "offset": "0",
    }
    response = await handler(request)

    assert response.status == 200
    data = json.loads(response.body)
    found_hashes = {a["destination_hash"] for a in data["announces"]}
    assert target_hash in found_hashes
