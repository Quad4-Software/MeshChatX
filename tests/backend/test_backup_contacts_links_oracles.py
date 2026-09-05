# SPDX-License-Identifier: 0BSD

"""Oracle tests for lxma:// dest-hash binding, contact import, links, restore caps."""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest
import RNS
from aiohttp import web

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.lxma_contact import bind_lxma_contact, parse_lxma_uri
from meshchatx.src.backend.message_export_bundle import import_contacts_list


def test_lxma_bind_rejects_dest_pubkey_mismatch():
    peer = RNS.Identity()
    other = RNS.Identity()
    dest_other = RNS.Destination.hash(other, "lxmf", "delivery").hex()
    dest_peer = RNS.Destination.hash(peer, "lxmf", "delivery").hex()
    assert dest_peer != dest_other
    uri = f"lxma://{dest_other}:{peer.get_public_key().hex()}"
    with pytest.raises(ValueError, match="does not match"):
        bind_lxma_contact(uri, ReticulumMeshChat._identity_from_public_key_bytes)


def test_lxma_bind_accepts_matching_dest_and_pubkey():
    peer = RNS.Identity()
    dest = RNS.Destination.hash(peer, "lxmf", "delivery").hex()
    uri = f"lxma://{dest}:{peer.get_public_key().hex()}"
    got_dest, identity = bind_lxma_contact(
        uri,
        ReticulumMeshChat._identity_from_public_key_bytes,
    )
    assert got_dest == dest
    assert identity.hash == peer.hash


def test_lxma_bind_does_not_retry_truncated_pubkey():
    peer = RNS.Identity()
    dest = RNS.Destination.hash(peer, "lxmf", "delivery").hex()
    pub = peer.get_public_key()
    assert len(pub) == 64
    padded = pub[:32] + (b"\xff" * 32)
    uri = f"lxma://{dest}:{padded.hex()}"
    calls = []

    def loader(key_bytes):
        calls.append(len(key_bytes))
        return ReticulumMeshChat._identity_from_public_key_bytes(key_bytes)

    with pytest.raises(ValueError, match="Invalid LXMA public key|does not match"):
        bind_lxma_contact(uri, loader)
    assert calls == [64]


def test_lxma_parse_rejects_non_hex_and_wrong_lengths():
    with pytest.raises(ValueError, match="format"):
        parse_lxma_uri("lxmf://aabb")
    with pytest.raises(ValueError, match="destination hash length"):
        parse_lxma_uri(f"lxma://aa:{'11' * 64}")
    with pytest.raises(ValueError, match="public key length"):
        parse_lxma_uri(f"lxma://{'aa' * 16}:{'11' * 16}")


def _ingest_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = MagicMock()
    app.config = MagicMock()
    app.database = MagicMock()
    app.reticulum = MagicMock()
    app.message_router = MagicMock()
    app.storage_dir = "/tmp/meshchat_test"
    app.config.auth_enabled.get.return_value = False
    app.database.contacts.get_contact_by_identity_hash.return_value = None
    app.database.contacts.add_contact = MagicMock()
    app.message_router.ingest_lxm_uri = MagicMock()
    app.sync_telephone_call_policy = MagicMock()
    return app


@pytest.mark.asyncio
async def test_lxm_ingest_uri_lxma_mismatch_does_not_add_contact():
    mock_app = _ingest_app()
    mock_client = MagicMock()
    mock_client.send_str = MagicMock(return_value=asyncio.sleep(0))

    peer = RNS.Identity()
    other = RNS.Identity()
    dest_other = RNS.Destination.hash(other, "lxmf", "delivery").hex()
    uri = f"lxma://{dest_other}:{peer.get_public_key().hex()}"

    with (
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=lambda coro: asyncio.create_task(coro),
        ),
        patch("meshchatx.meshchat.RNS.Identity.remember") as remember_mock,
    ):
        await mock_app.on_websocket_data_received(
            mock_client,
            {"type": "lxm.ingest_uri", "uri": uri},
        )
        await asyncio.sleep(0)

    mock_app.database.contacts.add_contact.assert_not_called()
    remember_mock.assert_not_called()
    payload = json.loads(mock_client.send_str.call_args[0][0])
    assert payload["type"] == "lxm.ingest_uri.result"
    assert payload["status"] == "error"
    assert "does not match" in payload["message"]


def test_rns_link_parse_rejects_wrong_dest_length():
    _, _, err = ReticulumMeshChat._rns_link_parse_dest_aspect(
        {"destination_hash": "aa", "aspect": "microrn.mgmt"},
    )
    assert err == "invalid_destination_hash"
    _, _, err = ReticulumMeshChat._rns_link_parse_dest_aspect(
        {"destination_hash": "aa" * 32, "aspect": "microrn.mgmt"},
    )
    assert err == "invalid_destination_hash"
    dest, aspect, err = ReticulumMeshChat._rns_link_parse_dest_aspect(
        {"destination_hash": "aa" * 16, "aspect": "microrn.mgmt"},
    )
    assert err is None
    assert dest == bytes.fromhex("aa" * 16)
    assert aspect == "microrn.mgmt"


def test_import_contacts_list_skips_invalid_hashes():
    database = MagicMock()
    added, skipped = import_contacts_list(
        database,
        [
            {"name": "Short", "remote_identity_hash": "aa"},
            {"name": "Path", "remote_identity_hash": "../evil"},
            {
                "name": "Ok",
                "remote_identity_hash": "ab" * 16,
                "lxmf_address": "cd" * 16,
            },
            {
                "name": "BadDest",
                "remote_identity_hash": "ef" * 16,
                "lxmf_address": "zz",
            },
        ],
    )
    assert added == 1
    assert skipped == 3
    database.contacts.add_contact.assert_called_once()
    kwargs = database.contacts.add_contact.call_args
    assert kwargs.args[1] == "ab" * 16
    assert kwargs.kwargs["lxmf_address"] == "cd" * 16


@pytest.mark.asyncio
async def test_identity_upload_cap_rejects_before_full_buffer():
    chunks = [b"x" * 4096, b"x" * 4096, b"x" * 70000]
    index = {"i": 0}

    async def read_chunk():
        i = index["i"]
        if i >= len(chunks):
            return b""
        index["i"] = i + 1
        return chunks[i]

    with pytest.raises(ValueError, match="too large"):
        await IdentityManager.read_upload_bytes_capped(read_chunk, max_bytes=8192)
    assert index["i"] == 3


@pytest.mark.asyncio
async def test_database_backup_download_streams_file(tmp_path):
    zip_path = tmp_path / "backup-stream.zip"
    zip_path.write_bytes(b"PK\x03\x04not-a-real-zip-but-enough")
    app = MagicMock()
    app.storage_path = str(tmp_path)
    app.database.backup_database.return_value = {"path": str(zip_path)}

    from meshchatx.src.backend.http.routes.database import register_database_routes

    routes = web.RouteTableDef()
    register_database_routes(routes, app)
    handler = None
    for route in routes:
        if (
            getattr(route, "path", None) == "/api/v1/database/backup/download"
            and getattr(route, "method", None) == "POST"
        ):
            handler = route.handler
            break
    assert handler is not None
    response = await handler(MagicMock())
    assert isinstance(response, web.FileResponse)
    assert os.path.realpath(response._path) == os.path.realpath(zip_path)
    app.database.backup_database.assert_called_once_with(str(tmp_path))
