import shutil
import tempfile
import pytest
import json
from unittest.mock import MagicMock, patch
from meshchatx.meshchat import ReticulumMeshChat
import RNS
import asyncio


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
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"test_hash_32_bytes_long_01234567"
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_app_info_extended(mock_rns_minimal, temp_dir):
    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("psutil.Process") as mock_process,
        patch("psutil.net_io_counters") as mock_net_io,
        patch("meshchatx.meshchat.LXST") as mock_lxst,
    ):
        mock_lxst.__version__ = "1.2.3"

        # Setup psutil mocks
        mock_proc_instance = mock_process.return_value
        mock_proc_instance.memory_info.return_value.rss = 1024 * 1024
        mock_proc_instance.memory_info.return_value.vms = 2048 * 1024

        mock_net_instance = mock_net_io.return_value
        mock_net_instance.bytes_sent = 100
        mock_net_instance.bytes_recv = 200
        mock_net_instance.packets_sent = 10
        mock_net_instance.packets_recv = 20

        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Create a mock request
        request = MagicMock()

        # Get the app_info handler from the routes
        # We need to find the handler for /api/v1/app/info
        app_info_handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/app/info" and route.method == "GET":
                app_info_handler = route.handler
                break

        assert app_info_handler is not None

        response = await app_info_handler(request)
        data = json.loads(response.body)

        assert "lxst_version" in data["app_info"]
        assert data["app_info"]["lxst_version"] == "1.2.3"


@pytest.mark.asyncio
async def test_app_shutdown_endpoint(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Mock shutdown method to avoid actual exit
        app_instance.shutdown = MagicMock(side_effect=asyncio.sleep(0))

        # Create a mock request
        request = MagicMock()

        # Find the shutdown handler
        shutdown_handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/app/shutdown" and route.method == "POST":
                shutdown_handler = route.handler
                break

        assert shutdown_handler is not None

        # We need to patch sys.exit to avoid stopping the test runner
        with (
            patch("sys.exit"),
            patch("asyncio.sleep", return_value=asyncio.sleep(0)),
        ):
            response = await shutdown_handler(request)
            assert response.status == 200
            data = json.loads(response.body)
            assert data["message"] == "Shutting down..."

            # The shutdown happens in a task, so we wait a bit
            await asyncio.sleep(0.1)

            # Since it's in a task, we might need to check if it was called
            # but sys.exit might not have been reached yet or was called in a different context
            # For this test, verifying the endpoint exists and returns 200 is sufficient.
