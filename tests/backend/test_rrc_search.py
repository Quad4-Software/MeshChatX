# SPDX-License-Identifier: 0BSD

"""Tests for global RRC message search across hubs and rooms."""

import json

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc import search

HUB_A = bytes.fromhex("00112233445566778899aabbccddeeff")
HUB_B = bytes.fromhex("ffeeddccbbaa99887766554433221100")


class FakeHub:
    """Minimal stand-in exposing only what the search scan touches."""

    def __init__(self, hub_hash, name=None, hub_name=None):
        self.hub_hash = hub_hash
        self.name = name or hub_hash.hex()
        self.hub_name = hub_name
        self.messages = {}

    def add(self, room, kind, nick, text, ts, seq=None, src=None):
        msg = proto.RRCMessage(kind, room, src, nick, text, ts)
        msg.seq = seq
        self.messages.setdefault(room, []).append(msg)
        return msg


def make_hub_a():
    hub = FakeHub(HUB_A, name="alpha-hub", hub_name="Alpha Relay")
    hub.add("lobby", "msg", "alice", "hello world", 1000, seq=1)
    hub.add("lobby", "msg", "bob", "goodbye world", 1001, seq=2)
    hub.add("dev", "msg", "alice", "hello developers", 1002, seq=3)
    hub.add("dev", "notice", None, "registered rooms", 1003, seq=4)
    hub.add("dev", "system", None, "connected to hub", 1004, seq=5)
    hub.add("dev", "action", "carol", "waves hello", 1005, seq=6)
    return hub


def make_hub_b():
    hub = FakeHub(HUB_B, name="beta-hub", hub_name="Beta Relay")
    hub.add("lobby", "msg", "dave", "hello from beta", 2000, seq=1)
    return hub


def test_parse_query_and_terms():
    groups = search.parse_query("foo bar")
    assert len(groups) == 1
    values = [c["value"] for c in groups[0]]
    assert values == ["foo", "bar"]
    assert all(c["field"] is None and not c["negated"] for c in groups[0])


def test_parse_query_or_groups():
    groups = search.parse_query("a OR b -c")
    assert len(groups) == 2
    assert groups[0][0]["value"] == "a"
    assert groups[1][0]["value"] == "b"
    assert groups[1][1]["value"] == "c"
    assert groups[1][1]["negated"] is True


def test_parse_query_or_lowercase_and_pipe():
    assert len(search.parse_query("a or b")) == 2
    assert len(search.parse_query("a | b")) == 2


def test_parse_query_not_keyword_and_dash():
    groups = search.parse_query("foo NOT bar")
    assert groups[0][1]["negated"] is True
    groups = search.parse_query("foo -bar")
    assert groups[0][1]["negated"] is True


def test_parse_query_quoted_phrase():
    groups = search.parse_query('a "hello world" b')
    values = [c["value"] for c in groups[0]]
    assert values == ["a", "hello world", "b"]


def test_parse_query_fields():
    groups = search.parse_query("from:alice room:lobby hub:0011 kind:msg")
    fields = {c["field"]: c["value"] for c in groups[0]}
    assert fields == {
        "from": "alice",
        "room": "lobby",
        "hub": "0011",
        "kind": "msg",
    }


def test_parse_query_empty():
    assert search.parse_query("") == []
    assert search.parse_query("   ") == []
    assert search.parse_query(None) == []
    assert search.parse_query(123) == []


def test_match_and_terms():
    hub = make_hub_a()
    parsed = search.parse_query("hello world")
    assert search.match_message(hub.messages["lobby"][0], parsed)
    assert not search.match_message(hub.messages["dev"][0], parsed)


def test_match_or_groups():
    hub = make_hub_a()
    parsed = search.parse_query("goodbye OR developers")
    hits = [
        m
        for m in hub.messages["lobby"] + hub.messages["dev"]
        if search.match_message(m, parsed)
    ]
    texts = {m.text for m in hits}
    assert texts == {"goodbye world", "hello developers"}


def test_match_negation():
    hub = make_hub_a()
    parsed = search.parse_query("world -goodbye")
    msgs = hub.messages["lobby"]
    assert search.match_message(msgs[0], parsed)
    assert not search.match_message(msgs[1], parsed)


def test_match_quoted_phrase():
    hub = make_hub_a()
    parsed = search.parse_query('"hello world"')
    assert search.match_message(hub.messages["lobby"][0], parsed)
    assert not search.match_message(hub.messages["dev"][0], parsed)


def test_match_from_filter():
    hub = make_hub_a()
    parsed = search.parse_query("from:bob")
    assert search.match_message(hub.messages["lobby"][1], parsed)
    assert not search.match_message(hub.messages["lobby"][0], parsed)


def test_match_from_src_hex_prefix():
    hub = FakeHub(HUB_A, name="x")
    msg = hub.add("lobby", "msg", None, "hi", 1, src=b"\xde\xad\xbe\xef")
    assert search.match_message(msg, search.parse_query("from:dead"))
    assert not search.match_message(msg, search.parse_query("from:beef"))


