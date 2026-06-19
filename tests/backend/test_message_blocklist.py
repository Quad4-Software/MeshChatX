# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.message_blocklist import (
    build_export_document,
    first_matching_blocklist_entry,
    normalize_message_blocklist,
    parse_import_document,
    parse_message_blocklist_json,
)


def test_parse_empty_defaults():
    out = parse_message_blocklist_json(None)
    assert out["scope"] == "non_contacts"
    assert out["match_message"] is True
    assert out["entries"] == []


def test_normalize_rejects_invalid_regex():
    raw = {
        "entries": [{"text": "[invalid", "match_mode": "regex"}],
    }
    out = normalize_message_blocklist(raw)
    assert out["entries"] == []


def test_substring_match_message():
    blocklist = normalize_message_blocklist(
        {
            "scope": "everyone",
            "match_message": True,
            "match_peer_fields": False,
            "entries": [{"text": "buy now", "match_mode": "substring"}],
        },
    )
    m = first_matching_blocklist_entry(
        blocklist,
        "alice",
        is_contact=False,
        message_haystack="click BUY NOW here",
    )
    assert m is not None
    assert m["text"] == "buy now"


def test_scope_non_contacts():
    blocklist = normalize_message_blocklist(
        {
            "scope": "non_contacts",
            "match_message": True,
            "entries": [{"text": "spam"}],
        },
    )
    assert (
        first_matching_blocklist_entry(
            blocklist,
            "peer",
            is_contact=True,
            message_haystack="spam here",
        )
        is None
    )
    assert (
        first_matching_blocklist_entry(
            blocklist,
            "peer",
            is_contact=False,
            message_haystack="spam here",
        )
        is not None
    )


def test_regex_match():
    blocklist = normalize_message_blocklist(
        {
            "match_message": True,
            "entries": [{"text": r"foo\d+", "match_mode": "regex"}],
        },
    )
    assert (
        first_matching_blocklist_entry(
            blocklist,
            "peer",
            message_haystack="hello foo99",
        )
        is not None
    )
    assert (
        first_matching_blocklist_entry(
            blocklist,
            "peer",
            message_haystack="hello bar",
        )
        is None
    )


def test_export_and_import_roundtrip():
    blocklist = normalize_message_blocklist(
        {
            "scope": "contacts",
            "match_peer_fields": True,
            "match_message": False,
            "entries": [{"text": "viagra", "match_mode": "substring"}],
        },
    )
    doc = build_export_document(blocklist)
    imported = parse_import_document(doc, merge=False)
    assert imported is not None
    assert imported["scope"] == "contacts"
    assert imported["entries"][0]["text"] == "viagra"


def test_import_merge_dedupes():
    existing = normalize_message_blocklist(
        {"entries": [{"text": "alpha"}]},
    )
    doc = build_export_document(
        normalize_message_blocklist({"entries": [{"text": "alpha"}, {"text": "beta"}]}),
    )
    merged = parse_import_document(doc, merge=True, existing=existing)
    assert merged is not None
    texts = [e["text"] for e in merged["entries"]]
    assert texts == ["alpha", "beta"]


def test_import_rejects_bad_schema():
    assert parse_import_document({"schema": "other"}, merge=False) is None
