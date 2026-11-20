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

# stdlib re.search cannot be interrupted once backtracking starts (signals
# do not fire inside the C loop), so patterns with ambiguous nested
# quantification can hang the whole delivery path forever. Validation walks
# the parsed pattern and rejects repeats whose operand can match the same
# input more than one way: nested quantifiers or alternations with
# overlapping first characters. The check is conservative; a pattern that
# looks ambiguous is dropped rather than matched.

try:
    import re._constants as _re_constants
    import re._parser as _re_parser
except ImportError:  # pragma: no cover - CPython internals are stable
    _re_constants = None
    _re_parser = None

_REPEAT_OPS = frozenset(
    op
    for op in (
        getattr(_re_constants, "MAX_REPEAT", None),
        getattr(_re_constants, "MIN_REPEAT", None),
        getattr(_re_constants, "REPEAT", None),
        getattr(_re_constants, "REPEAT_ONE", None),
        getattr(_re_constants, "POSSESSIVE_REPEAT", None),
    )
    if op is not None
)
_GROUP_OPS = frozenset(
    op
    for op in (
        getattr(_re_constants, "SUBPATTERN", None),
        getattr(_re_constants, "ATOMIC_GROUP", None),
    )
    if op is not None
)
_MAXREPEAT = getattr(_re_constants, "MAXREPEAT", None)
_LITERAL_OPS = frozenset(
    op
    for op in (
        getattr(_re_constants, "LITERAL", None),
        getattr(_re_constants, "NOT_LITERAL", None),
    )
    if op is not None
)


def _first_token_ops(nodes):
    """First literal-ish atoms each alternative can start with.

    Returns a set of opaque first-token keys, or None when some alternative
    can begin with something opaque (character classes, categories, empty
    branches). Treating unknown as overlapping keeps the check safe.
    """
    keys = set()
    for branch in nodes:
        body = list(branch)
        while body:
            op, av = body[0]
            if op in _LITERAL_OPS:
                keys.add(("lit", av))
                break
            if op in _GROUP_OPS:
                body = list(av[-1]) + body[1:]
                continue
            # Anchors and assertions are zero-width; look through them.
            if op is getattr(_re_constants, "AT", None) or op in (
                getattr(_re_constants, "ASSERT", None),
                getattr(_re_constants, "ASSERT_NOT", None),
            ):
                body = body[1:]
                continue
            return None
        else:
            # Empty branch can match nothing, so it overlaps everything.
            return None
    return keys


def _repeat_operand_is_unambiguous(nodes) -> bool:
    """True when a repeat operand cannot match the same prefix two ways."""
    for op, av in nodes:
        if op in _REPEAT_OPS:
            return False
        if op is getattr(_re_constants, "BRANCH", None):
            branches = av[1]
            if len(branches) > 1 and _first_token_ops(branches) is None:
                return False
            for branch in branches:
                if not _repeat_operand_is_unambiguous(list(branch)):
                    return False
            continue
        if op in _GROUP_OPS:
            if not _repeat_operand_is_unambiguous(list(av[-1])):
                return False
            continue
        if op in (
            getattr(_re_constants, "ASSERT", None),
            getattr(_re_constants, "ASSERT_NOT", None),
        ):
            if not _repeat_operand_is_unambiguous(list(av[1])):
                return False
    return True


def _pattern_is_backtracking_safe(pattern: str) -> bool:
    """Reject user regexes whose backtracking can grow exponentially."""
    if _re_parser is None:
        return True
    try:
        parsed = _re_parser.parse(pattern, _REGEX_FLAGS)
    except Exception:
        return False

    def walk(nodes) -> bool:
        for op, av in nodes:
            if op in _REPEAT_OPS:
                _, maximum, operand = av
                repeats_many = maximum is _MAXREPEAT or maximum > 1
                if repeats_many and not _repeat_operand_is_unambiguous(list(operand)):
                    return False
                if not walk(list(operand)):
                    return False
                continue
            if op is getattr(_re_constants, "BRANCH", None):
                for branch in av[1]:
                    if not walk(list(branch)):
                        return False
                continue
            if op in _GROUP_OPS:
                if not walk(list(av[-1])):
                    return False
                continue
            if op in (
                getattr(_re_constants, "ASSERT", None),
                getattr(_re_constants, "ASSERT_NOT", None),
            ):
                # Lookahead bodies backtrack the same way; walk them too.
                if not walk(list(av[1])):
                    return False
        return True

    return walk(list(parsed))


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
        if not _pattern_is_backtracking_safe(p):
            return None
        out.append(p)
    return out or None


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
        elif not terms:
            continue

        folder_id: int | None = None
        if action == "folder":
            raw_folder_id = item.get("folder_id")
            if raw_folder_id is None:
                continue
            try:
                folder_id = int(raw_folder_id)
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
