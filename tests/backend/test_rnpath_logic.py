import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from meshchatx.meshchat import ReticulumMeshChat
import RNS


@pytest.fixture
def temp_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def mock_rns_minimal():
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport") as mock_transport,
        patch("LXMF.LXMRouter"),
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        # Setup RNS.Transport mock constants and tables
        mock_transport.path_table = {}
        mock_transport.path_states = {}
        mock_transport.STATE_UNKNOWN = 0
        mock_transport.STATE_RESPONSIVE = 1
        mock_transport.STATE_UNRESPONSIVE = 2

        # Path management mocks
        mock_rns_instance.get_path_table.return_value = []
        mock_rns_instance.get_rate_table.return_value = []
        mock_rns_instance.drop_path.return_value = True
        mock_rns_instance.drop_all_via.return_value = True
        mock_rns_instance.drop_announce_queues = MagicMock()

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"\x00" * 32
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_rnpath_table_endpoint(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        entry = {
            "hash": b"\x01" * 32,
            "hops": 1,
            "via": b"\x02" * 32,
            "interface": "UDP",
            "expires": 1234567890,
        }
        app_instance.reticulum.get_path_table.return_value = [entry]

        request = MagicMock()
        request.query = {}

        handler = next(
            r.handler
            for r in app_instance.get_routes()
            if r.path == "/api/v1/rnpath/table"
        )
        response = await handler(request)
        data = json.loads(response.body)

        assert len(data["table"]) == 1
        assert data["table"][0]["hash"] == entry["hash"].hex()


@pytest.mark.asyncio
async def test_rnpath_request_endpoint(mock_rns_minimal, temp_dir):
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch.object(RNS.Transport, "request_path") as mock_request_path,
    ):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        target_hash = "a" * 32
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        handler = next(
            r.handler
            for r in app_instance.get_routes()
            if r.path == "/api/v1/rnpath/request"
        )
        response = await handler(request)

        mock_request_path.assert_called_with(bytes.fromhex(target_hash))
        assert json.loads(response.body)["success"] is True


@pytest.mark.asyncio
async def test_rnpath_drop_endpoint(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        target_hash = "b" * 32
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        handler = next(
            r.handler
            for r in app_instance.get_routes()
            if r.path == "/api/v1/rnpath/drop"
        )
        response = await handler(request)

        app_instance.reticulum.drop_path.assert_called_with(bytes.fromhex(target_hash))
        assert json.loads(response.body)["success"] is True
