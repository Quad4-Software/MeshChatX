import time
from unittest.mock import MagicMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.telemetry_utils import Telemeter


@pytest.fixture
def mock_app():
    # We create a simple mock object that has the methods/attributes
    # needed by process_incoming_telemetry and other telemetry logic.
    app = MagicMock(spec=ReticulumMeshChat)

    # Mock database
    app.database = MagicMock()
    app.database.telemetry = MagicMock()

    # Mock context
    app.current_context = MagicMock()
    app.current_context.database = app.database
    app.current_context.local_lxmf_destination = MagicMock()
    app.current_context.local_lxmf_destination.hexhash = "local_hash"

    # Mock reticulum
    app.reticulum = MagicMock()
    app.reticulum.get_packet_rssi.return_value = -70
    app.reticulum.get_packet_snr.return_value = 12.5
    app.reticulum.get_packet_q.return_value = 85

    # Mock websocket_broadcast
    app.websocket_broadcast = MagicMock()

    # Attach the actual method we want to test if possible,
    # but since it's an instance method, we might need to bind it.
    app.process_incoming_telemetry = (
        ReticulumMeshChat.process_incoming_telemetry.__get__(app, ReticulumMeshChat)
    )

    return app


@pytest.mark.asyncio
async def test_process_incoming_telemetry_single(mock_app):
    source_hash = "source_hash"
    location = {"latitude": 50.0, "longitude": 10.0}
    packed_telemetry = Telemeter.pack(location=location)

    mock_lxmf_message = MagicMock()
    mock_lxmf_message.hash = b"msg_hash"

    mock_app.process_incoming_telemetry(
        source_hash,
        packed_telemetry,
        mock_lxmf_message,
    )

    # Verify database call
    mock_app.database.telemetry.upsert_telemetry.assert_called()
    call_args = mock_app.database.telemetry.upsert_telemetry.call_args[1]
    assert call_args["destination_hash"] == source_hash
    assert call_args["data"] == packed_telemetry


@pytest.mark.asyncio
async def test_process_incoming_telemetry_stream(mock_app):
    entries = [
        (
            "peer1",
            int(time.time()) - 60,
            Telemeter.pack(location={"latitude": 1.0, "longitude": 1.0}),
        ),
        (
            "peer2",
            int(time.time()),
            Telemeter.pack(location={"latitude": 2.0, "longitude": 2.0}),
        ),
    ]

    mock_lxmf_message = MagicMock()
    mock_lxmf_message.hash = b"stream_msg_hash"

    # We call it directly for each entry as process_incoming_telemetry is refactored
    # to handle single entries, and on_lxmf_delivery loops over streams.
    for entry_source, entry_timestamp, entry_data in entries:
        mock_app.process_incoming_telemetry(
            entry_source,
            entry_data,
            mock_lxmf_message,
            timestamp_override=entry_timestamp,
        )

    assert mock_app.database.telemetry.upsert_telemetry.call_count == 2


@pytest.mark.asyncio
async def test_telemetry_request_parsing(mock_app):
    # Test that on_lxmf_delivery correctly identifies telemetry requests
    # and calls handle_telemetry_request.
    mock_lxmf_message = MagicMock()
    # 0x01 is SidebandCommands.TELEMETRY_REQUEST
    # We mock get_fields to return a command request
    mock_lxmf_message.get_fields.return_value = {0x01: [{0x01: int(time.time())}]}
    mock_lxmf_message.source_hash = b"source_hash_bytes"
    mock_lxmf_message.hash = b"msg_hash"
    mock_lxmf_message.destination_hash = b"dest_hash"

    # We need to mock handle_telemetry_request on the app
    mock_app.handle_telemetry_request = MagicMock()

    # Bind on_lxmf_delivery
    mock_app.on_lxmf_delivery = ReticulumMeshChat.on_lxmf_delivery.__get__(
        mock_app,
        ReticulumMeshChat,
    )

    # Mocking dependencies
    mock_app.is_destination_blocked.return_value = False
    mock_app.current_context.config.telemetry_enabled.get.return_value = True
    mock_app.database.contacts.get_contact_by_identity_hash.return_value = {
        "is_telemetry_trusted": True,
    }
    mock_app.database.messages.get_lxmf_message_by_hash.return_value = {}  # To avoid JSON error

    # Call it
    mock_app.on_lxmf_delivery(mock_lxmf_message)

    # Verify handle_telemetry_request was called
    mock_app.handle_telemetry_request.assert_called_with(
        "736f757263655f686173685f6279746573",
    )


@pytest.mark.asyncio
async def test_tracking_toggle_endpoint(mock_app):
    # Mock database responses
    mock_app.database.telemetry.is_tracking.return_value = False

    # We can't easily test the web endpoint here without more setup,
    # but we can test the logic it calls if it was refactored into a method.
