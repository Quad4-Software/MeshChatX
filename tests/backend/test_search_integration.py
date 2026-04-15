"""Integration tests for conversation list search and announce search filtering."""

import secrets
import time

from meshchatx.src.backend.announce_manager import (
    filter_announced_dicts_by_search_query,
)
from meshchatx.src.backend.message_handler import MessageHandler
from tests.backend.test_performance_hotpaths import make_message


def test_get_conversations_search_finds_peer_via_older_message(db):
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        m_old = make_message(peer, 1)
        m_old["content"] = "unique_old_body_xyz"
        m_old["title"] = "t1"
        m_old["timestamp"] = time.time() - 100

        m_new = make_message(peer, 2)
        m_new["content"] = "latest"
        m_new["title"] = "t2"
        m_new["timestamp"] = time.time()

        db.messages.upsert_lxmf_message(m_old)
        db.messages.upsert_lxmf_message(m_new)

    rows = handler.get_conversations("local", search="unique_old_body")
    dest_hashes = {r["peer_hash"] for r in rows}
    assert peer in dest_hashes


def test_get_conversations_search_matches_custom_display_name(db):
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        db.messages.upsert_lxmf_message(make_message(peer, 0))
        db.announces.upsert_custom_display_name(peer, "CustomDisplayUniqueZ")

    rows = handler.get_conversations("local", search="CustomDisplayUnique")
    assert any(r["peer_hash"] == peer for r in rows)


def test_filter_announced_dicts_by_search_query_display_name():
    items = [
        {
            "display_name": "AlphaOnlyName",
            "destination_hash": "c" * 32,
            "identity_hash": "e" * 32,
        },
        {
            "display_name": "BetaOtherName",
            "destination_hash": "d" * 32,
            "identity_hash": "e" * 32,
        },
    ]
    out = filter_announced_dicts_by_search_query(items, "AlphaOnly")
    assert len(out) == 1
    assert out[0]["destination_hash"] == "c" * 32


def test_filter_announced_dicts_by_search_query_custom_display_name():
    items = [
        {
            "display_name": "Anonymous Peer",
            "custom_display_name": "CustomNickUniqueSearch",
            "destination_hash": "f" * 32,
            "identity_hash": "1" * 32,
        },
    ]
    out = filter_announced_dicts_by_search_query(items, "customnickunique")
    assert len(out) == 1


def test_filter_announced_dicts_by_search_query_destination_hash_substring():
    dest = "ab" + "0" * 30
    items = [
        {"display_name": "X", "destination_hash": dest, "identity_hash": "y" * 32},
    ]
    out = filter_announced_dicts_by_search_query(items, "ab00")
    assert len(out) == 1


def test_filter_announced_dicts_by_search_query_case_insensitive():
    items = [
        {"display_name": "CamelCaseName", "destination_hash": "z" * 32},
    ]
    out = filter_announced_dicts_by_search_query(items, "camelcase")
    assert len(out) == 1
