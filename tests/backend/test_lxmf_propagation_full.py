import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import LXMF
import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat

# Store original constants
PR_IDLE = LXMF.LXMRouter.PR_IDLE
PR_PATH_REQUESTED = LXMF.LXMRouter.PR_PATH_REQUESTED
PR_PATH_TIMEOUT = LXMF.LXMRouter.PR_PATH_TIMEOUT
PR_RECEIVING = LXMF.LXMRouter.PR_RECEIVING
PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE
PR_FAILED = LXMF.LXMRouter.PR_FAILED


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_app(temp_dir):
    with (
        patch("RNS.Reticulum") as mock_rns,
        patch("RNS.Transport"),
        patch("LXMF.LXMRouter") as mock_router_class,
        patch("meshchatx.meshchat.get_file_path", return_value="/tmp/mock_path"),
        patch("meshchatx.meshchat.generate_ssl_certificate"),
    ):
        # Set up constants on the mock class
        mock_router_class.PR_IDLE = PR_IDLE
        mock_router_class.PR_PATH_REQUESTED = PR_PATH_REQUESTED
        mock_router_class.PR_PATH_TIMEOUT = PR_PATH_TIMEOUT
        mock_router_class.PR_RECEIVING = PR_RECEIVING
        mock_router_class.PR_COMPLETE = PR_COMPLETE
        mock_router_class.PR_FAILED = PR_FAILED

        mock_router = mock_router_class.return_value
        mock_router.PR_IDLE = PR_IDLE
        mock_router.PR_PATH_REQUESTED = PR_PATH_REQUESTED
        mock_router.PR_PATH_TIMEOUT = PR_PATH_TIMEOUT
        mock_router.PR_RECEIVING = PR_RECEIVING
        mock_router.PR_COMPLETE = PR_COMPLETE
        mock_router.PR_FAILED = PR_FAILED

        mock_router.propagation_transfer_state = PR_IDLE
        mock_router.propagation_transfer_progress = 0.0
        mock_router.propagation_transfer_last_result = 0

        mock_dest = MagicMock()
        mock_dest.hash = b"local_dest_hash_16b"
        mock_dest.hexhash = "6c6f63616c5f646573745f686173685f"
        mock_router.register_delivery_identity.return_value = mock_dest

        mock_rns_inst = mock_rns.return_value
        mock_rns_inst.transport_enabled.return_value = False

        with patch(
            "meshchatx.src.backend.meshchat_utils.LXMRouter",
        ) as mock_utils_router:
            mock_utils_router.PR_IDLE = PR_IDLE
            mock_utils_router.PR_PATH_REQUESTED = PR_PATH_REQUESTED
            mock_utils_router.PR_PATH_TIMEOUT = PR_PATH_TIMEOUT
            mock_utils_router.PR_RECEIVING = PR_RECEIVING
            mock_utils_router.PR_COMPLETE = PR_COMPLETE
            mock_utils_router.PR_FAILED = PR_FAILED

            real_id = RNS.Identity()
            app = ReticulumMeshChat(
                identity=real_id,
                storage_dir=temp_dir,
                reticulum_config_dir=temp_dir,
            )

            app.current_context.message_router = mock_router

            with patch.object(
                app,
                "send_config_to_websocket_clients",
                return_value=None,
            ):
                yield app


@pytest.mark.asyncio
async def test_lxmf_propagation_config(mock_app):
    node_hash_hex = "d81255ae2ff367d4883b16c9cc8c6178"
    node_hash_bytes = bytes.fromhex(node_hash_hex)

    await mock_app.update_config(
        {"lxmf_preferred_propagation_node_destination_hash": node_hash_hex},
    )

    mock_app.current_context.message_router.set_outbound_propagation_node.assert_called_with(
        node_hash_bytes,
    )
    assert (
        mock_app.config.lxmf_preferred_propagation_node_destination_hash.get()
        == node_hash_hex
    )


@pytest.mark.asyncio
async def test_lxmf_sync_flow(mock_app):
    mock_router = mock_app.current_context.message_router
    mock_router.get_outbound_propagation_node.return_value = b"somehash"

    # Trigger sync
    for route in mock_app.get_routes():
        if route.path == "/api/v1/lxmf/propagation-node/sync":
            await route.handler(None)
            break

    mock_router.request_messages_from_propagation_node.assert_called_once()

    # Check status (Receiving)
    mock_router.propagation_transfer_state = PR_RECEIVING
    mock_router.propagation_transfer_progress = 0.75

    status_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/status"
    )
    response = await status_handler(None)
    data = json.loads(response.body)
    assert data["propagation_node_status"]["state"] == "receiving"
    assert data["propagation_node_status"]["progress"] == 75.0


@pytest.mark.asyncio
async def test_hosting_prop_node(mock_app):
    mock_router = mock_app.current_context.message_router

    await mock_app.update_config({"lxmf_local_propagation_node_enabled": True})
    mock_router.enable_propagation.assert_called_once()

    await mock_app.update_config({"lxmf_local_propagation_node_enabled": False})
    mock_router.disable_propagation.assert_called_once()


