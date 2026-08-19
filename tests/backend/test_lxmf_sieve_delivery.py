# SPDX-License-Identifier: 0BSD

"""Inbound LXMF delivery applies sieve hide/ignore/folder/banish against SQLite."""

from __future__ import annotations

import secrets

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session

from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_FRIEND,
    PEER_SPAMMER,
    conversation_folder_id,
    delivery_ws_payload,
    make_inbound_lxmf,
    peer_blocked,
    prepare_messaging_app,
    set_sieve_filters,
    stored_message,
)


def _deliver(app, source, content, title=""):
    msg = make_inbound_lxmf(
        source_hash=source,
        destination_hash=LOCAL_LXMF,
        content=content,
        title=title,
    )
    app.on_lxmf_delivery(msg)
    return msg


def test_inbound_ignore_stores_message_and_suppresses_notifications(mock_app):
    app = prepare_messaging_app(mock_app)
    set_sieve_filters(
        app,
        [
            {
                "action": "ignore",
                "terms": ["alert"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    msg = _deliver(app, PEER_SPAMMER, "ALERT from mesh")
    row = stored_message(app, msg)
    assert row is not None
    assert row["content"] == "ALERT from mesh"
    assert row["peer_hash"] == PEER_SPAMMER
    payload = delivery_ws_payload(app)
    assert payload is not None
    assert payload["type"] == "lxmf.delivery"
    assert payload["sieve_suppress_notifications"] is True
    assert (
        app._lxmf_sieve_hides_peer(PEER_SPAMMER, message_content="ALERT from mesh")
        is False
    )
    assert (
        app._lxmf_sieve_suppresses_notifications(
            PEER_SPAMMER,
            message_content="ALERT from mesh",
        )
        is True
    )


def test_inbound_hide_persists_but_hides_peer(mock_app):
    app = prepare_messaging_app(mock_app)
    set_sieve_filters(
        app,
        [
            {
                "action": "hide",
                "terms": ["lurk"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    msg = _deliver(app, PEER_SPAMMER, "please lurk here")
    assert stored_message(app, msg) is not None
    assert peer_blocked(app, PEER_SPAMMER) is False
    assert (
        app._lxmf_sieve_hides_peer(
            PEER_SPAMMER,
            message_content="please lurk here",
        )
        is True
    )
    payload = delivery_ws_payload(app)
    assert payload["sieve_suppress_notifications"] is True


def test_inbound_folder_moves_conversation(mock_app):
    app = prepare_messaging_app(mock_app)
    cur = app.database.messages.create_folder("Work")
    folder_id = int(cur.lastrowid)
    set_sieve_filters(
        app,
        [
            {
                "action": "folder",
                "terms": ["invoice"],
                "folder_id": folder_id,
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    msg = _deliver(app, PEER_FRIEND, "invoice attached")
    assert stored_message(app, msg) is not None
    assert conversation_folder_id(app, PEER_FRIEND) == folder_id
    payload = delivery_ws_payload(app)
    assert payload["sieve_suppress_notifications"] is False


def test_inbound_banish_blocks_peer_and_keeps_row(mock_app):
    app = prepare_messaging_app(mock_app)
    set_sieve_filters(
        app,
        [
            {
                "action": "banish",
                "terms": ["scam"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    msg = _deliver(app, PEER_SPAMMER, "scam offer")
    assert stored_message(app, msg) is not None
    assert peer_blocked(app, PEER_SPAMMER) is True
    payload = delivery_ws_payload(app)
    assert payload["sieve_suppress_notifications"] is True


def test_inbound_blocked_source_never_upserts(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.misc.add_blocked_destination(PEER_SPAMMER)
    msg = _deliver(app, PEER_SPAMMER, "still trying")
    assert stored_message(app, msg) is None
    assert app.websocket_broadcast.call_count == 0


def test_inbound_contacts_scope_skips_strangers(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Friend", PEER_FRIEND, lxmf_address=PEER_FRIEND)
    set_sieve_filters(
        app,
        [
            {
                "action": "hide",
                "terms": ["secret"],
                "scope": "contacts",
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    stranger = _deliver(app, PEER_SPAMMER, "secret note")
    friend = _deliver(app, PEER_FRIEND, "secret note")
    assert stored_message(app, stranger) is not None
    assert stored_message(app, friend) is not None
    assert (
        app._lxmf_sieve_hides_peer(
            PEER_SPAMMER,
            message_content="secret note",
        )
        is False
    )
    assert (
        app._lxmf_sieve_hides_peer(
            PEER_FRIEND,
            message_content="secret note",
        )
        is True
    )


def test_inbound_peer_haystack_matches_contact_name(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact(
        "Mr Spammer",
        PEER_SPAMMER,
        lxmf_address=PEER_SPAMMER,
    )
    set_sieve_filters(app, [{"action": "ignore", "terms": ["spammer"]}])
    msg = _deliver(app, PEER_SPAMMER, "innocent body")
    assert stored_message(app, msg) is not None
    assert app._lxmf_sieve_suppresses_notifications(PEER_SPAMMER) is True


def test_inbound_non_matching_body_does_not_hide(mock_app):
    app = prepare_messaging_app(mock_app)
    set_sieve_filters(
        app,
        [
            {
                "action": "hide",
                "terms": ["zzzunique"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    msg = _deliver(app, PEER_FRIEND, "ordinary chat")
    assert stored_message(app, msg) is not None
    assert (
        app._lxmf_sieve_hides_peer(
            PEER_FRIEND,
            message_content="ordinary chat",
        )
        is False
    )
    payload = delivery_ws_payload(app)
    assert payload["sieve_suppress_notifications"] is False


def _make_aio_app(mock_app):
    mock_app.session_secret_key = secrets.token_urlsafe(32)
    mock_app.listen_host = "127.0.0.1"
    mock_app.listen_port = 8000
    mock_app.use_https = False
    mock_app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = mock_app._define_routes(routes)
    aio_app = web.Application()
    setup_session(aio_app, mock_app._encrypted_cookie_storage(False))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_sieve_http_put_roundtrip_and_unknown_folder(mock_app):
    prepare_messaging_app(mock_app)
    cur = mock_app.database.messages.create_folder("Inbox")
    folder_id = int(cur.lastrowid)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        csrf = await fetch_api_csrf_headers(client)
        missing = await client.put(
            "/api/v1/lxmf/sieve-filters",
            json={"filters": "nope"},
            headers=csrf,
        )
        assert missing.status == 400
        bad_folder = await client.put(
            "/api/v1/lxmf/sieve-filters",
            json={
                "filters": [
                    {
                        "action": "folder",
                        "terms": ["x"],
                        "folder_id": 999999,
                    },
                ],
            },
            headers=csrf,
        )
        assert bad_folder.status == 400
        ok = await client.put(
            "/api/v1/lxmf/sieve-filters",
            json={
                "filters": [
                    {
                        "action": "folder",
                        "terms": ["work"],
                        "folder_id": folder_id,
                        "scope": "everyone",
                    },
                ],
            },
            headers=csrf,
        )
        assert ok.status == 200
        body = await ok.json()
        assert body["filters"][0]["action"] == "folder"
        assert body["filters"][0]["folder_id"] == folder_id
        got = await client.get("/api/v1/lxmf/sieve-filters")
        assert got.status == 200
        listed = await got.json()
        assert listed["filters"][0]["terms"] == ["work"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_sieve_http_put_rejects_missing_csrf(mock_app, monkeypatch):
    monkeypatch.delenv("MESHCHAT_DISABLE_CSRF", raising=False)
    prepare_messaging_app(mock_app)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        r = await client.put(
            "/api/v1/lxmf/sieve-filters",
            json={"filters": [{"action": "ignore", "terms": ["x"]}]},
        )
        assert r.status == 403
