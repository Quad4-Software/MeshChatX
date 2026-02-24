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
PR_COMPLETE = LXMF.LXMRouter.PR_COMPLETE


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
        mock_router_class.PR_COMPLETE = PR_COMPLETE

        mock_router = mock_router_class.return_value
        mock_router.PR_IDLE = PR_IDLE
        mock_router.PR_COMPLETE = PR_COMPLETE

        mock_router.propagation_transfer_state = PR_IDLE
        mock_router.propagation_transfer_progress = 0
        mock_router.propagation_transfer_last_result = 0

        mock_dest = MagicMock()
        mock_dest.hexhash = "mock_hash"
        mock_router.register_delivery_identity.return_value = mock_dest

        mock_rns_inst = mock_rns.return_value
        mock_rns_inst.transport_enabled.return_value = False

        with patch(
            "meshchatx.src.backend.meshchat_utils.LXMRouter",
        ) as mock_utils_router:
            mock_utils_router.PR_IDLE = PR_IDLE
            mock_utils_router.PR_COMPLETE = PR_COMPLETE

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
async def test_lxmf_sync_endpoints(mock_app):
    # 1. Test status endpoint initially idle
    handler = None
    for route in mock_app.get_routes():
        if (
            route.path == "/api/v1/lxmf/propagation-node/status"
            and route.method == "GET"
        ):
            handler = route.handler
            break

    assert handler is not None
    response = await handler(None)
    data = json.loads(response.body)
    assert data["propagation_node_status"]["state"] == "idle"

    # 2. Test sync initiation
    sync_handler = None
    for route in mock_app.get_routes():
        if route.path == "/api/v1/lxmf/propagation-node/sync" and route.method == "GET":
            sync_handler = route.handler
            break

    assert sync_handler is not None

    # Mock outbound propagation node configured
    mock_app.current_context.message_router.get_outbound_propagation_node.return_value = b"somehash"

    response = await sync_handler(None)
    assert response.status == 200
    mock_app.current_context.message_router.request_messages_from_propagation_node.assert_called_once()

    # 3. Test status change to complete
    mock_app.current_context.message_router.propagation_transfer_state = (
        LXMF.LXMRouter.PR_COMPLETE
    )
    response = await handler(None)
    data = json.loads(response.body)
    assert data["propagation_node_status"]["state"] == "complete"


@pytest.mark.asyncio
async def test_specific_node_hash_validation(mock_app):
    node_hash_hex = "d81255ae2ff367d4883b16c9cc8c6178"

    # Ensure update_config doesn't crash due to mock serialization
    with patch.object(mock_app, "send_config_to_websocket_clients", return_value=None):
        # Set the preferred propagation node
        await mock_app.update_config(
            {"lxmf_preferred_propagation_node_destination_hash": node_hash_hex},
        )

    # Verify it was set on the router correctly as 16 bytes
    expected_bytes = bytes.fromhex(node_hash_hex)
    mock_app.current_context.message_router.set_outbound_propagation_node.assert_called_with(
        expected_bytes,
    )

    # Trigger sync
    sync_handler = None
    for route in mock_app.get_routes():
        if route.path == "/api/v1/lxmf/propagation-node/sync" and route.method == "GET":
            sync_handler = route.handler
            break

    # Ensure it's considered configured
    mock_app.current_context.message_router.get_outbound_propagation_node.return_value = expected_bytes

    await sync_handler(None)
    mock_app.current_context.message_router.request_messages_from_propagation_node.assert_called_once()


@pytest.mark.asyncio
async def test_status_includes_sync_storage_and_confirmation_metrics(mock_app):
    status_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/status"
    )
    sync_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/sync"
    )

    mock_app.current_context.message_router.get_outbound_propagation_node.return_value = b"somehash"
    mock_app.current_context.message_router.propagation_transfer_last_result = 8

    with (
        patch.object(
            mock_app.current_context.database.messages,
            "count_lxmf_messages",
            side_effect=[10, 13],
        ),
        patch.object(
            mock_app.current_context.database.messages,
            "count_lxmf_messages_by_state",
            side_effect=[2, 4],
        ),
    ):
        await sync_handler(None)
        response = await status_handler(None)

    data = json.loads(response.body)["propagation_node_status"]
    assert data["messages_received"] == 8
    assert data["messages_stored"] == 3
    assert data["delivery_confirmations"] == 2
    assert data["messages_hidden"] == 3


@pytest.mark.asyncio
async def test_status_metrics_default_to_zero_before_any_sync(mock_app):
    status_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/status"
    )
    response = await status_handler(None)
    data = json.loads(response.body)["propagation_node_status"]

    assert data["messages_received"] == 0
    assert data["messages_stored"] == 0
    assert data["delivery_confirmations"] == 0
    assert data["messages_hidden"] == 0


@pytest.mark.asyncio
async def test_status_hidden_metric_is_clamped_to_zero(mock_app):
    status_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/status"
    )
    sync_handler = next(
        r.handler
        for r in mock_app.get_routes()
        if r.path == "/api/v1/lxmf/propagation-node/sync"
    )

    mock_app.current_context.message_router.get_outbound_propagation_node.return_value = b"somehash"
    mock_app.current_context.message_router.propagation_transfer_last_result = 1

    with (
        patch.object(
            mock_app.current_context.database.messages,
            "count_lxmf_messages",
            side_effect=[10, 20],
        ),
        patch.object(
            mock_app.current_context.database.messages,
            "count_lxmf_messages_by_state",
            side_effect=[2, 8],
        ),
    ):
        await sync_handler(None)
        response = await status_handler(None)

    data = json.loads(response.body)["propagation_node_status"]
    assert data["messages_hidden"] == 0


def test_on_lxmf_sending_failed_forwards_context_to_state_update(mock_app):
    msg = MagicMock(spec=LXMF.LXMessage)
    msg.state = LXMF.LXMessage.FAILED
    msg.try_propagation_on_fail = False

    with patch.object(mock_app, "on_lxmf_sending_state_updated") as state_update_mock:
        mock_app.on_lxmf_sending_failed(msg, context=mock_app.current_context)

    state_update_mock.assert_called_once_with(msg, context=mock_app.current_context)
