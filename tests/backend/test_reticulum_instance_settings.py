# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat


class ConfigDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.write_called = False

    def write(self):
        self.write_called = True
        return True


@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path)


def build_identity():
    identity = MagicMock(spec=RNS.Identity)
    identity.hash = b"test_hash_32_bytes_long_01234567"
    identity.hexhash = identity.hash.hex()
    identity.get_private_key.return_value = b"test_private_key"
    return identity


async def find_route_handler(app_instance, path, method):
    for route in app_instance.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def test_parse_rns_config_bool():
    assert ReticulumMeshChat._parse_rns_config_bool("Yes") is True
    assert ReticulumMeshChat._parse_rns_config_bool("No") is False
    assert ReticulumMeshChat._parse_rns_config_bool(True) is True
    assert ReticulumMeshChat._parse_rns_config_bool(None, default=True) is True
    assert ReticulumMeshChat._format_rns_config_bool(True) == "Yes"
    assert ReticulumMeshChat._format_rns_config_bool(False) == "No"


@given(
    raw=st.one_of(
        st.booleans(),
        st.sampled_from(
            [
                "Yes",
                "No",
                "yes",
                "no",
                "TRUE",
                "false",
                "1",
                "0",
                "on",
                "off",
                "",
                "  Yes  ",
            ],
        ),
        st.integers(min_value=-3, max_value=3),
        st.none(),
    ),
    default=st.booleans(),
)
@settings(max_examples=80)
def test_parse_rns_config_bool_fuzz(raw, default):
    result = ReticulumMeshChat._parse_rns_config_bool(raw, default=default)
    assert isinstance(result, bool)
    formatted = ReticulumMeshChat._format_rns_config_bool(result)
    assert formatted in ("Yes", "No")
    assert ReticulumMeshChat._parse_rns_config_bool(formatted) is result


@pytest.mark.asyncio
async def test_reticulum_instance_get_and_patch(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {
                "share_instance": "Yes",
                "local_hops_delta": "No",
                "enable_transport": "No",
                "respond_to_probes": "No",
                "enable_remote_management": "No",
                "remote_management_allowed": [
                    "aabbccddeeff00112233445566778899",
                ],
                "instance_name": "default",
                "shared_instance_type": "tcp",
                "rpc_key": "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
            },
            "interfaces": {},
        },
    )

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.shared_instance_type = "tcp"
        mock_reticulum.rpc_key = bytes.fromhex(
            "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        )
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)

        get_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "GET",
        )
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )
        assert get_handler and patch_handler

        get_response = await get_handler(MagicMock())
        get_data = json.loads(get_response.body)
        assert get_data["instance"]["share_instance"] is True
        assert get_data["instance"]["local_hops_delta"] is False
        assert get_data["instance"]["shared_instance_type"] == "tcp"
        assert get_data["instance"]["remote_management_allowed"] == [
            "aabbccddeeff00112233445566778899",
        ]
        assert get_data["instance"]["rpc_config_snippet"]
        assert "rpc_key =" in get_data["instance"]["rpc_config_snippet"]

        class PatchRequest:
            @staticmethod
            async def json():
                return {
                    "share_instance": True,
                    "local_hops_delta": True,
                    "respond_to_probes": True,
                    "shared_instance_type": "unix",
                    "instance_name": "meshchatx",
                    "remote_management_allowed": [
                        "00112233445566778899aabbccddeeff",
                    ],
                    "enable_remote_management": True,
                }

        patch_response = await patch_handler(PatchRequest())
        patch_data = json.loads(patch_response.body)
        assert patch_response.status == 200
        assert patch_data["instance"]["local_hops_delta"] is True
        assert patch_data["instance"]["respond_to_probes"] is True
        assert patch_data["instance"]["enable_remote_management"] is True
        assert patch_data["instance"]["remote_management_allowed"] == [
            "00112233445566778899aabbccddeeff",
        ]
        assert config["reticulum"]["remote_management_allowed"] == [
            "00112233445566778899aabbccddeeff",
        ]
        assert config["reticulum"]["enable_remote_management"] == "Yes"
        assert patch_data["instance"]["shared_instance_type"] == "unix"
        assert patch_data["instance"]["instance_name"] == "meshchatx"
        assert config["reticulum"]["local_hops_delta"] == "Yes"
        assert config["reticulum"]["shared_instance_type"] == "unix"
        assert config.write_called is True
        app_instance.reload_reticulum.assert_awaited_once()


@pytest.mark.asyncio
async def test_reticulum_instance_rejects_bad_type(temp_dir):
    config = ConfigDict({"reticulum": {"share_instance": "Yes"}, "interfaces": {}})

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)

        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )

        class PatchRequest:
            @staticmethod
            async def json():
                return {"shared_instance_type": "udp"}

        response = await patch_handler(PatchRequest())
        assert response.status == 400


