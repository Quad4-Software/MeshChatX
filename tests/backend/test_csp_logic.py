from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from aiohttp import web

from meshchatx.meshchat import ReticulumMeshChat


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
async def test_csp_header_logic(mock_rns_minimal, tmp_path):
    storage_dir = str(tmp_path / "storage")
    config_dir = str(tmp_path / "config")

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=storage_dir,
            reticulum_config_dir=config_dir,
        )

        # Mock the config values
        app_instance.config.csp_extra_connect_src.set("https://api.example.com")
        app_instance.config.map_tile_server_url.set(
            "https://tiles.example.com/{z}/{x}/{y}.png",
        )

        # Mock a request and handler
        request = MagicMock(spec=web.Request)
        request.path = "/"
        request.app = {}

        # We need to mock the handler to return a real response
        async def mock_handler(req):
            return web.Response(text="test")

        # Call _define_routes to get the security_middleware
        routes = web.RouteTableDef()
        _, _, security_middleware = app_instance._define_routes(routes)

        response = await security_middleware(request, mock_handler)

        csp = response.headers.get("Content-Security-Policy", "")
        assert "https://api.example.com" in csp
        assert "https://tiles.example.com" in csp
        assert "default-src 'self'" in csp


@pytest.mark.asyncio
async def test_config_update_csp(mock_rns_minimal, tmp_path):
    storage_dir = str(tmp_path / "storage")
    config_dir = str(tmp_path / "config")

    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=storage_dir,
            reticulum_config_dir=config_dir,
        )

        # Find the config update handler
        config_update_handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/config" and route.method == "PATCH":
                config_update_handler = route.handler
                break

        assert config_update_handler is not None

        # Mock request with new CSP settings
        request_data = {
            "csp_extra_connect_src": "https://api1.com, https://api2.com",
            "csp_extra_img_src": "https://img.com",
        }

        request = MagicMock(spec=web.Request)
        # request.json() must be awaited, so it should return an awaitable
        request.json = AsyncMock(return_value=request_data)

        # To avoid the JSON serialization error of MagicMock in get_config_dict,
        # we mock get_config_dict to return a serializable dict.
        with (
            patch.object(
                app_instance,
                "get_config_dict",
                return_value={"status": "ok"},
            ),
            patch.object(app_instance, "send_config_to_websocket_clients"),
        ):
            response = await config_update_handler(request)
            assert response.status == 200

        assert (
            app_instance.config.csp_extra_connect_src.get()
            == "https://api1.com, https://api2.com"
        )
        assert app_instance.config.csp_extra_img_src.get() == "https://img.com"
