# SPDX-License-Identifier: 0BSD

"""LXMF sieve filters: match peer/message text (substring or regex) and apply actions."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

MAX_RULES = 64
MAX_TERMS_PER_RULE = 32
MAX_TERM_LEN = 512

SIEVE_SCOPES = frozenset({"everyone", "contacts", "non_contacts"})
SIEVE_ACTIONS = frozenset({"hide", "ignore", "folder", "banish"})
MATCH_MODES = frozenset({"substring", "regex"})

_REGEX_FLAGS = re.IGNORECASE | re.DOTALL


def _new_rule_id() -> str:
    return uuid.uuid4().hex[:16]


def _validate_regex_terms(terms: list[str]) -> list[str] | None:
    out: list[str] = []
    for raw in terms:
        p = str(raw)[:MAX_TERM_LEN]
        if not p.strip():
            continue
        try:
            re.compile(p, _REGEX_FLAGS)
        except re.error:
            return None
        out.append(p)
    return out if out else None


def _normalize_action(raw: str | None) -> str | None:
    if raw == "block":
        return "hide"
    if raw in SIEVE_ACTIONS:
        return raw
    return None


def normalize_lxmf_sieve_filters(filters: list) -> list[dict[str, Any]]:
    """Validate and normalize a list of sieve rule dicts from user input."""
    out: list[dict[str, Any]] = []
    if not isinstance(filters, list):
        return out
    for item in filters[:MAX_RULES]:
        if not isinstance(item, dict):
            continue
        action = _normalize_action(item.get("action"))
        if action is None:
            continue

        match_mode = item.get("match_mode") or "substring"
        if match_mode not in MATCH_MODES:
            match_mode = "substring"

        match_peer_fields = item.get("match_peer_fields")
        if match_peer_fields is None:
            match_peer_fields = True
        else:
            match_peer_fields = bool(match_peer_fields)
        match_message = bool(item.get("match_message", False))
        if not match_peer_fields and not match_message:
            continue

        terms_in = item.get("terms")
        if isinstance(terms_in, str):
            terms = [t.strip() for t in re.split(r"[\n,]+", terms_in) if t.strip()]
        elif isinstance(terms_in, list):
            terms = [str(t).strip() for t in terms_in if str(t).strip()]
        else:
            terms = []
        terms = [t[:MAX_TERM_LEN] for t in terms[:MAX_TERMS_PER_RULE]]

        if match_mode == "regex":
            validated = _validate_regex_terms(terms)
            if validated is None:
                continue
            terms = validated
        else:
            if not terms:
                continue

        folder_id: int | None = None
        if action == "folder":
            try:
                folder_id = int(item.get("folder_id"))
            except (TypeError, ValueError):
                continue

        rid = str(item.get("id") or "").strip() or _new_rule_id()
        scope = item.get("scope") or item.get("applies_to")
        if scope not in SIEVE_SCOPES:
            scope = "everyone"
        out.append(
            {
                "id": rid,
                "enabled": bool(item.get("enabled", True)),
                "scope": scope,
                "match_peer_fields": match_peer_fields,
                "match_message": match_message,
                "match_mode": match_mode,
                "terms": terms,
                "action": action,
                "folder_id": folder_id,
            },
        )
    return out


def parse_lxmf_sieve_filters_json(raw: str | None) -> list[dict[str, Any]]:
    if not raw or not str(raw).strip():
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return normalize_lxmf_sieve_filters(data)


def _rule_scope_matches(rule: dict[str, Any], is_contact: bool) -> bool:
    scope = rule.get("scope") or "everyone"
    if scope not in SIEVE_SCOPES:
        scope = "everyone"
    if scope == "everyone":
        return True
    if scope == "contacts":
        return is_contact
    if scope == "non_contacts":
        return not is_contact
    return True


def _any_term_matches_substring(terms: list[str], haystack_lower: str) -> bool:
    hs = haystack_lower or ""
    for term in terms:
        t = str(term).lower()
        if t and t in hs:
            return True
    return False


def _any_term_matches_regex(terms: list[str], haystack_raw: str) -> bool:
    text = haystack_raw or ""
    for pattern in terms:
        try:
            if re.search(pattern, text, _REGEX_FLAGS):
                return True
        except re.error:
            continue
    return False


def _terms_match_rule_on_text(
    rule: dict[str, Any],
    text_lower: str,
    text_raw: str,
) -> bool:
    terms = rule.get("terms") or []
    mode = rule.get("match_mode") or "substring"
    if mode == "regex":
        return _any_term_matches_regex(terms, text_raw)
    return _any_term_matches_substring(terms, text_lower)


def first_matching_lxmf_sieve_rule(
    rules: list[dict[str, Any]],
    peer_haystack: str | None,
    *,
    is_contact: bool = False,
    message_haystack: str | None = None,
) -> dict[str, Any] | None:
    """Return the first enabled rule whose scope and match flags are satisfied."""
    peer_raw = peer_haystack or ""
    peer_lower = peer_raw.lower()
    msg_raw = message_haystack
    msg_lower = (message_haystack or "").lower()

    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if not _rule_scope_matches(rule, is_contact):
            continue

        peer_fields = rule.get("match_peer_fields", True)
        match_msg = rule.get("match_message", False)

        peer_ok = True
        if peer_fields:
            peer_ok = _terms_match_rule_on_text(rule, peer_lower, peer_raw)

        msg_ok = True
        if match_msg:
            if msg_raw is None:
                continue
            msg_ok = _terms_match_rule_on_text(rule, msg_lower, msg_raw)

        if peer_ok and msg_ok:
            return {
                "action": rule["action"],
                "folder_id": rule.get("folder_id"),
                "rule_id": rule.get("id"),
                "scope": rule.get("scope") or "everyone",
            }
    return None