@pytest.mark.asyncio
async def test_send_failed_via_prop_node(mock_app):
    mock_router = mock_app.current_context.message_router
    mock_router.get_outbound_propagation_node.return_value = b"active_prop_node"

    # Create a mock failed message with required attributes
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.state = LXMF.LXMessage.FAILED
    mock_msg.source_hash = b"source_hash_16b"
    mock_msg.destination_hash = b"dest_hash_16b"
    mock_msg.hash = b"msg_hash_16b"

    mock_app.send_failed_message_via_propagation_node(mock_msg)

    assert mock_msg.desired_method == LXMF.LXMessage.PROPAGATED
    mock_router.handle_outbound.assert_called_with(mock_msg)


@pytest.mark.asyncio
async def test_auto_sync_interval_config(mock_app):
    await mock_app.update_config(
        {"lxmf_preferred_propagation_node_auto_sync_interval_seconds": 3600},
    )
    assert (
        mock_app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
        == 3600
    )


@pytest.mark.asyncio
async def test_propagation_node_status_mapping(mock_app):
    mock_router = mock_app.current_context.message_router
    status_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/status"
    )

    states_to_test = [
        (PR_IDLE, "idle"),
        (PR_PATH_REQUESTED, "path_requested"),
        (PR_PATH_TIMEOUT, "path_timeout"),
        (PR_RECEIVING, "receiving"),
        (PR_COMPLETE, "complete"),
        (PR_FAILED, "failed"),
    ]

    for state_val, state_str in states_to_test:
        mock_router.propagation_transfer_state = state_val
        response = await status_handler(None)
        data = json.loads(response.body)
        assert data["propagation_node_status"]["state"] == state_str
        assert "local_propagation_node" in data


@pytest.mark.asyncio
async def test_local_propagation_node_stop_and_restart_routes(mock_app):
    mock_router = mock_app.current_context.message_router
    mock_router.propagation_node = True
    mock_router.compile_stats.return_value = {
        "uptime": 42,
        "messagestore": {"count": 3, "bytes": 2048, "limit": 4096},
        "clients": {
            "client_propagation_messages_received": 7,
            "client_propagation_messages_served": 5,
        },
        "delivery_limit": 10,
        "propagation_limit": 20,
        "sync_limit": 30,
        "target_stamp_cost": 16,
        "static_peers": 1,
        "discovered_peers": 2,
        "total_peers": 3,
        "max_peers": 10,
    }

    stop_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/stop"
    )
    restart_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/restart"
    )

    stop_response = await stop_handler(None)
    stop_data = json.loads(stop_response.body)
    assert stop_data["message"] == "Local propagation node stopped"
    mock_router.disable_propagation.assert_called()

    restart_response = await restart_handler(None)
    restart_data = json.loads(restart_response.body)
    assert restart_data["message"] == "Local propagation node restarted"
    mock_router.enable_propagation.assert_called()


@pytest.mark.asyncio
async def test_user_provided_node_hash(mock_app):
    """Specifically test the node hash provided by the user."""
    node_hash_hex = "d81255ae2ff367d4883b16c9cc8c6178"

    # Set this node as preferred
    await mock_app.update_config(
        {"lxmf_preferred_propagation_node_destination_hash": node_hash_hex},
    )

    # Check if the router was updated with the correct bytes
    mock_app.current_context.message_router.set_outbound_propagation_node.assert_called_with(
        bytes.fromhex(node_hash_hex),
    )

    # Trigger a sync request
    mock_app.current_context.message_router.get_outbound_propagation_node.return_value = bytes.fromhex(
        node_hash_hex,
    )
    sync_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/sync"
    )
    await sync_handler(None)

    # Verify the router was told to sync for our identity
    mock_app.current_context.message_router.request_messages_from_propagation_node.assert_called_with(
        mock_app.current_context.identity,
    )


def test_convert_propagation_node_state_maps_all_lxmf_transfer_states():
    from meshchatx.src.backend.meshchat_utils import (
        convert_propagation_node_state_to_string,
    )

    r = LXMF.LXMRouter
    expected = {
        r.PR_IDLE: "idle",
        r.PR_PATH_REQUESTED: "path_requested",
        r.PR_LINK_ESTABLISHING: "link_establishing",
        r.PR_LINK_ESTABLISHED: "link_established",
        r.PR_REQUEST_SENT: "request_sent",
        r.PR_RECEIVING: "receiving",
        r.PR_RESPONSE_RECEIVED: "response_received",
        r.PR_COMPLETE: "complete",
        r.PR_NO_PATH: "no_path",
        r.PR_LINK_FAILED: "link_failed",
        r.PR_TRANSFER_FAILED: "transfer_failed",
        r.PR_NO_IDENTITY_RCVD: "no_identity_received",
        r.PR_NO_ACCESS: "no_access",
        r.PR_FAILED: "failed",
        r.PR_PATH_TIMEOUT: "path_timeout",
    }
    for state_val, state_str in expected.items():
        assert convert_propagation_node_state_to_string(state_val) == state_str
