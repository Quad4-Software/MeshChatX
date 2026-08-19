# SPDX-License-Identifier: 0BSD

"""Independent oracles and inbound LXMF fixtures for messaging tools tests.

The matchers here are a trusted model of sieve and blocklist accept/reject.
Delivery helpers feed LXMF-shaped objects through on_lxmf_delivery against
a real SQLite identity database.
"""

from __future__ import annotations

import json
import os
import re
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import LXMF

from meshchatx.src.backend.lxmf_sieve import (
    MATCH_MODES,
    MAX_RULES,
    MAX_TERM_LEN,
    MAX_TERMS_PER_RULE,
    SIEVE_ACTIONS,
    SIEVE_SCOPES,
    normalize_lxmf_sieve_filters,
)
from meshchatx.src.backend.message_blocklist import (
    BLOCKLIST_SCOPES,
    MAX_ENTRIES,
    MAX_TERM_LEN as BLOCKLIST_MAX_TERM_LEN,
    normalize_message_blocklist,
)

LOCAL_LXMF = "11" * 16
PEER_SPAMMER = "aa" * 16
PEER_FRIEND = "bb" * 16
PEER_FORWARD_TO = "cc" * 16
PEER_ALIAS = "dd" * 16
PEER_OTHER = "ee" * 16

_REGEX_FLAGS = re.IGNORECASE | re.DOTALL


def _any_substring(terms: list[str], haystack: str) -> bool:
    hs = (haystack or "").lower()
    return any(str(term).lower() in hs for term in terms if str(term))


def _any_regex(terms: list[str], haystack: str) -> bool:
    text = haystack or ""
    for pattern in terms:
        try:
            if re.search(str(pattern), text, _REGEX_FLAGS):
                return True
        except re.error:
            continue
    return False


def _terms_hit(mode: str, terms: list[str], haystack: str) -> bool:
    if mode == "regex":
        return _any_regex(terms, haystack)
    return _any_substring(terms, haystack)


def _scope_matches(scope: str, is_contact: bool) -> bool:
    if scope == "contacts":
        return is_contact
    if scope == "non_contacts":
        return not is_contact
    return True


def oracle_sieve_first_match(
    rules: list[dict[str, Any]],
    peer_haystack: str | None,
    *,
    is_contact: bool = False,
    message_haystack: str | None = None,
) -> dict[str, Any] | None:
    """Predict the first matching sieve action without calling lxmf_sieve."""
    peer_raw = peer_haystack or ""
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        scope = rule.get("scope") or "everyone"
        if not _scope_matches(scope, is_contact):
            continue
        mode = rule.get("match_mode") or "substring"
        terms = list(rule.get("terms") or [])
        peer_ok = True
        if rule.get("match_peer_fields", True):
            peer_ok = _terms_hit(mode, terms, peer_raw)
        msg_ok = True
        if rule.get("match_message", False):
            if message_haystack is None:
                continue
            msg_ok = _terms_hit(mode, terms, message_haystack)
        if peer_ok and msg_ok:
            return {
                "action": rule["action"],
                "folder_id": rule.get("folder_id"),
                "rule_id": rule.get("id"),
                "scope": scope if scope in SIEVE_SCOPES else "everyone",
            }
    return None


def oracle_blocklist_first_match(
    blocklist: dict[str, Any],
    peer_haystack: str | None,
    *,
    is_contact: bool = False,
    message_haystack: str | None = None,
) -> dict[str, Any] | None:
    """Predict the first matching blocklist entry without calling message_blocklist."""
    if not isinstance(blocklist, dict):
        return None
    if not _scope_matches(blocklist.get("scope") or "non_contacts", is_contact):
        return None
    peer_raw = peer_haystack or ""
    peer_fields = bool(blocklist.get("match_peer_fields", False))
    match_msg = bool(blocklist.get("match_message", True))
    for entry in blocklist.get("entries") or []:
        if not entry.get("enabled", True):
            continue
        mode = entry.get("match_mode") or "substring"
        terms = [entry.get("text") or ""]
        peer_ok = True
        if peer_fields:
            peer_ok = _terms_hit(mode, terms, peer_raw)
        msg_ok = True
        if match_msg:
            if message_haystack is None:
                continue
            msg_ok = _terms_hit(mode, terms, message_haystack)
        if peer_ok and msg_ok:
            return {
                "entry_id": entry.get("id"),
                "text": entry.get("text"),
                "match_mode": entry.get("match_mode"),
            }
    return None


