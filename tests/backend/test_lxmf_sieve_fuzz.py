# SPDX-License-Identifier: 0BSD

import json

from hypothesis import given, settings, strategies as st

from meshchatx.src.backend.lxmf_sieve import (
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
    parse_lxmf_sieve_filters_json,
)

_json_like = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(min_value=-10_000, max_value=10_000)
    | st.floats(allow_nan=False, width=32)
    | st.text(max_size=256),
    lambda children: (
        st.lists(children, max_size=12)
        | st.dictionaries(st.text(max_size=32), children, max_size=12)
    ),
    max_leaves=40,
)


@given(_json_like)
@settings(max_examples=300, deadline=None)
def test_normalize_lxmf_sieve_filters_never_raises(data):
    if isinstance(data, list):
        normalize_lxmf_sieve_filters(data)
    else:
        normalize_lxmf_sieve_filters([data])


@given(st.text(max_size=4096))
@settings(max_examples=400, deadline=None)
def test_parse_lxmf_sieve_filters_json_never_raises(s):
    parse_lxmf_sieve_filters_json(s)


@given(st.text(max_size=4096))
@settings(max_examples=200, deadline=None)
def test_parse_json_dumped_list_never_raises(s):
    try:
        payload = json.dumps(
            [{"action": "ignore", "terms": [s], "match_mode": "substring"}]
        )
    except (TypeError, ValueError):
        return
    parse_lxmf_sieve_filters_json(payload)


@given(
    peer=st.text(max_size=512),
    msg=st.one_of(st.none(), st.text(max_size=512)),
    is_contact=st.booleans(),
    raw_terms=st.lists(st.text(max_size=64), max_size=8),
)
@settings(max_examples=250, deadline=None)
def test_first_matching_never_raises(peer, msg, is_contact, raw_terms):
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "ignore",
                "terms": raw_terms or ["x"],
                "match_peer_fields": True,
                "match_message": False,
            },
        ],
    )
    first_matching_lxmf_sieve_rule(
        rules,
        peer,
        is_contact=is_contact,
        message_haystack=msg,
    )


@given(
    peer=st.text(max_size=256),
    msg=st.text(max_size=256),
    is_contact=st.booleans(),
)
@settings(max_examples=200, deadline=None)
def test_first_matching_with_message_flag_never_raises(peer, msg, is_contact):
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "hide",
                "terms": ["a"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    first_matching_lxmf_sieve_rule(
        rules,
        peer,
        is_contact=is_contact,
        message_haystack=msg,
    )
