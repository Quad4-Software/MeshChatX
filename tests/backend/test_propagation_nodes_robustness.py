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

        # Use a real identity to satisfy RNS.Destination.hash
        real_id = RNS.Identity()

        # We can still mock parts of it if needed, but RNS expects
        # isinstance(identity, RNS.Identity) to pass or bytes of specific length
        yield real_id


@pytest.mark.asyncio
async def test_propagation_nodes_endpoint_robustness(mock_rns_minimal, temp_dir):
    app_instance = ReticulumMeshChat(
        identity=mock_rns_minimal,
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )

    # Find the propagation nodes handler
    handler = None
    for route in app_instance.get_routes():
        if route.path == "/api/v1/lxmf/propagation-nodes" and route.method == "GET":
            handler = route.handler
            break

    assert handler is not None

    # Test with valid limit
    request = MagicMock()
    request.query = {"limit": "10"}
    response = await handler(request)
    assert response.status == 200
    data = json.loads(response.body)
    assert "lxmf_propagation_nodes" in data

    # Test with invalid limit (should not crash)
    request.query = {"limit": "invalid"}
    response = await handler(request)
    assert response.status == 200
    data = json.loads(response.body)
    assert "lxmf_propagation_nodes" in data

    # Test with missing limit (should not crash)
    request.query = {}
    response = await handler(request)
    assert response.status == 200
    data = json.loads(response.body)
    assert "lxmf_propagation_nodes" in data
