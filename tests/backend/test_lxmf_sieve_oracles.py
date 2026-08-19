# SPDX-License-Identifier: 0BSD

"""Independent oracles for LXMF sieve normalize and first-match."""

from __future__ import annotations

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.lxmf_sieve import (
    MAX_RULES,
    MAX_TERM_LEN,
    MAX_TERMS_PER_RULE,
    SIEVE_ACTIONS,
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
    parse_lxmf_sieve_filters_json,
)
from tests.backend.lxmf_tools_support import (
    oracle_sieve_first_match,
    sieve_caps,
)

_TERM = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")
_SCOPE = st.sampled_from(["everyone", "contacts", "non_contacts"])
_ACTION = st.sampled_from(sorted(SIEVE_ACTIONS))
_MODE = st.sampled_from(["substring", "regex"])


def _rule_strategy():
    return st.fixed_dictionaries(
        {
            "action": _ACTION,
            "terms": st.lists(_TERM, min_size=1, max_size=4),
            "enabled": st.booleans(),
            "scope": _SCOPE,
            "match_peer_fields": st.booleans(),
            "match_message": st.booleans(),
            "match_mode": st.just("substring"),
        },
        optional={"folder_id": st.integers(min_value=1, max_value=50), "id": _TERM},
    )


def test_oracle_caps_are_the_published_limits():
    caps = sieve_caps()
    assert caps["max_rules"] == 64
    assert caps["max_terms"] == 32
    assert caps["max_term_len"] == 512
    assert caps["actions"] == frozenset({"hide", "ignore", "folder", "banish"})


def test_oracle_normalize_drops_unknown_action():
    assert normalize_lxmf_sieve_filters([{"action": "delete", "terms": ["x"]}]) == []


def test_oracle_normalize_maps_legacy_block_to_hide():
    out = normalize_lxmf_sieve_filters([{"action": "block", "terms": ["spam"]}])
    assert len(out) == 1
    assert out[0]["action"] == "hide"


def test_oracle_normalize_caps_rule_count():
    raw = [{"action": "ignore", "terms": [f"t{i}"]} for i in range(MAX_RULES + 12)]
    out = normalize_lxmf_sieve_filters(raw)
    assert len(out) == MAX_RULES


def test_oracle_normalize_caps_terms_and_term_len():
    long_term = "z" * (MAX_TERM_LEN + 40)
    extra = [f"t{i}" for i in range(MAX_TERMS_PER_RULE + 5)]
    out = normalize_lxmf_sieve_filters(
        [{"action": "hide", "terms": extra + [long_term]}],
    )
    assert len(out) == 1
    assert len(out[0]["terms"]) == MAX_TERMS_PER_RULE
    assert all(len(t) <= MAX_TERM_LEN for t in out[0]["terms"])


def test_oracle_normalize_folder_requires_int_folder_id():
    assert (
        normalize_lxmf_sieve_filters(
            [{"action": "folder", "terms": ["x"], "folder_id": None}],
        )
        == []
    )
    assert (
        normalize_lxmf_sieve_filters(
            [{"action": "folder", "terms": ["x"], "folder_id": "nope"}],
        )
        == []
    )
    kept = normalize_lxmf_sieve_filters(
        [{"action": "folder", "terms": ["x"], "folder_id": "7"}],
    )
    assert kept[0]["folder_id"] == 7


def test_oracle_parse_rejects_non_list_json():
    assert parse_lxmf_sieve_filters_json('{"action":"hide"}') == []
    assert parse_lxmf_sieve_filters_json("null") == []
    assert parse_lxmf_sieve_filters_json("1") == []


def test_oracle_json_roundtrip_of_normalized_rules():
    raw = [
        {
            "action": "folder",
            "terms": ["work"],
            "folder_id": 2,
            "scope": "contacts",
            "match_message": True,
            "id": "keep-me",
        },
        {"action": "banish", "terms": ["scam"], "scope": "non_contacts"},
    ]
    first = normalize_lxmf_sieve_filters(raw)
    again = parse_lxmf_sieve_filters_json(json.dumps(first))
    assert again == first


@pytest.mark.parametrize(
    ("scope", "is_contact", "expect_match"),
    [
        ("everyone", True, True),
        ("everyone", False, True),
        ("contacts", True, True),
        ("contacts", False, False),
        ("non_contacts", True, False),
        ("non_contacts", False, True),
    ],
)
def test_oracle_scope_matrix(scope, is_contact, expect_match):
    rules = normalize_lxmf_sieve_filters(
        [{"action": "hide", "terms": ["hit"], "scope": scope}],
    )
    got = first_matching_lxmf_sieve_rule(
        rules,
        "hit peer",
        is_contact=is_contact,
    )
    assert (got is not None) is expect_match
    if expect_match:
        assert got["action"] == "hide"


def test_oracle_first_enabled_rule_wins():
    rules = normalize_lxmf_sieve_filters(
        [
            {"action": "ignore", "terms": ["x"], "enabled": False},
            {"action": "hide", "terms": ["x"], "enabled": True},
            {"action": "banish", "terms": ["x"], "enabled": True},
        ],
    )
    got = first_matching_lxmf_sieve_rule(rules, "xx")
    assert got is not None
    assert got["action"] == "hide"


def test_oracle_regex_is_case_insensitive_dotall():
    rules = normalize_lxmf_sieve_filters(
        [{"action": "ignore", "terms": [r"spam.word"], "match_mode": "regex"}],
    )
    assert first_matching_lxmf_sieve_rule(rules, "SPAM\nWORD") is not None
    assert first_matching_lxmf_sieve_rule(rules, "ham") is None


def test_oracle_comma_separated_terms_string():
    rules = normalize_lxmf_sieve_filters(
        [{"action": "hide", "terms": "alpha, beta\ngamma"}],
    )
    assert rules[0]["terms"] == ["alpha", "beta", "gamma"]
    assert first_matching_lxmf_sieve_rule(rules, "please beta now")["action"] == "hide"


@given(
    rules_raw=st.lists(_rule_strategy(), max_size=8),
    peer=st.text(max_size=80),
    is_contact=st.booleans(),
    msg=st.one_of(st.none(), st.text(max_size=80)),
)
@settings(max_examples=60, deadline=None)
def test_oracle_first_match_matches_independent_model(
    rules_raw,
    peer,
    is_contact,
    msg,
):
    for item in rules_raw:
        if not item.get("match_peer_fields") and not item.get("match_message"):
            item["match_peer_fields"] = True
        if item["action"] == "folder":
            item["folder_id"] = item.get("folder_id") or 1
    rules = normalize_lxmf_sieve_filters(rules_raw)
    got = first_matching_lxmf_sieve_rule(
        rules,
        peer,
        is_contact=is_contact,
        message_haystack=msg,
    )
    expected = oracle_sieve_first_match(
        rules,
        peer,
        is_contact=is_contact,
        message_haystack=msg,
    )
    assert got == expected


@given(blob=st.text(max_size=200))
@settings(max_examples=40, deadline=None)
def test_oracle_parse_never_raises(blob):
    assert isinstance(parse_lxmf_sieve_filters_json(blob), list)