def oracle_forward_sends(
    *,
    mapping: dict[str, Any] | None,
    rules: list[dict[str, Any]],
    source_hash: str,
    destination_hash: str,
) -> list[dict[str, Any]]:
    """Predict send_message calls from handle_forwarding inputs.

    Reply path wins when a mapping exists for the destination alias.
    Otherwise every active rule whose identity matches dest (or is null)
    and whose source filter is empty or equals source produces one send.
    """
    if mapping:
        return [
            {
                "path": "reply",
                "destination_hash": mapping["original_sender_hash"],
                "sender_identity_hash": None,
            },
        ]
    sends: list[dict[str, Any]] = []
    for rule in rules:
        active = rule.get("is_active")
        if active in (0, False):
            continue
        identity = rule.get("identity_hash")
        if identity and identity != destination_hash:
            continue
        filt = rule.get("source_filter_hash")
        if filt and filt != source_hash:
            continue
        sends.append(
            {
                "path": "forward",
                "destination_hash": rule["forward_to_hash"],
                "sender_identity_hash": "alias",
            },
        )
    return sends


def make_inbound_lxmf(
    *,
    source_hash: str,
    destination_hash: str,
    content: str = "hello",
    title: str = "",
    fields: dict | None = None,
    msg_hash: bytes | None = None,
) -> SimpleNamespace:
    """Build an LXMF-shaped inbound object that convert_lxmf_message_to_dict accepts."""
    payload = content.encode("utf-8") if isinstance(content, str) else content
    heading = title.encode("utf-8") if isinstance(title, str) else title
    stored_fields = dict(fields or {})
    msg = SimpleNamespace(
        hash=msg_hash if msg_hash is not None else os.urandom(32),
        source_hash=bytes.fromhex(source_hash),
        destination_hash=bytes.fromhex(destination_hash),
        content=payload,
        title=heading,
        incoming=True,
        progress=1.0,
        delivery_attempts=0,
        next_delivery_attempt=None,
        rssi=None,
        snr=None,
        q=None,
        timestamp=time.time(),
        state=LXMF.LXMessage.DELIVERED,
        method=LXMF.LXMessage.DIRECT,
        signature_validated=True,
        fields=stored_fields,
        stamp=None,
        outbound_ticket=None,
        desired_method=LXMF.LXMessage.DIRECT,
        stamp_cost=None,
    )
    msg.get_fields = lambda: dict(msg.fields)
    return msg


def prepare_messaging_app(app, *, local_hash: str = LOCAL_LXMF):
    """Make mock_app safe for inbound LXMF delivery against the real test DB."""
    ctx = app.current_context
    ctx.running = True
    ctx.database = app.database
    ctx.config = app.config
    if ctx.local_lxmf_destination is None:
        ctx.local_lxmf_destination = SimpleNamespace()
    ctx.local_lxmf_destination.hexhash = local_hash
    ctx.local_lxmf_destination.hash = bytes.fromhex(local_hash)
    app.config.lxmf_flood_protection_enabled.set(False)
    app.config.block_all_from_strangers.set(False)
    app.config.block_attachments_from_strangers.set(False)
    app.config.message_blocklist_enabled.set(False)
    app.config.lxmf_sieve_filters_json.set("[]")
    if (
        not hasattr(app, "_lxmf_incoming_timestamps")
        or app._lxmf_incoming_timestamps is None
    ):
        app._lxmf_incoming_timestamps = []
    reticulum = getattr(app, "reticulum", None)
    if reticulum is not None:
        reticulum.get_packet_rssi = MagicMock(return_value=None)
        reticulum.get_packet_snr = MagicMock(return_value=None)
        reticulum.get_packet_q = MagicMock(return_value=None)
    return app


def set_sieve_filters(app, filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = normalize_lxmf_sieve_filters(filters)
    app.config.lxmf_sieve_filters_json.set(json.dumps(normalized))
    return normalized


def set_blocklist(
    app, blocklist: dict[str, Any], *, enabled: bool = True
) -> dict[str, Any]:
    normalized = normalize_message_blocklist(blocklist)
    app.config.message_blocklist_json.set(json.dumps(normalized))
    app.config.message_blocklist_enabled.set(enabled)
    return normalized


def stored_message(app, msg) -> dict | None:
    row = app.database.messages.get_lxmf_message_by_hash(msg.hash.hex())
    return dict(row) if row is not None else None


def peer_blocked(app, peer_hash: str) -> bool:
    return bool(app.database.misc.is_destination_blocked(peer_hash))


def conversation_folder_id(app, peer_hash: str) -> int | None:
    row = app.database.messages.get_conversation_folder(peer_hash)
    if row is None:
        return None
    return dict(row).get("folder_id")


def delivery_ws_payload(app) -> dict | None:
    call = app.websocket_broadcast.call_args
    if not call:
        return None
    raw = call[0][0]
    if not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def sieve_caps() -> dict[str, Any]:
    return {
        "max_rules": MAX_RULES,
        "max_terms": MAX_TERMS_PER_RULE,
        "max_term_len": MAX_TERM_LEN,
        "actions": SIEVE_ACTIONS,
        "scopes": SIEVE_SCOPES,
        "match_modes": MATCH_MODES,
        "blocklist_max_entries": MAX_ENTRIES,
        "blocklist_max_term_len": BLOCKLIST_MAX_TERM_LEN,
        "blocklist_scopes": BLOCKLIST_SCOPES,
    }
