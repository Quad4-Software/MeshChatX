# SPDX-License-Identifier: 0BSD

"""Oracles for LXMF forwarding rules, mappings, WS mutators, and handle_forwarding."""

from __future__ import annotations

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.src.backend.forwarding_manager import ForwardingManager
from meshchatx.src.backend.http.ws.handlers_lxmf import (
    handle_lxmf_forwarding_rule_add,
    handle_lxmf_forwarding_rule_delete,
    handle_lxmf_forwarding_rule_toggle,
    handle_lxmf_forwarding_rules_get,
)
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_ALIAS,
    PEER_FORWARD_TO,
    PEER_OTHER,
    PEER_SPAMMER,
    make_inbound_lxmf,
    oracle_forward_sends,
    prepare_messaging_app,
)


def _run_async(coro):
    if asyncio.iscoroutine(coro):
        asyncio.run(coro)


def _ws_client():
    client = MagicMock()
    client.send_str = MagicMock()
    return client


def test_oracle_reply_path_beats_rules(mock_app):
    app = prepare_messaging_app(mock_app)
    app.database.messages.create_forwarding_mapping(
        {
            "alias_identity_private_key": base64.b64encode(b"k").decode(),
            "alias_hash": PEER_ALIAS,
            "original_sender_hash": PEER_SPAMMER,
            "final_recipient_hash": PEER_FORWARD_TO,
            "original_destination_hash": LOCAL_LXMF,
        },
    )
    app.database.misc.create_forwarding_rule(
        identity_hash=PEER_ALIAS,
        forward_to_hash=PEER_OTHER,
        source_filter_hash=None,
        is_active=True,
        name="should-not-run",
    )
    mapping = app.database.messages.get_forwarding_mapping(alias_hash=PEER_ALIAS)
    rules = [dict(r) for r in app.database.misc.get_forwarding_rules()]
    expected = oracle_forward_sends(
        mapping=dict(mapping),
        rules=rules,
        source_hash=PEER_OTHER,
        destination_hash=PEER_ALIAS,
    )
    assert expected == [
        {
            "path": "reply",
            "destination_hash": PEER_SPAMMER,
            "sender_identity_hash": None,
        },
    ]
    app.send_message = AsyncMock()
    msg = make_inbound_lxmf(
        source_hash=PEER_OTHER,
        destination_hash=PEER_ALIAS,
        content="reply body",
    )
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        app.handle_forwarding(msg, context=app.current_context)
    app.send_message.assert_awaited_once()
    kwargs = app.send_message.await_args.kwargs
    assert kwargs["destination_hash"] == expected[0]["destination_hash"]
    assert "sender_identity_hash" not in kwargs
    assert kwargs["content"] in (b"reply body", "reply body")


def test_oracle_source_filter_and_inactive_rules(mock_app):
    app = prepare_messaging_app(mock_app)
    app.current_context.forwarding_manager = MagicMock()
    app.current_context.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": PEER_ALIAS,
    }
    app.database.misc.create_forwarding_rule(
        identity_hash=LOCAL_LXMF,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=PEER_OTHER,
        is_active=True,
        name="filter-miss",
    )
    app.database.misc.create_forwarding_rule(
        identity_hash=LOCAL_LXMF,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=None,
        is_active=False,
        name="inactive",
    )
    rules = [
        dict(r)
        for r in app.database.misc.get_forwarding_rules(
            identity_hash=LOCAL_LXMF,
            active_only=True,
        )
    ]
    expected = oracle_forward_sends(
        mapping=None,
        rules=rules,
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
    )
    assert expected == []
    app.send_message = AsyncMock()
    msg = make_inbound_lxmf(
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
        content="no forward",
    )
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        app.handle_forwarding(msg, context=app.current_context)
    app.send_message.assert_not_called()
    app.current_context.forwarding_manager.get_or_create_mapping.assert_not_called()


def test_oracle_each_matching_rule_sends_once(mock_app):
    app = prepare_messaging_app(mock_app)
    app.current_context.forwarding_manager = MagicMock()
    app.current_context.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": PEER_ALIAS,
    }
    app.database.misc.create_forwarding_rule(
        identity_hash=None,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=None,
        is_active=True,
        name="a",
    )
    app.database.misc.create_forwarding_rule(
        identity_hash=LOCAL_LXMF,
        forward_to_hash=PEER_OTHER,
        source_filter_hash=PEER_SPAMMER,
        is_active=True,
        name="b",
    )
    rules = [
        dict(r)
        for r in app.database.misc.get_forwarding_rules(
            identity_hash=LOCAL_LXMF,
            active_only=True,
        )
    ]
    expected = oracle_forward_sends(
        mapping=None,
        rules=rules,
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
    )
    assert {s["destination_hash"] for s in expected} == {PEER_FORWARD_TO, PEER_OTHER}
    app.send_message = AsyncMock()
    msg = make_inbound_lxmf(
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
        content="fanout",
        title="t",
    )
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        app.handle_forwarding(msg, context=app.current_context)
    assert app.send_message.await_count == len(expected)
    dests = [c.kwargs["destination_hash"] for c in app.send_message.await_args_list]
    assert dests == [s["destination_hash"] for s in expected]
    for call in app.send_message.await_args_list:
        assert call.kwargs["sender_identity_hash"] == PEER_ALIAS
        assert call.kwargs["content"] in (b"fanout", "fanout")