@pytest.mark.asyncio
async def test_reticulum_instance_rejects_bad_instance_name(temp_dir):
    config = ConfigDict({"reticulum": {"share_instance": "Yes"}, "interfaces": {}})

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )

        class PatchRequest:
            @staticmethod
            async def json():
                return {"instance_name": "bad name"}

        response = await patch_handler(PatchRequest())
        assert response.status == 400
        app_instance.reload_reticulum.assert_not_awaited()


@pytest.mark.asyncio
async def test_reticulum_instance_empty_patch_noop(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {
                "share_instance": "Yes",
                "local_hops_delta": "No",
            },
            "interfaces": {},
        },
    )

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )

        class PatchRequest:
            @staticmethod
            async def json():
                return {}

        response = await patch_handler(PatchRequest())
        assert response.status == 200
        assert config.write_called is False
        app_instance.reload_reticulum.assert_not_awaited()


@pytest.mark.asyncio
async def test_reticulum_instance_clears_optional_fields(temp_dir):
    config = ConfigDict(
        {
            "reticulum": {
                "share_instance": "Yes",
                "shared_instance_type": "tcp",
                "instance_name": "custom",
            },
            "interfaces": {},
        },
    )

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )

        class PatchRequest:
            @staticmethod
            async def json():
                return {"shared_instance_type": "", "instance_name": ""}

        response = await patch_handler(PatchRequest())
        assert response.status == 200
        assert "shared_instance_type" not in config["reticulum"]
        assert "instance_name" not in config["reticulum"]


@given(
    payload=st.fixed_dictionaries(
        {},
        optional={
            "share_instance": st.one_of(
                st.booleans(),
                st.sampled_from(["Yes", "No", 1, 0]),
            ),
            "local_hops_delta": st.one_of(
                st.booleans(),
                st.sampled_from(["yes", "no"]),
            ),
            "respond_to_probes": st.booleans(),
            "enable_remote_management": st.booleans(),
            "shared_instance_type": st.one_of(
                st.none(),
                st.sampled_from(["tcp", "unix", "TCP", "Unix", "udp", "quic", ""]),
            ),
            "instance_name": st.one_of(
                st.none(),
                st.sampled_from(
                    ["default", "meshchatx", "a", "bad name", "x" * 65, ""],
                ),
                st.text(min_size=0, max_size=80),
            ),
        },
    ),
)
@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.asyncio
async def test_reticulum_instance_patch_fuzz_never_500(payload, temp_dir):
    config = ConfigDict(
        {
            "reticulum": {
                "share_instance": "Yes",
                "local_hops_delta": "No",
            },
            "interfaces": {},
        },
    )

    with (
        patch("meshchatx.meshchat.generate_ssl_certificate"),
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter"),
    ):
        mock_reticulum = mock_rns.return_value
        mock_reticulum.config = config
        mock_reticulum.configpath = "/tmp/mock_config"
        mock_reticulum.is_connected_to_shared_instance = False
        mock_reticulum.share_instance = True
        mock_reticulum.transport_enabled.return_value = False

        app_instance = ReticulumMeshChat(
            identity=build_identity(),
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        app_instance.reload_reticulum = AsyncMock(return_value=True)
        patch_handler = await find_route_handler(
            app_instance,
            "/api/v1/reticulum/instance",
            "PATCH",
        )

        class PatchRequest:
            @staticmethod
            async def json():
                return payload

        response = await patch_handler(PatchRequest())
        assert response.status in (200, 400)
        body = json.loads(response.body)
        assert isinstance(body, dict)
        if response.status == 200:
            assert "instance" in body
            assert isinstance(body["instance"].get("share_instance"), bool)
            assert isinstance(body["instance"].get("local_hops_delta"), bool)


def test_build_reticulum_instance_settings_prefers_config_over_live():
    app = MagicMock()
    app._get_reticulum_section = lambda: {
        "share_instance": "No",
        "local_hops_delta": "No",
        "rpc_key": "aa" * 32,
        "instance_name": "default",
    }
    app._parse_rns_config_bool = ReticulumMeshChat._parse_rns_config_bool
    app._get_reticulum_rpc_key_hex = lambda: (
        ReticulumMeshChat._get_reticulum_rpc_key_hex(app)
    )
    app.reticulum = MagicMock()
    app.reticulum.share_instance = True
    app.reticulum.is_connected_to_shared_instance = False
    app.reticulum.transport_enabled = MagicMock(return_value=True)
    app.reticulum.rpc_key = None

    settings = ReticulumMeshChat._build_reticulum_instance_settings(app)
    assert settings["share_instance"] is False
    assert settings["local_hops_delta"] is False
    assert settings["rpc_config_snippet"]
    assert "rpc_key = " in settings["rpc_config_snippet"]
