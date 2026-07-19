# SPDX-License-Identifier: 0BSD

import json
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.message_export_bundle import (
    MESSAGE_EXPORT_FORMAT,
    build_messages_export_bundle,
    import_messages_export_bundle,
)


def _make_json_request(body):
    request = MagicMock()

    async def _json():
        return body

    request.json = _json
    return request


def _make_export_request(**query):
    """GET export reads request.query. Bare MagicMock makes .get() truthy junk."""
    request = MagicMock()
    request.query = dict(query)
    return request


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


def _seed_message(app, *, msg_hash, peer, incoming=1, timestamp=1000.0, content="Hi"):
    app.database.messages.upsert_lxmf_message(
        {
            "hash": msg_hash,
            "source_hash": peer if incoming else "local",
            "destination_hash": "local" if incoming else peer,
            "peer_hash": peer,
            "state": "delivered",
            "progress": 1.0,
            "is_incoming": incoming,
            "method": "delivery",
            "delivery_attempts": 0,
            "next_delivery_attempt_at": None,
            "title": None,
            "content": content,
            "fields": None,
            "timestamp": timestamp,
            "rssi": None,
            "snr": None,
            "quality": None,
            "is_spam": 0,
            "reply_to_hash": None,
            "attachments_stripped": None,
            "path_hops_at_send": None,
            "path_interface_at_send": None,
            "path_finding_measure": None,
            "path_row_hash_hex": None,
        },
    )


@pytest.mark.asyncio
async def test_messages_export_includes_contacts_names_and_read_state(
    mock_rns_minimal,
    temp_dir,
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        peer = "a" * 32
        _seed_message(app, msg_hash="msg1", peer=peer, timestamp=1500.0)
        app.database.contacts.add_contact("Alice", peer, lxmf_address=peer)
        app.database.announces.upsert_custom_display_name(peer, "Alice Custom")
        app.database.messages.mark_conversation_as_read(peer)
        app.database.messages.mark_notification_as_viewed(peer)

        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/maintenance/messages/export"
                and route.method == "GET"
            ):
                handler = route.handler
                break
        assert handler is not None
        response = await handler(_make_export_request())
        data = json.loads(response.body)

        assert data["format"] == MESSAGE_EXPORT_FORMAT
        assert len(data["messages"]) == 1
        assert any(c["name"] == "Alice" for c in data["contacts"])
        assert any(
            d["destination_hash"] == peer and d["display_name"] == "Alice Custom"
            for d in data["display_names"]
        )
        assert any(
            r["destination_hash"] == peer for r in data["conversation_read_state"]
        )
        assert any(
            r["destination_hash"] == peer for r in data["notification_viewed_state"]
        )


@pytest.mark.asyncio
async def test_messages_import_restores_contacts_names_and_read_state(
    mock_rns_minimal,
    temp_dir,
):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        peer = "b" * 32
        _seed_message(app, msg_hash="msg-export", peer=peer, timestamp=2000.0)
        app.database.contacts.add_contact("Bob", peer, lxmf_address=peer)
        app.database.announces.upsert_custom_display_name(peer, "Bob Name")
        app.database.messages.mark_conversation_as_read(peer)
        app.database.messages.mark_notification_as_viewed(peer)

        messages = [dict(m) for m in app.database.messages.get_all_lxmf_messages()]
        bundle = build_messages_export_bundle(app.database, messages)

        # Wipe identity-scoped tables by importing into a fresh app DB path is hard
        # so clear via DAO deletes then re-import.
        app.database.messages.delete_all_lxmf_messages()
        app.database.provider.execute("DELETE FROM contacts")
        app.database.provider.execute("DELETE FROM custom_destination_display_names")
        app.database.provider.execute("DELETE FROM lxmf_conversation_read_state")
        app.database.provider.execute("DELETE FROM notification_viewed_state")

        result = import_messages_export_bundle(app.database, bundle)
        assert result["ok"] is True
        assert result["imported"] == 1
        assert result["contacts_added"] == 1
        assert result["display_names_imported"] == 1
        assert result["read_state_imported"] >= 1

        contacts = app.database.contacts.get_contacts()
        assert any(c["name"] == "Bob" for c in contacts)
        assert app.database.announces.get_custom_display_name(peer) == "Bob Name"
        assert app.database.messages.is_conversation_unread(peer) is False


@pytest.mark.asyncio
async def test_bulk_mark_all_as_read(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        peer = "c" * 32
        _seed_message(app, msg_hash="msg-unread", peer=peer, timestamp=3000.0)
        assert app.database.messages.is_conversation_unread(peer) is True

        handler = None
        for route in app.get_routes():
            if (
                route.path == "/api/v1/lxmf/conversations/bulk-mark-as-read"
                and route.method == "POST"
            ):
                handler = route.handler
                break
        assert handler is not None
        response = await handler(_make_json_request({"mark_all": True}))
        assert response.status == 200
        assert app.database.messages.is_conversation_unread(peer) is False


@pytest.mark.asyncio
async def test_legacy_messages_only_import_still_works(mock_rns_minimal, temp_dir):
    with patch("meshchatx.meshchat.generate_ssl_certificate"):
        app = ReticulumMeshChat(
            identity=mock_rns_minimal,
            storage_dir=temp_dir,
            reticulum_config_dir=temp_dir,
        )
        peer = "d" * 32
        payload = {
            "messages": [
                {
                    "hash": "legacy1",
                    "source_hash": peer,
                    "destination_hash": "local",
                    "peer_hash": peer,
                    "state": "delivered",
                    "progress": 1.0,
                    "is_incoming": 1,
                    "method": "delivery",
                    "delivery_attempts": 0,
                    "title": None,
                    "content": "legacy",
                    "fields": None,
                    "timestamp": 1111.0,
                    "is_spam": 0,
                },
            ],
        }
        result = import_messages_export_bundle(app.database, payload)
        assert result["ok"] is True
        assert result["imported"] == 1
