# SPDX-License-Identifier: 0BSD

"""MessagingToolsPack: sieve, forwarder, and blocklist accept/reject oracles."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meshchatx.src.backend.lxmf_sieve import (
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
)
from meshchatx.src.backend.message_blocklist import (
    first_matching_blocklist_entry,
    normalize_message_blocklist,
)
from tests.backend.eect.harness import eect_scenario
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_ALIAS,
    PEER_FORWARD_TO,
    PEER_OTHER,
    PEER_SPAMMER,
    make_inbound_lxmf,
    prepare_messaging_app,
)

pytestmark = pytest.mark.eect


def _run_async(coro):
    if asyncio.iscoroutine(coro):
        asyncio.run(coro)


def test_eect_sieve_first_match_and_suppress():
    with eect_scenario("messaging.sieve.first_match") as (_s, _seed, rng):
        term = f"tok{rng.randint(10, 99)}"
        rules = normalize_lxmf_sieve_filters(
            [
                {"action": "ignore", "terms": [term], "enabled": False},
                {
                    "action": "hide",
                    "terms": [term],
                    "match_peer_fields": False,
                    "match_message": True,
                },
            ],
        )
        hay = f"body {term} end"
        got = first_matching_lxmf_sieve_rule(
            rules,
            "peer",
            message_haystack=hay,
        )
        assert got is not None
        assert got["action"] == "hide"


def test_eect_forwarder_source_filter(mock_app):
    with eect_scenario("messaging.forwarder.source_filter") as (_s, _seed, _rng):
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
            name="filter",
        )
        app.send_message = AsyncMock()
        miss = make_inbound_lxmf(
            source_hash=PEER_SPAMMER,
            destination_hash=LOCAL_LXMF,
            content="miss",
        )
        with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
            app.handle_forwarding(miss, context=app.current_context)
        app.send_message.assert_not_called()

        hit = make_inbound_lxmf(
            source_hash=PEER_OTHER,
            destination_hash=LOCAL_LXMF,
            content="hit",
        )
        with patch("meshchatx.meshchat.AsyncUtils.run_async", side_effect=_run_async):
            app.handle_forwarding(hit, context=app.current_context)
        app.send_message.assert_awaited_once()
        assert app.send_message.await_args.kwargs["destination_hash"] == PEER_FORWARD_TO


def test_eect_blocklist_non_contacts_only():
    with eect_scenario("messaging.blocklist.non_contacts") as (_s, _seed, _rng):
        blocklist = normalize_message_blocklist(
            {
                "scope": "non_contacts",
                "match_message": True,
                "entries": [{"text": "buy now"}],
            },
        )
        contact = first_matching_blocklist_entry(
            blocklist,
            "friend",
            is_contact=True,
            message_haystack="buy now",
        )
        stranger = first_matching_blocklist_entry(
            blocklist,
            "stranger",
            is_contact=False,
            message_haystack="buy now",
        )
        assert contact is None
        assert stranger is not None
        assert stranger["text"] == "buy now"
