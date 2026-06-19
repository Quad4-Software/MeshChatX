# SPDX-License-Identifier: 0BSD

"""LXMF message blocklist: match spam phrases (substring or regex) and auto-banish."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from meshchatx.src.backend.lxmf_sieve import (
    _any_term_matches_regex,
    _any_term_matches_substring,
    _rule_scope_matches,
)

MAX_ENTRIES = 256
MAX_TERM_LEN = 512
BLOCKLIST_SCOPES = frozenset({"everyone", "contacts", "non_contacts"})
MATCH_MODES = frozenset({"substring", "regex"})
EXPORT_SCHEMA = "meshchatx.message_blocklist"
EXPORT_VERSION = 1

_REGEX_FLAGS = re.IGNORECASE | re.DOTALL


def _new_entry_id() -> str:
    return uuid.uuid4().hex[:16]


def _validate_regex_pattern(pattern: str) -> str | None:
    p = str(pattern)[:MAX_TERM_LEN]
    if not p.strip():
        return None
    try:
        re.compile(p, _REGEX_FLAGS)
    except re.error:
        return None
    return p


def _normalize_scope(raw: str | None) -> str:
    if raw in BLOCKLIST_SCOPES:
        return raw
    return "non_contacts"


def _normalize_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    text_in = item.get("text") or item.get("term") or item.get("pattern") or ""
    text = str(text_in).strip()[:MAX_TERM_LEN]
    if not text:
        return None

    match_mode = item.get("match_mode") or "substring"
    if match_mode not in MATCH_MODES:
        match_mode = "substring"

    if match_mode == "regex":
        validated = _validate_regex_pattern(text)
        if validated is None:
            return None
        text = validated

    rid = str(item.get("id") or "").strip() or _new_entry_id()
    return {
        "id": rid,
        "enabled": bool(item.get("enabled", True)),
        "text": text,
        "match_mode": match_mode,
    }


def normalize_message_blocklist(data: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and normalize blocklist settings from user input."""
    if not isinstance(data, dict):
        data = {}

    scope = _normalize_scope(data.get("scope"))
    match_peer_fields = bool(data.get("match_peer_fields", False))
    match_message = data.get("match_message")
    if match_message is None:
        match_message = True
    else:
        match_message = bool(match_message)
    if not match_peer_fields and not match_message:
        match_message = True

    entries_in = data.get("entries")
    if not isinstance(entries_in, list):
        entries_in = []

    entries: list[dict[str, Any]] = []
    for item in entries_in[:MAX_ENTRIES]:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_entry(item)
        if normalized is not None:
            entries.append(normalized)

    return {
        "scope": scope,
        "match_peer_fields": match_peer_fields,
        "match_message": match_message,
        "entries": entries,
    }


def parse_message_blocklist_json(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return normalize_message_blocklist({})
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return normalize_message_blocklist({})
    if not isinstance(data, dict):
        return normalize_message_blocklist({})
    return normalize_message_blocklist(data)


def _entry_matches(entry: dict[str, Any], text_lower: str, text_raw: str) -> bool:
    pattern = entry.get("text") or ""
    mode = entry.get("match_mode") or "substring"
    if mode == "regex":
        return _any_term_matches_regex([pattern], text_raw)
    return _any_term_matches_substring([pattern], text_lower)


def first_matching_blocklist_entry(
    blocklist: dict[str, Any],
    peer_haystack: str | None,
    *,
    is_contact: bool = False,
    message_haystack: str | None = None,
) -> dict[str, Any] | None:
    """Return the first enabled entry whose scope and targets match."""
    if not isinstance(blocklist, dict):
        return None
    if not _rule_scope_matches(blocklist, is_contact):
        return None

    peer_raw = peer_haystack or ""
    peer_lower = peer_raw.lower()
    msg_raw = message_haystack
    msg_lower = (message_haystack or "").lower()

    peer_fields = bool(blocklist.get("match_peer_fields", False))
    match_msg = bool(blocklist.get("match_message", True))

    for entry in blocklist.get("entries") or []:
        if not entry.get("enabled", True):
            continue

        peer_ok = True
        if peer_fields:
            peer_ok = _entry_matches(entry, peer_lower, peer_raw)

        msg_ok = True
        if match_msg:
            if msg_raw is None:
                continue
            msg_ok = _entry_matches(entry, msg_lower, msg_raw)

        if peer_ok and msg_ok:
            return {
                "entry_id": entry.get("id"),
                "text": entry.get("text"),
                "match_mode": entry.get("match_mode"),
            }
    return None


def build_export_document(blocklist: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_message_blocklist(blocklist)
    return {
        "schema": EXPORT_SCHEMA,
        "version": EXPORT_VERSION,
        "scope": normalized["scope"],
        "match_peer_fields": normalized["match_peer_fields"],
        "match_message": normalized["match_message"],
        "entries": [
            {
                "text": e["text"],
                "match_mode": e["match_mode"],
                "enabled": e["enabled"],
            }
            for e in normalized["entries"]
        ],
    }


def parse_import_document(
    document: dict[str, Any] | None,
    *,
    merge: bool = False,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Parse a shared blocklist document. Returns normalized blocklist or None."""
    if not isinstance(document, dict):
        return None

    schema = document.get("schema")
    if schema is not None and schema != EXPORT_SCHEMA:
        return None

    version = document.get("version")
    if version is not None and int(version) != EXPORT_VERSION:
        return None

    imported = normalize_message_blocklist(
        {
            "scope": document.get("scope"),
            "match_peer_fields": document.get("match_peer_fields"),
            "match_message": document.get("match_message"),
            "entries": document.get("entries"),
        },
    )

    if not merge:
        return imported

    base = normalize_message_blocklist(existing or {})
    seen = {e["text"].lower() for e in base["entries"]}
    merged_entries = list(base["entries"])
    for entry in imported["entries"]:
        key = entry["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        merged_entries.append(entry)
    base["entries"] = merged_entries[:MAX_ENTRIES]
    return base
