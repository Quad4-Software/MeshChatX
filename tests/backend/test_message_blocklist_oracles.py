# SPDX-License-Identifier: 0BSD

"""Independent oracles for message blocklist match, import, and inbound banish."""

from __future__ import annotations

import secrets

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.message_blocklist import (
    EXPORT_SCHEMA,
    EXPORT_VERSION,
    MAX_ENTRIES,
    build_export_document,
    first_matching_blocklist_entry,
    normalize_message_blocklist,
    parse_import_document,
    parse_message_blocklist_json,
)
from tests.backend.conftest import extend_meshchat_middlewares, fetch_api_csrf_headers
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_FRIEND,
    PEER_SPAMMER,
    make_inbound_lxmf,
    oracle_blocklist_first_match,
    peer_blocked,
    prepare_messaging_app,
    set_blocklist,
    stored_message,
)

_TEXT = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")


def test_oracle_default_scope_is_non_contacts():
    out = parse_message_blocklist_json(None)
    assert out["scope"] == "non_contacts"
    assert out["match_message"] is True
    assert out["match_peer_fields"] is False


def test_oracle_caps_entry_count():
    raw = {"entries": [{"text": f"t{i}"} for i in range(MAX_ENTRIES + 20)]}
    out = normalize_message_blocklist(raw)
    assert len(out["entries"]) == MAX_ENTRIES


def test_oracle_forces_a_match_target_on():
    out = normalize_message_blocklist(
        {
            "match_peer_fields": False,
            "match_message": False,
            "entries": [{"text": "x"}],
        },
    )
    assert out["match_message"] is True


@pytest.mark.parametrize(
    ("scope", "is_contact", "expect"),
    [
        ("everyone", True, True),
        ("everyone", False, True),
        ("contacts", True, True),
        ("contacts", False, False),
        ("non_contacts", True, False),
        ("non_contacts", False, True),
    ],
)
def test_oracle_blocklist_scope_matrix(scope, is_contact, expect):
    blocklist = normalize_message_blocklist(
        {
            "scope": scope,
            "match_message": True,
            "entries": [{"text": "spam", "enabled": True}],
        },
    )
    got = first_matching_blocklist_entry(
        blocklist,
        "peer",
        is_contact=is_contact,
        message_haystack="buy spam now",
    )
    assert (got is not None) is expect
    if expect:
        assert got["text"] == "spam"


def test_oracle_disabled_entry_is_skipped():
    blocklist = normalize_message_blocklist(
        {
            "scope": "everyone",
            "entries": [
                {"text": "spam", "enabled": False},
                {"text": "scam", "enabled": True},
            ],
        },
    )
    got = first_matching_blocklist_entry(
        blocklist,
        "p",
        message_haystack="this is spam and scam",
    )
    assert got["text"] == "scam"


def test_oracle_import_rejects_wrong_version():
    doc = build_export_document(
        normalize_message_blocklist({"entries": [{"text": "a"}]}),
    )
    doc["version"] = EXPORT_VERSION + 1
    assert parse_import_document(doc) is None
    assert EXPORT_SCHEMA == "meshchatx.message_blocklist"


@given(
    texts=st.lists(_TEXT, min_size=1, max_size=6),
    is_contact=st.booleans(),
    hay=st.text(max_size=80),
)
@settings(max_examples=40, deadline=None)
def test_oracle_first_match_equals_independent_model(texts, is_contact, hay):
    blocklist = normalize_message_blocklist(
        {
            "scope": "everyone",
            "match_message": True,
            "match_peer_fields": False,
            "entries": [{"text": t, "match_mode": "substring"} for t in texts],
        },
    )
    got = first_matching_blocklist_entry(
        blocklist,
        "peer",
        is_contact=is_contact,
        message_haystack=hay,
    )
    expected = oracle_blocklist_first_match(
        blocklist,
        "peer",
        is_contact=is_contact,
        message_haystack=hay,
    )
    assert got == expected


def test_inbound_blocklist_banishes_stranger(mock_app):
    app = prepare_messaging_app(mock_app)
    set_blocklist(
        app,
        {
            "scope": "non_contacts",
            "match_message": True,
            "entries": [{"text": "buy now"}],
        },
        enabled=True,
    )
    msg = make_inbound_lxmf(
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
        content="click BUY NOW",
    )
    app.on_lxmf_delivery(msg)
    assert stored_message(app, msg) is not None
    assert peer_blocked(app, PEER_SPAMMER) is True


def test_inbound_blocklist_respects_disabled_flag(mock_app):
    app = prepare_messaging_app(mock_app)
    set_blocklist(
        app,
        {
            "scope": "everyone",
            "match_message": True,
            "entries": [{"text": "buy now"}],
        },
        enabled=False,
    )
    msg = make_inbound_lxmf(
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
        content="click BUY NOW",
    )
    app.on_lxmf_delivery(msg)
    assert stored_message(app, msg) is not None
    assert peer_blocked(app, PEER_SPAMMER) is False


def test_inbound_blocklist_skips_contacts_when_scoped(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Friend", PEER_FRIEND, lxmf_address=PEER_FRIEND)
    set_blocklist(
        app,
        {
            "scope": "non_contacts",
            "match_message": True,
            "entries": [{"text": "buy now"}],
        },
        enabled=True,
    )
    msg = make_inbound_lxmf(
        source_hash=PEER_FRIEND,
        destination_hash=LOCAL_LXMF,
        content="click BUY NOW",
    )
    app.on_lxmf_delivery(msg)
    assert stored_message(app, msg) is not None
    assert peer_blocked(app, PEER_FRIEND) is False


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
async def test_blocklist_http_put_export_import(mock_app):
    prepare_messaging_app(mock_app)
    aio_app = _make_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        csrf = await fetch_api_csrf_headers(client)
        bad = await client.put(
            "/api/v1/lxmf/message-blocklist",
            json={"blocklist": []},
            headers=csrf,
        )
        assert bad.status == 400
        put = await client.put(
            "/api/v1/lxmf/message-blocklist",
            json={
                "enabled": True,
                "blocklist": {
                    "scope": "everyone",
                    "match_message": True,
                    "entries": [{"text": "viagra"}],
                },
            },
            headers=csrf,
        )
        assert put.status == 200
        body = await put.json()
        assert body["enabled"] is True
        assert body["blocklist"]["entries"][0]["text"] == "viagra"
        exported = await client.get("/api/v1/lxmf/message-blocklist/export")
        assert exported.status == 200
        doc = await exported.json()
        assert doc["schema"] == EXPORT_SCHEMA
        imported = await client.post(
            "/api/v1/lxmf/message-blocklist/import",
            json={"document": doc, "merge": False},
            headers=csrf,
        )
        assert imported.status == 200
        got = await imported.json()
        assert got["blocklist"]["entries"][0]["text"] == "viagra"
        listed = await client.get("/api/v1/lxmf/message-blocklist")
        assert listed.status == 200
        listed_body = await listed.json()
        assert listed_body["enabled"] is True