def test_oracle_inbound_delivery_triggers_forward(mock_app):
    app = prepare_messaging_app(mock_app)
    app.current_context.forwarding_manager = MagicMock()
    app.current_context.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": PEER_ALIAS,
    }
    app.database.misc.create_forwarding_rule(
        identity_hash=LOCAL_LXMF,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=None,
        is_active=True,
        name="live",
    )
    app.send_message = AsyncMock()
    msg = make_inbound_lxmf(
        source_hash=PEER_SPAMMER,
        destination_hash=LOCAL_LXMF,
        content="please forward",
    )
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        app.on_lxmf_delivery(msg)
    row = app.database.messages.get_lxmf_message_by_hash(msg.hash.hex())
    assert row is not None
    app.send_message.assert_awaited()
    assert app.send_message.await_args.kwargs["destination_hash"] == PEER_FORWARD_TO


def test_oracle_ws_add_get_toggle_delete(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _ws_client()
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            client,
            {"rule": {"name": "r1", "forward_to_hash": PEER_FORWARD_TO}},
        ),
    )
    rows = [dict(r) for r in app.database.misc.get_forwarding_rules()]
    assert len(rows) == 1
    assert rows[0]["forward_to_hash"] == PEER_FORWARD_TO
    assert rows[0]["is_active"] in (1, True)
    rule_id = rows[0]["id"]

    asyncio.run(handle_lxmf_forwarding_rules_get(app, client, {}))
    payload = json.loads(client.send_str.call_args[0][0])
    assert payload["type"] == "lxmf.forwarding.rules"
    assert payload["rules"][0]["id"] == rule_id
    assert payload["rules"][0]["forward_to_hash"] == PEER_FORWARD_TO

    asyncio.run(handle_lxmf_forwarding_rule_toggle(app, client, {"id": rule_id}))
    toggled = dict(app.database.misc.get_forwarding_rules()[0])
    assert toggled["is_active"] in (0, False)

    asyncio.run(handle_lxmf_forwarding_rule_delete(app, client, {"id": rule_id}))
    assert app.database.misc.get_forwarding_rules() == []


def test_oracle_ws_add_rejects_invalid_hashes(mock_app):
    app = prepare_messaging_app(mock_app)
    client = _ws_client()
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            client,
            {"rule": {"name": "bad", "forward_to_hash": "not-a-hash"}},
        ),
    )
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            client,
            {"rule": {"name": "empty", "forward_to_hash": ""}},
        ),
    )
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            client,
            {
                "rule": {
                    "name": "bad-filter",
                    "forward_to_hash": PEER_FORWARD_TO,
                    "source_filter_hash": "zz",
                },
            },
        ),
    )
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            client,
            {
                "rule": {
                    "name": "bad-identity",
                    "forward_to_hash": PEER_FORWARD_TO,
                    "identity_hash": "nope",
                },
            },
        ),
    )
    assert app.database.misc.get_forwarding_rules() == []


def test_oracle_ws_add_canonicalizes_hex(mock_app):
    app = prepare_messaging_app(mock_app)
    mixed = PEER_FORWARD_TO.upper()
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            _ws_client(),
            {"rule": {"name": "r1", "forward_to_hash": mixed}},
        ),
    )
    asyncio.run(
        handle_lxmf_forwarding_rule_add(
            app,
            _ws_client(),
            {
                "rule": {
                    "name": "r2",
                    "forward_to_hash": PEER_FORWARD_TO,
                    "source_filter_hash": "",
                },
            },
        ),
    )
    rows = [dict(r) for r in app.database.misc.get_forwarding_rules()]
    assert len(rows) == 2
    dests = {r["forward_to_hash"] for r in rows}
    assert dests == {PEER_FORWARD_TO}
    assert all(r["source_filter_hash"] in (None, "") for r in rows)


def test_oracle_ws_add_without_forward_to_hash_is_noop(mock_app):
    app = prepare_messaging_app(mock_app)
    asyncio.run(
        handle_lxmf_forwarding_rule_add(app, _ws_client(), {"rule": {"name": "x"}}),
    )
    assert app.database.misc.get_forwarding_rules() == []


