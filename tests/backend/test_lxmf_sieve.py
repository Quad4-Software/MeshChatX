# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.lxmf_sieve import (
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
    parse_lxmf_sieve_filters_json,
)


def test_parse_empty_and_invalid():
    assert parse_lxmf_sieve_filters_json(None) == []
    assert parse_lxmf_sieve_filters_json("") == []
    assert parse_lxmf_sieve_filters_json("not json") == []
    assert parse_lxmf_sieve_filters_json("{}") == []


def test_normalize_drops_bad_and_keeps_good():
    raw = [
        {"action": "nope", "terms": ["x"]},
        {"action": "ignore", "terms": ["spam"], "enabled": True, "id": "a1"},
        {"action": "folder", "terms": ["work"], "folder_id": 3, "id": "b2"},
        {"action": "folder", "terms": ["bad"], "folder_id": "nan"},
    ]
    out = normalize_lxmf_sieve_filters(raw)
    assert len(out) == 2
    assert out[0]["action"] == "ignore"
    assert out[0]["terms"] == ["spam"]
    assert out[0]["scope"] == "everyone"
    assert out[0]["match_peer_fields"] is True
    assert out[0]["match_message"] is False
    assert out[0]["match_mode"] == "substring"
    assert out[1]["action"] == "folder"
    assert out[1]["folder_id"] == 3
    assert out[1]["scope"] == "everyone"


def test_normalize_drops_when_both_match_targets_disabled():
    assert (
        normalize_lxmf_sieve_filters(
            [
                {
                    "action": "ignore",
                    "terms": ["a"],
                    "match_peer_fields": False,
                    "match_message": False,
                },
            ],
        )
        == []
    )


def test_first_match_respects_order_and_enabled():
    rules = normalize_lxmf_sieve_filters(
        [
            {"action": "ignore", "terms": ["foo"], "enabled": True},
            {"action": "hide", "terms": ["foo"], "enabled": True},
        ],
    )
    m = first_matching_lxmf_sieve_rule(rules, "Mr foo bar")
    assert m["action"] == "ignore"

    rules2 = normalize_lxmf_sieve_filters(
        [
            {"action": "ignore", "terms": ["foo"], "enabled": False},
            {"action": "block", "terms": ["foo"], "enabled": True},
        ],
    )
    m2 = first_matching_lxmf_sieve_rule(rules2, "Mr foo bar")
    assert m2["action"] == "hide"


def test_legacy_block_action_normalizes_to_hide():
    rules = normalize_lxmf_sieve_filters([{"action": "block", "terms": ["z"]}])
    assert rules[0]["action"] == "hide"


def test_case_insensitive_substring():
    rules = normalize_lxmf_sieve_filters([{"action": "hide", "terms": ["SpAm"]}])
    assert first_matching_lxmf_sieve_rule(rules, "user spammer")["action"] == "hide"
    assert first_matching_lxmf_sieve_rule(rules, "USER") is None


def test_parse_json_roundtrip():
    s = '[{"id":"1","enabled":true,"terms":["a"],"action":"ignore","folder_id":null}]'
    got = parse_lxmf_sieve_filters_json(s)
    assert len(got) == 1
    assert got[0]["terms"] == ["a"]
    assert got[0]["scope"] == "everyone"


def test_normalize_preserves_scope():
    out = normalize_lxmf_sieve_filters(
        [
            {"action": "ignore", "terms": ["x"], "scope": "contacts"},
            {"action": "hide", "terms": ["y"], "scope": "non_contacts"},
        ],
    )
    assert out[0]["scope"] == "contacts"
    assert out[1]["scope"] == "non_contacts"


def test_normalize_invalid_scope_becomes_everyone():
    out = normalize_lxmf_sieve_filters(
        [{"action": "ignore", "terms": ["a"], "scope": "unknown"}],
    )
    assert out[0]["scope"] == "everyone"


def test_first_match_scope_contacts():
    rules = normalize_lxmf_sieve_filters(
        [{"action": "hide", "terms": ["foo"], "scope": "contacts"}],
    )
    assert first_matching_lxmf_sieve_rule(rules, "Mr foo", is_contact=False) is None
    assert (
        first_matching_lxmf_sieve_rule(rules, "Mr foo", is_contact=True)["action"]
        == "hide"
    )


def test_first_match_scope_non_contacts():
    rules = normalize_lxmf_sieve_filters(
        [{"action": "ignore", "terms": ["foo"], "scope": "non_contacts"}],
    )
    assert first_matching_lxmf_sieve_rule(rules, "foo bar", is_contact=True) is None
    assert (
        first_matching_lxmf_sieve_rule(rules, "foo bar", is_contact=False)["action"]
        == "ignore"
    )


def test_order_skips_non_matching_scope():
    rules = normalize_lxmf_sieve_filters(
        [
            {"action": "ignore", "terms": ["spam"], "scope": "contacts"},
            {"action": "hide", "terms": ["spam"], "scope": "everyone"},
        ],
    )
    r = first_matching_lxmf_sieve_rule(rules, "spam here", is_contact=False)
    assert r["action"] == "hide"


def test_regex_invalid_dropped():
    assert (
        normalize_lxmf_sieve_filters(
            [{"action": "ignore", "terms": ["("], "match_mode": "regex"}],
        )
        == []
    )


def test_regex_matches_peer():
    rules = normalize_lxmf_sieve_filters(
        [{"action": "hide", "terms": [r"foo\d+"], "match_mode": "regex"}],
    )
    assert first_matching_lxmf_sieve_rule(rules, "x FOO99 y")["action"] == "hide"
    assert first_matching_lxmf_sieve_rule(rules, "x bar y") is None


def test_message_only_match():
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "ignore",
                "terms": ["alert"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    assert (
        first_matching_lxmf_sieve_rule(
            rules,
            "nothing",
            message_haystack="my alert here",
        )["action"]
        == "ignore"
    )
    assert (
        first_matching_lxmf_sieve_rule(
            rules,
            "alert in peer",
            message_haystack="no",
        )
        is None
    )


def test_match_message_requires_message_haystack():
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "ignore",
                "terms": ["a"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    assert first_matching_lxmf_sieve_rule(rules, "peer", message_haystack=None) is None


def test_peer_and_message_both_must_match_when_enabled():
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "ignore",
                "terms": ["peerterm", "msgterm"],
                "match_peer_fields": True,
                "match_message": True,
            },
        ],
    )
    assert (
        first_matching_lxmf_sieve_rule(
            rules,
            "has peerterm only",
            message_haystack="nothing",
        )
        is None
    )
    assert (
        first_matching_lxmf_sieve_rule(
            rules,
            "has peerterm",
            message_haystack="and msgterm here",
        )["action"]
        == "ignore"
    )


def test_banish_action_normalized():
    rules = normalize_lxmf_sieve_filters([{"action": "banish", "terms": ["x"]}])
    assert rules[0]["action"] == "banish"