def test_match_room_filter():
    hub = make_hub_a()
    parsed = search.parse_query("room:dev hello")
    lobby_msg, dev_msgs = hub.messages["lobby"][0], hub.messages["dev"]
    assert not search.match_message(lobby_msg, parsed, room="lobby")
    assert search.match_message(dev_msgs[0], parsed, room="dev")


def test_search_hub_filter_by_hash_prefix():
    hits = search.search_hubs(
        [make_hub_a(), make_hub_b()],
        "hub:ffeedd hello",
    )
    assert len(hits) == 1
    assert hits[0]["hub_hash"] == HUB_B.hex()


def test_search_hub_filter_by_name_substring():
    hits = search.search_hubs(
        [make_hub_a(), make_hub_b()],
        "hub:beta hello",
    )
    assert len(hits) == 1
    assert hits[0]["hub_name"] == "Beta Relay"


def test_search_hit_shape():
    hits = search.search_hubs([make_hub_a()], "hello world")
    assert hits
    hit = next(h for h in hits if h["room"] == "lobby")
    assert hit["hub_hash"] == HUB_A.hex()
    assert hit["hub_name"] == "Alpha Relay"
    assert hit["room"] == "lobby"
    assert hit["kind"] == "msg"
    assert hit["nick"] == "alice"
    assert hit["text"] == "hello world"
    assert hit["ts"] == 1000
    assert hit["seq"] == 1
    assert hit["score"] > 0
    assert "src" in hit
    assert "mention" in hit


def test_search_skips_notice_and_system_by_default():
    hits = search.search_hubs([make_hub_a()], "registered OR connected")
    assert hits == []


def test_search_kind_notice_filter_includes_notices():
    hits = search.search_hubs([make_hub_a()], "kind:notice registered")
    assert len(hits) == 1
    assert hits[0]["kind"] == "notice"


def test_search_action_kind_included():
    hits = search.search_hubs([make_hub_a()], "waves")
    assert len(hits) == 1
    assert hits[0]["kind"] == "action"


def test_fuzzy_fallback_subsequence():
    hub = make_hub_a()
    parsed = search.parse_query("hlo")
    assert search.match_message(hub.messages["lobby"][0], parsed)


def test_exact_scores_above_fuzzy():
    hub = FakeHub(HUB_A, name="x")
    exact = hub.add("r", "msg", "a", "hlo said", 1)
    fuzzy = hub.add("r", "msg", "a", "hello there", 2)
    parsed = search.parse_query("hlo")
    exact_score = search.score_message(exact, parsed)
    fuzzy_score = search.score_message(fuzzy, parsed)
    assert exact_score > fuzzy_score > 0


def test_fuzzy_min_term_length():
    hub = FakeHub(HUB_A, name="x")
    msg = hub.add("r", "msg", "a", "hello", 1)
    assert not search.match_message(msg, search.parse_query("hl"))


def test_negated_term_uses_exact_only():
    hub = FakeHub(HUB_A, name="x")
    msg = hub.add("r", "msg", "a", "hello there", 1)
    # "hlo" fuzzily matches hello but negation only counts exact hits
    assert search.match_message(msg, search.parse_query("there -hlo"))
    assert not search.match_message(msg, search.parse_query("there -hello"))


def test_search_limit():
    hits = search.search_hubs([make_hub_a(), make_hub_b()], "hello", limit=1)
    assert len(hits) == 1
    hits = search.search_hubs([make_hub_a(), make_hub_b()], "hello", limit=9999)
    assert len(hits) == 4


def test_search_sorted_by_score_then_ts():
    hub = make_hub_a()
    hits = search.search_hubs([hub], "hello")
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_search_empty_query():
    assert search.search_hubs([make_hub_a()], "") == []
    assert search.search_hubs([make_hub_a()], "   ") == []


def test_search_dict_messages():
    hub = FakeHub(HUB_A, name="x")
    hub.messages["lobby"] = [
        {
            "kind": "msg",
            "nick": "alice",
            "text": "dict shaped hello",
            "ts": 7,
            "seq": 9,
            "src": "abcd",
        },
    ]
    hits = search.search_hubs([hub], "hello")
    assert len(hits) == 1
    assert hits[0]["src"] == "abcd"


def test_search_dict_of_hubs():
    hits = search.search_hubs({HUB_A.hex(): make_hub_a()}, "hello")
    assert len(hits) == 3


def test_search_scan_cap():
    hub = FakeHub(HUB_A, name="x")
    room_msgs = [
        proto.RRCMessage("msg", "r", None, "a", "hello", i) for i in range(600)
    ]
    hub.messages["r"] = room_msgs
    monkey_scan = search.MAX_SCAN_MESSAGES
    try:
        search.MAX_SCAN_MESSAGES = 500
        hits = search.search_hubs([hub], "hello")
        assert len(hits) <= 500
    finally:
        search.MAX_SCAN_MESSAGES = monkey_scan


