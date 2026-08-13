# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

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
    ):
        mock_rns_instance = mock_rns.return_value
        mock_rns_instance.configpath = "/tmp/mock_config"
        mock_rns_instance.is_connected_to_shared_instance = False
        mock_rns_instance.transport_enabled.return_value = True
        # Mock the new blackhole methods
        mock_rns_instance.blackhole_identity = MagicMock()
        mock_rns_instance.unblackhole_identity = MagicMock()
        mock_rns_instance.get_blackholed_identities.return_value = {}

        mock_id = MagicMock(spec=RNS.Identity)
        mock_id.hash = b"\x00" * 32
        mock_id.hexhash = mock_id.hash.hex()
        mock_id.get_private_key.return_value = b"test_private_key"
        yield mock_id


@pytest.mark.asyncio
async def test_banish_identity_with_blackhole(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # Ensure blackhole integration is enabled
        app_instance.config.blackhole_integration_enabled.set(True)

        app_instance.database = MagicMock()
        app_instance.database.announces.get_announce_by_hash.return_value = None
        app_instance.database.announces.get_announces_by_identity_hash.return_value = []
        app_instance.database.announces.get_filtered_announces.return_value = []

        target_hash = "a" * 32

        # Mock request
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        # Find handler
        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        assert handler is not None

        response = await handler(request)
        assert response.status == 200

        # Verify DB call
        app_instance.database.misc.add_blocked_destination.assert_any_call(
            target_hash,
        )

        # Verify RNS blackhole call
        app_instance.reticulum.blackhole_identity.assert_called()
        args, kwargs = app_instance.reticulum.blackhole_identity.call_args
        assert args[0] == bytes.fromhex(target_hash)


@pytest.mark.asyncio
async def test_banish_identity_with_resolution(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        app_instance.config.blackhole_integration_enabled.set(True)
        app_instance.database = MagicMock()
        dest_hash = "d" * 32
        ident_hash = "e" * 32

        # Mock identity resolution
        app_instance.database.announces.get_announce_by_hash.return_value = {
            "identity_hash": ident_hash,
            "destination_hash": dest_hash,
        }
        app_instance.database.announces.get_announces_by_identity_hash.return_value = [
            {"identity_hash": ident_hash, "destination_hash": dest_hash},
        ]
        app_instance.database.announces.get_filtered_announces.return_value = []

        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": dest_hash})

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        await handler(request)

        # Should have blackholed the IDENTITY hash, not the destination hash
        app_instance.reticulum.blackhole_identity.assert_called()
        args, _ = app_instance.reticulum.blackhole_identity.call_args
        assert args[0] == bytes.fromhex(ident_hash)


@pytest.mark.asyncio
async def test_banish_identity_disabled_integration(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        # DISABLE blackhole integration
        app_instance.config.blackhole_integration_enabled.set(False)
        app_instance.database = MagicMock()
        app_instance.database.announces.get_announce_by_hash.return_value = None
        app_instance.database.announces.get_announces_by_identity_hash.return_value = []
        app_instance.database.announces.get_filtered_announces.return_value = []

        target_hash = "b" * 32
        request = MagicMock()
        request.json = AsyncMock(return_value={"destination_hash": target_hash})

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/blocked-destinations" and route.method == "POST":
                handler = route.handler
                break

        await handler(request)

        # DB call should still happen
        app_instance.database.misc.add_blocked_destination.assert_called_with(
            target_hash,
        )

        # RNS blackhole call should NOT happen
        app_instance.reticulum.blackhole_identity.assert_not_called()


@pytest.mark.asyncio
async def test_lift_banishment(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        app_instance.config.blackhole_integration_enabled.set(True)
        app_instance.database = MagicMock()
        # Mock identity resolution
        app_instance.database.announces.get_announce_by_hash.return_value = None
        app_instance.database.announces.get_announces_by_identity_hash.return_value = []
        app_instance.database.announces.get_filtered_announces.return_value = []

        target_hash = "c" * 32

        # Mock request with match_info for the variable in path
        request = MagicMock()
        request.match_info = {"destination_hash": target_hash}

        handler = None
        for route in app_instance.get_routes():
            if (
                route.path == "/api/v1/blocked-destinations/{destination_hash}"
                and route.method == "DELETE"
            ):
                handler = route.handler
                break

        assert handler is not None

        await handler(request)

        # Verify DB call
        app_instance.database.misc.delete_blocked_destination.assert_called_with(
            target_hash,
        )

        # Verify RNS unblackhole call
        app_instance.reticulum.unblackhole_identity.assert_called()
        args, _ = app_instance.reticulum.unblackhole_identity.call_args
        assert args[0] == bytes.fromhex(target_hash)


@pytest.mark.asyncio
async def test_get_blackhole_list(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

        ident_hash_bytes = b"\x01" * 32
        app_instance.reticulum.get_blackholed_identities.return_value = {
            ident_hash_bytes: {
                "source": b"\x02" * 32,
                "until": 1234567890,
                "reason": "Spam",
            },
        }

        request = MagicMock()

        handler = None
        for route in app_instance.get_routes():
            if route.path == "/api/v1/reticulum/blackhole" and route.method == "GET":
                handler = route.handler
                break

        assert handler is not None

        response = await handler(request)
        data = json.loads(response.body)

        assert ident_hash_bytes.hex() in data["blackholed_identities"]
        info = data["blackholed_identities"][ident_hash_bytes.hex()]
        assert info["reason"] == "Spam"
        assert info["source"] == (b"\x02" * 32).hex()


def test_is_destination_blocked_by_identity_hash(mock_rns_minimal, temp_dir):
    """Match blocked destinations when looked up by identity hash.

    When an identity hash is passed to is_destination_blocked, any blocked
    destination belonging to that identity should match.
    """
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app_instance = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )

    app_instance.database = MagicMock()

    ident_hash = "i" * 32
    dest_hash = "d" * 32

    # Simulate: no direct block on the identity hash, no announce with
    # destination_hash == ident_hash, but there IS an announce for the
    # identity and its destination is blocked.
    app_instance.database.misc.is_destination_blocked.side_effect = lambda h: (
        h == dest_hash
    )
    app_instance.database.announces.get_announce_by_hash.return_value = None
    app_instance.database.announces.get_announces_by_identity_hash.return_value = [
        {"destination_hash": dest_hash, "identity_hash": ident_hash},
    ]
    app_instance.database.announces.get_filtered_announces.return_value = []

    assert app_instance.is_destination_blocked(ident_hash) is True

    # Also verify a non-blocked identity returns False
    app_instance.database.misc.is_destination_blocked.side_effect = lambda h: False
    assert app_instance.is_destination_blocked(ident_hash) is False


def _banish_app():
    """Lightweight app for banishment ACL oracles (no Reticulum boot)."""
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    ctx = MagicMock()
    ctx.database.announces.get_announce_by_hash.return_value = None
    ctx.database.announces.get_announces_by_identity_hash.return_value = []
    ctx.database.announces.get_filtered_announces.return_value = []
    ctx.config.blackhole_integration_enabled.get.return_value = True
    ctx.local_lxmf_destination.hash.hex.return_value = "c" * 32
    app.current_context = ctx
    app.reticulum = MagicMock()
    app.get_lxmf_destination_hash_for_identity_hash = MagicMock(return_value=None)
    app.get_lxst_telephony_hash_for_identity_hash = MagicMock(return_value=None)
    app.sync_telephone_call_policy = MagicMock()
    app._broadcast_blocked_destinations = AsyncMock()
    return app, ctx


def test_oracle_identity_block_matches_lxmf_destination():
    """Call/Nomad banish stores the identity hash. LXMF dest of that identity must match."""
    app, ctx = _banish_app()
    ident = "a" * 32
    dest = "b" * 32
    ctx.database.misc.is_destination_blocked.side_effect = lambda h: h == ident
    ctx.database.announces.get_announce_by_hash.side_effect = lambda h: (
        {"identity_hash": ident, "destination_hash": dest} if h == dest else None
    )
    ctx.database.announces.get_announces_by_identity_hash.side_effect = lambda h: (
        [{"identity_hash": ident, "destination_hash": dest}] if h == ident else []
    )
    assert app.is_destination_blocked(dest) is True
    assert app.is_destination_blocked(ident) is True
    assert app.is_destination_blocked("f" * 32) is False


def test_oracle_is_destination_blocked_fail_closed_on_db_error():
    """Broken block-list queries must not fail open for inbound LXMF/LXST."""
    app, ctx = _banish_app()
    ctx.database.misc.is_destination_blocked.side_effect = RuntimeError("db down")
    assert app.is_destination_blocked("a" * 32) is True


def test_oracle_banish_identity_hash_persists_related_dest_and_wipes_history():
    app, ctx = _banish_app()
    ident = "a" * 32
    dest = "b" * 32
    ctx.database.announces.get_announce_by_hash.side_effect = lambda h: (
        {"identity_hash": ident, "destination_hash": dest} if h == dest else None
    )
    ctx.database.announces.get_announces_by_identity_hash.side_effect = lambda h: (
        [{"identity_hash": ident, "destination_hash": dest}] if h == ident else []
    )
    app.get_lxmf_destination_hash_for_identity_hash.return_value = dest

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        app.banish_lxmf_peer(ident)

    added = [
        c.args[0] for c in ctx.database.misc.add_blocked_destination.call_args_list
    ]
    assert ident in added
    assert dest in added
    ctx.message_handler.delete_conversation.assert_any_call("c" * 32, dest)
    ctx.message_handler.delete_conversation.assert_any_call("c" * 32, ident)
    app.reticulum.blackhole_identity.assert_called()
    args, _ = app.reticulum.blackhole_identity.call_args
    assert args[0] == bytes.fromhex(ident)


def test_oracle_banish_does_not_remove_reticulum_interfaces():
    """Banish blackholes the peer. It must not delete interface config sections."""
    import copy

    app, ctx = _banish_app()
    app.reticulum.config = {
        "interfaces": {
            "artyom.ddns.net": {
                "type": "TCPClientInterface",
                "interface_enabled": "True",
                "target_host": "10.100.11.12",
                "target_port": "4242",
            }
        }
    }
    before = copy.deepcopy(app.reticulum.config["interfaces"])
    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        app.banish_lxmf_peer("a" * 32)
    assert app.reticulum.config["interfaces"] == before


def test_oracle_lift_identity_unblocks_related_dest():
    app, ctx = _banish_app()
    ident = "a" * 32
    dest = "b" * 32
    ctx.database.announces.get_announce_by_hash.side_effect = lambda h: (
        {"identity_hash": ident, "destination_hash": dest} if h == dest else None
    )
    ctx.database.announces.get_announces_by_identity_hash.side_effect = lambda h: (
        [{"identity_hash": ident, "destination_hash": dest}] if h == ident else []
    )
    app.get_lxmf_destination_hash_for_identity_hash.return_value = dest

    with patch("meshchatx.meshchat.AsyncUtils") as async_utils:
        async_utils.run_async = MagicMock()
        app.lift_lxmf_peer_banishment(ident)

    deleted = [
        c.args[0] for c in ctx.database.misc.delete_blocked_destination.call_args_list
    ]
    assert ident in deleted
    assert dest in deleted
    unblackholed = [
        c.args[0] for c in app.reticulum.unblackhole_identity.call_args_list
    ]
    assert bytes.fromhex(ident) in unblackholed
    assert bytes.fromhex(dest) in unblackholed
