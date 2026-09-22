# SPDX-License-Identifier: 0BSD

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


def test_filter_announced_dicts_empty_search_matches_all():
    """Empty substring matches every string in Python; callers should normalize UI input."""
    items = [
        {"display_name": "AAA"},
        {"destination_hash": "0123abcd"},
        {"identity_hash": "fedcba"},
    ]
    out = filter_announced_dicts_by_search_query(items, "")
    assert len(out) == 3


def test_filter_announced_dicts_whitespace_search_can_match():
    items = [
        {"display_name": " Hi "},
        {"destination_hash": "99"},
    ]
    out = filter_announced_dicts_by_search_query(items, " ")
    assert len(out) == 1
    assert out[0]["display_name"] == " Hi "


def test_filter_announced_dicts_by_search_query_case_insensitive():
    items = [
        {"display_name": "CamelCaseName", "destination_hash": "z" * 32},
    ]
    out = filter_announced_dicts_by_search_query(items, "camelcase")
    assert len(out) == 1


def test_search_messages_fts_substring_mid_token(db):
    """Trigram FTS must match mid-token substrings like LIKE %term% did."""
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        m = make_message(peer, 1)
        m["content"] = "aaaxyzbespokebbb"
        m["title"] = "t"
        db.messages.upsert_lxmf_message(m)

    if db.messages.lxmf_fts_match("xyzbespoke") is None:
        import pytest

        pytest.skip("lxmf_messages_fts not present")
    rows = handler.search_messages("local", "xyzbespoke")
    assert any(r["peer_hash"] == peer for r in rows)


def test_search_messages_short_term_like_fallback(db):
    """Queries under the trigram minimum still resolve via LIKE."""
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        m = make_message(peer, 1)
        m["content"] = "body with zz token"
        db.messages.upsert_lxmf_message(m)

    assert db.messages.lxmf_fts_match("zz") is None
    rows = handler.search_messages("local", "zz")
    assert any(r["peer_hash"] == peer for r in rows)


def test_search_messages_fts_tracks_update_and_delete(db):
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        m = make_message(peer, 1)
        m["content"] = "firstuniquevalue"
        db.messages.upsert_lxmf_message(m)

    if db.messages.lxmf_fts_match("firstuniquevalue") is None:
        import pytest

        pytest.skip("lxmf_messages_fts not present")

    assert any(
        r["peer_hash"] == peer
        for r in handler.search_messages("local", "firstuniquevalue")
    )

    with db.provider:
        db.provider.execute(
            "UPDATE lxmf_messages SET content = ? WHERE peer_hash = ?",
            ("seconduniquevalue", peer),
        )
    rows = handler.search_messages("local", "firstuniquevalue")
    assert not any(r["peer_hash"] == peer for r in rows)
    assert any(
        r["peer_hash"] == peer
        for r in handler.search_messages("local", "seconduniquevalue")
    )

    with db.provider:
        db.provider.execute(
            "DELETE FROM lxmf_messages WHERE peer_hash = ?",
            (peer,),
        )
    rows = handler.search_messages("local", "seconduniquevalue")
    assert not any(r["peer_hash"] == peer for r in rows)


def test_search_messages_fts_quotes_special_chars(db):
    """FTS5 syntax characters in user input must not error or inject."""
    handler = MessageHandler(db)
    peer = secrets.token_hex(16)
    with db.provider:
        m = make_message(peer, 1)
        m["content"] = 'quoted "inner" text here'
        db.messages.upsert_lxmf_message(m)

    if db.messages.lxmf_fts_match(' "inner" ') is None:
        import pytest

        pytest.skip("lxmf_messages_fts not present")
    rows = handler.search_messages("local", ' "inner" ')
    assert any(r["peer_hash"] == peer for r in rows)
    # NEAR/AND/column syntax must be treated as literal text, not a crash.
    handler.search_messages("local", 'content:"x" NEAR y OR z*')