_GARBAGE = [
    "",
    " ",
    '"',
    '"unclosed phrase',
    "-",
    "--foo",
    "- - -",
    "OR",
    "or or or",
    "|",
    "|||",
    "NOT",
    "not not",
    "from:",
    "room:",
    "hub:",
    "kind:",
    "from::",
    "::::",
    "from:alice:extra",
    "-from:",
    'a "b" c "d',
    '"""',
    "a OR -b",
    "-OR",
    "NOT OR foo",
    "from: OR room:",
    "\t\n\r",
    "a\x00b",
    "from:\x00",
    "🔥 emoji 🎉",
    "hub:zzzzzzzz",
    "-hub:",
    "kind:notice OR kind:msg",
    "a" * 500,
    "-" * 100,
    '"' * 50,
    "OR" * 30,
    "fRoM:AlIcE",
    "room:lobby room:dev",
    "-room:lobby -room:dev",
    "msg msg msg",
]


def _assert_parsed_shape(parsed):
    assert isinstance(parsed, list)
    for group in parsed:
        assert isinstance(group, list)
        for clause in group:
            assert set(clause.keys()) == {"field", "value", "negated"}
            assert clause["field"] in (None, "from", "room", "hub", "kind")
            assert isinstance(clause["value"], str) and clause["value"]
            assert isinstance(clause["negated"], bool)


@pytest.mark.parametrize("garbage", _GARBAGE)
def test_garbage_queries_do_not_crash(garbage):
    parsed = search.parse_query(garbage)
    _assert_parsed_shape(parsed)
    hub = make_hub_a()
    for msgs in hub.messages.values():
        for msg in msgs:
            assert isinstance(search.match_message(msg, parsed, hub=hub), bool)
    results = search.search_hubs([hub], garbage)
    assert isinstance(results, list)
    assert len(results) <= search.MAX_LIMIT


def _find_handler(app, path, method):
    for route in app.get_routes():
        if route.path == path and route.method == method:
            return route.handler
    return None


def _make_request(query=None):
    from unittest.mock import MagicMock

    request = MagicMock()
    request.match_info = {}
    request.query = query or {}
    return request


@pytest.mark.asyncio
async def test_rrc_search_route(mock_app):
    handler = _find_handler(mock_app, "/api/v1/rrc/search", "GET")
    assert handler is not None
    manager = mock_app.rrc_manager
    hub = manager.add_hub(HUB_A)
    msg = proto.RRCMessage("msg", "lobby", b"\x01" * 16, "alice", "hello world", 1234)
    msg.seq = 1
    hub.messages["lobby"] = [msg]

    response = await handler(_make_request(query={"q": "hello"}))
    assert response.status == 200
    data = json.loads(response.body)
    assert len(data["results"]) == 1
    hit = data["results"][0]
    assert hit["hub_hash"] == HUB_A.hex()
    assert hit["room"] == "lobby"
    assert hit["text"] == "hello world"
    assert hit["nick"] == "alice"
    assert hit["src"] == (b"\x01" * 16).hex()


@pytest.mark.asyncio
async def test_rrc_search_route_empty_query(mock_app):
    handler = _find_handler(mock_app, "/api/v1/rrc/search", "GET")
    response = await handler(_make_request(query={"q": ""}))
    assert response.status == 200
    assert json.loads(response.body) == {"results": []}

    response = await handler(_make_request(query={}))
    assert response.status == 200
    assert json.loads(response.body) == {"results": []}


@pytest.mark.asyncio
async def test_rrc_search_route_limit_clamp(mock_app):
    handler = _find_handler(mock_app, "/api/v1/rrc/search", "GET")
    manager = mock_app.rrc_manager
    hub = manager.add_hub(HUB_A)
    hub.messages["lobby"] = [
        proto.RRCMessage("msg", "lobby", None, "a", "hello", i) for i in range(5)
    ]
    response = await handler(_make_request(query={"q": "hello", "limit": "2"}))
    assert len(json.loads(response.body)["results"]) == 2
    response = await handler(_make_request(query={"q": "hello", "limit": "abc"}))
    assert len(json.loads(response.body)["results"]) == 5
    response = await handler(_make_request(query={"q": "hello", "limit": "0"}))
    assert len(json.loads(response.body)["results"]) == 1


def test_date_filter_matches_local_day():
    import time

    msg = {"text": "hi", "ts": time.time() * 1000, "kind": "msg", "nick": "a"}
    assert search.match_message(msg, "date:today")
    assert not search.match_message(msg, "date:yesterday")
    assert not search.match_message(msg, "-date:today")

    day = time.strftime("%Y-%m-%d", time.localtime(msg["ts"] / 1000.0))
    assert search.match_message(msg, f"date:{day}")
    assert not search.match_message(msg, "date:1999-01-01")

    # Invalid dates never match instead of raising.
    assert not search.match_message(msg, "date:banana")
    assert not search.match_message({"text": "hi", "ts": None}, "date:today")