def test_oracle_mapping_roundtrip_sqlite(mock_app):
    app = prepare_messaging_app(mock_app)
    data = {
        "alias_identity_private_key": base64.b64encode(b"priv").decode(),
        "alias_hash": PEER_ALIAS,
        "original_sender_hash": PEER_SPAMMER,
        "final_recipient_hash": PEER_FORWARD_TO,
        "original_destination_hash": LOCAL_LXMF,
    }
    app.database.messages.create_forwarding_mapping(data)
    by_alias = dict(app.database.messages.get_forwarding_mapping(alias_hash=PEER_ALIAS))
    by_pair = dict(
        app.database.messages.get_forwarding_mapping(
            original_sender_hash=PEER_SPAMMER,
            final_recipient_hash=PEER_FORWARD_TO,
        ),
    )
    assert by_alias["alias_hash"] == PEER_ALIAS
    assert by_pair["original_sender_hash"] == PEER_SPAMMER
    all_rows = app.database.messages.get_all_forwarding_mappings()
    assert len(all_rows) == 1


def test_oracle_get_or_create_mapping_reuses_row(tmp_path, db):
    mgr = ForwardingManager(db, str(tmp_path), delivery_callback=lambda m: None)
    fake_dest = MagicMock()
    fake_router = MagicMock()
    fake_router.register_delivery_identity.return_value = fake_dest
    identity = MagicMock()
    identity.hash.hex.return_value = PEER_ALIAS
    identity.get_private_key.return_value = b"alias-key"

    with (
        patch(
            "meshchatx.src.backend.forwarding_manager.RNS.Identity",
            return_value=identity,
        ),
        patch(
            "meshchatx.src.backend.forwarding_manager.create_lxmf_router",
            return_value=fake_router,
        ),
    ):
        first = mgr.get_or_create_mapping(PEER_SPAMMER, PEER_FORWARD_TO, LOCAL_LXMF)
        second = mgr.get_or_create_mapping(PEER_SPAMMER, PEER_FORWARD_TO, LOCAL_LXMF)
    assert first["alias_hash"] == PEER_ALIAS
    assert second["alias_hash"] == PEER_ALIAS
    assert len(db.messages.get_all_forwarding_mappings()) == 1
    fake_router.register_delivery_callback.assert_called()


def test_oracle_teardown_clears_alias_tables(tmp_path, db):
    mgr = ForwardingManager(db, str(tmp_path), delivery_callback=lambda m: None)
    dest = MagicMock()
    router = MagicMock()
    router.delivery_destinations = {"x": dest}
    router.propagation_destination = MagicMock()
    mgr.forwarding_destinations[PEER_ALIAS] = dest
    mgr.forwarding_routers[PEER_ALIAS] = router
    mgr.teardown()
    assert mgr.forwarding_destinations == {}
    assert mgr.forwarding_routers == {}
    router.exit_handler.assert_called_once()


def test_oracle_null_identity_rule_forwards_any_source(mock_app):
    app = prepare_messaging_app(mock_app)
    app.current_context.forwarding_manager = MagicMock()
    app.current_context.forwarding_manager.get_or_create_mapping.return_value = {
        "alias_hash": PEER_ALIAS,
    }
    app.database.misc.create_forwarding_rule(
        identity_hash=None,
        forward_to_hash=PEER_FORWARD_TO,
        source_filter_hash=None,
        is_active=True,
        name="any",
    )
    app.send_message = AsyncMock()
    msg = make_inbound_lxmf(
        source_hash=PEER_OTHER,
        destination_hash=LOCAL_LXMF,
        content="fan",
    )
    with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
        app.handle_forwarding(msg, context=app.current_context)
    app.send_message.assert_awaited_once()
    assert app.send_message.await_args.kwargs["destination_hash"] == PEER_FORWARD_TO


@pytest.mark.asyncio
async def test_oracle_ws_forwarding_add_requires_auth(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set("hash")
    client = MagicMock()
    client.request = MagicMock()
    client.send_str = AsyncMock()

    def _schedule(coro):
        return asyncio.create_task(coro)

    with (
        patch.object(mock_app, "_websocket_session_authorized", return_value=False),
        patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_schedule),
    ):
        await mock_app.on_websocket_data_received(
            client,
            {
                "type": "lxmf.forwarding.rule.add",
                "rule": {"forward_to_hash": PEER_FORWARD_TO},
            },
        )
        await asyncio.sleep(0)

    client.send_str.assert_awaited_once()
    payload = client.send_str.await_args.args[0]
    assert '"Authentication required"' in payload
    assert mock_app.database.misc.get_forwarding_rules() == []
