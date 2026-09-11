# SPDX-License-Identifier: 0BSD

"""Global message search across connected RRC hubs.

Pure query parsing, matching, and ranking helpers plus a bounded scan over
the in-memory per-room message buffers each hub keeps. No I/O happens here;
the HTTP layer passes hub objects in and serializes the returned hit dicts.

Query grammar (whitespace separated terms):

- bare terms are AND-ed: "foo bar" requires both
- "quoted phrase" treats spaces as part of one term
- OR (or lowercase "or", or a pipe) splits the query into alternative
  groups: "a OR b -c" means (a) OR (b AND NOT c)
- a leading dash or the NOT keyword negates the next term
- field filters: from:nick (substring on nick or hex prefix on src),
  room:name (substring), hub:value (hex prefix on the hub hash or
  case-insensitive substring on the hub name), kind:value (exact kind),
  date:today|yesterday|YYYY-MM-DD (local calendar day of the message)

Matching is case-insensitive. A term can hit at three tiers, best first:
exact substring, word-anchored abbreviation (term characters appear in
order starting at a word boundary, for example "hlo" inside "hello"), and
loose subsequence fuzzy. Fuzzy tiers only apply to terms of three or more
characters and never apply to negated terms, which use exact matching so
exclusions stay predictable.
"""

import contextlib
import re
import time

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_SCAN_MESSAGES = 50000
FUZZY_MIN_TERM_LEN = 3

_FUZZY_TEXT_CAP = 2048
_WORD_RE = re.compile(r"[0-9a-zA-Z_]+")

_DEFAULT_KINDS = frozenset({"msg", "action"})
_TERM_FIELDS = frozenset({"from", "room", "hub", "kind", "date"})

_SCORE_SUBSTRING = 100.0
_SCORE_WORD_PREFIX = 50.0
_SCORE_FUZZY = 10.0
_SCORE_FIELD = 60.0


def _tokenize(text):
    """Split a query into tokens, honouring double-quoted spans."""
    tokens = []
    buf = []
    quoted = False
    for ch in text:
        if ch == '"':
            quoted = not quoted
            continue
        if not quoted and ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            continue
        buf.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _make_clause(raw, negated):
    field = None
    value = raw
    if ":" in raw:
        head, _, tail = raw.partition(":")
        if head.lower() in _TERM_FIELDS and tail:
            field = head.lower()
            value = tail
    value = value.strip()
    if not value:
        return None
    return {"field": field, "value": value, "negated": negated}


def parse_query(query):
    """Parse a query string into a list of clause groups.

    The result is a list of groups; each group is a list of clause dicts
    with keys field (None or from/room/hub/kind), value, and negated. A
    message matches when every clause in at least one group holds, so
    groups are OR-ed and clauses within a group are AND-ed. Empty or
    unparsable input returns an empty list.
    """
    if not isinstance(query, str):
        return []
    groups = []
    current = []
    negate_next = False
    for tok in _tokenize(query):
        low = tok.lower()
        if tok == "|" or low == "or":
            if current:
                groups.append(current)
                current = []
            negate_next = False
            continue
        if low == "not":
            negate_next = True
            continue
        negated = negate_next
        negate_next = False
        while tok.startswith("-") and len(tok) > 1:
            negated = not negated
            tok = tok[1:]
        if not tok or tok == "-":
            continue
        clause = _make_clause(tok, negated)
        if clause is not None:
            current.append(clause)
    if current:
        groups.append(current)
    return groups


def _msg_field(msg, name, default=None):
    if isinstance(msg, dict):
        return msg.get(name, default)
    return getattr(msg, name, default)


def _src_hex(msg):
    src = _msg_field(msg, "src")
    if isinstance(src, (bytes, bytearray)):
        return bytes(src).hex()
    if isinstance(src, str):
        return src.lower()
    return ""


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_subsequence(needle, hay):
    it = iter(hay)
    return all(c in it for c in needle)


def _word_prefix_match(needle, hay_lower):
    """True when needle is a subsequence anchored at a word start."""
    if not needle:
        return False
    first = needle[0]
    rest = needle[1:]
    for m in _WORD_RE.finditer(hay_lower):
        word = m.group(0)
        if len(word) < len(needle) or word[0] != first:
            continue
        if _is_subsequence(rest, word[1:]):
            return True
    return False


def _term_score_in(needle, hay_lower, allow_fuzzy=True):
    if not needle or not hay_lower:
        return 0.0
    if needle in hay_lower:
        return _SCORE_SUBSTRING
    if not allow_fuzzy or len(needle) < FUZZY_MIN_TERM_LEN:
        return 0.0
    capped = hay_lower[:_FUZZY_TEXT_CAP]
    if _word_prefix_match(needle, capped):
        return _SCORE_WORD_PREFIX
    if _is_subsequence(needle, capped):
        return _SCORE_FUZZY
    return 0.0


def _hub_names(hub):
    names = []
    get_display = getattr(hub, "get_display_name", None)
    if callable(get_display):
        with contextlib.suppress(Exception):
            value = get_display()
            if isinstance(value, str) and value:
                names.append(value)
    for attr in ("hub_name", "name"):
        value = getattr(hub, attr, None)
        if isinstance(value, str) and value:
            names.append(value)
    return names


def _hub_hash_hex(hub):
    hh = getattr(hub, "hub_hash", None)
    if isinstance(hh, (bytes, bytearray)):
        return bytes(hh).hex()
    if isinstance(hh, str):
        return hh.lower()
    return ""


def _hub_value_match(hub, value_lower):
    if value_lower and _hub_hash_hex(hub).startswith(value_lower):
        return True
    return any(value_lower in n.lower() for n in _hub_names(hub))


def _clause_score(clause, msg, room, hub):
    """Score one clause; zero means the clause does not hold."""
    field = clause["field"]
    value = clause["value"].lower()
    allow_fuzzy = not clause["negated"]
    if field is None:
        text = _msg_field(msg, "text")
        nick = _msg_field(msg, "nick")
        text_l = text.lower() if isinstance(text, str) else ""
        nick_l = nick.lower() if isinstance(nick, str) else ""
        return max(
            _term_score_in(value, text_l, allow_fuzzy=allow_fuzzy),
            _term_score_in(value, nick_l, allow_fuzzy=allow_fuzzy),
        )
    if field == "from":
        nick = _msg_field(msg, "nick")
        if isinstance(nick, str) and value in nick.lower():
            return _SCORE_FIELD
        if _src_hex(msg).startswith(value):
            return _SCORE_FIELD
        return 0.0
    if field == "room":
        room_l = room.lower() if isinstance(room, str) else ""
        return _SCORE_FIELD if value in room_l else 0.0
    if field == "kind":
        kind = _msg_field(msg, "kind")
        kind_l = kind.lower() if isinstance(kind, str) else ""
        return _SCORE_FIELD if kind_l == value else 0.0
    if field == "hub":
        if hub is None:
            return 0.0
        return _SCORE_FIELD if _hub_value_match(hub, value) else 0.0
    if field == "date":
        return _SCORE_FIELD if _date_matches(msg, clause["value"]) else 0.0
    return 0.0


def _date_matches(msg, value):
    """Match the message's local calendar day: today, yesterday, YYYY-MM-DD."""
    ts = _msg_field(msg, "ts")
    try:
        day = time.localtime(float(ts) / 1000.0)
    except (TypeError, ValueError, OverflowError):
        return False
    v = str(value or "").strip().lower()
    if v == "today":
        target = time.localtime()
    elif v == "yesterday":
        target = time.localtime(time.time() - 86400)
    else:
        try:
            target = time.strptime(v, "%Y-%m-%d")
        except ValueError:
            return False
    return (day.tm_year, day.tm_mon, day.tm_mday) == (
        target.tm_year,
        target.tm_mon,
        target.tm_mday,
    )


def score_message(msg, parsed, room=None, hub=None):
    """Return the ranking score for msg against a parsed query.

    Zero means no group matched. Otherwise it is the summed clause score
    of the best matching OR group. room and hub supply context for room
    and hub field clauses; room defaults to the message room field.
    """
    if isinstance(parsed, str):
        parsed = parse_query(parsed)
    if room is None:
        room = _msg_field(msg, "room")
    best = 0.0
    for group in parsed or []:
        total = 0.0
        matched = True
        for clause in group:
            score = _clause_score(clause, msg, room, hub)
            if clause["negated"]:
                if score > 0:
                    matched = False
                    break
            elif score <= 0:
                matched = False
                break
            else:
                total += score
        if matched and total > best:
            best = total
    return best


def match_message(msg, parsed, room=None, hub=None):
    """Return True when msg matches at least one parsed query group."""
    return score_message(msg, parsed, room=room, hub=hub) > 0


def _allowed_kinds(parsed):
    kinds = set(_DEFAULT_KINDS)
    for group in parsed:
        for clause in group:
            if clause["field"] == "kind" and not clause["negated"]:
                kinds.add(clause["value"].lower())
    return kinds


def _sorted_hits(hits, limit):
    hits.sort(key=lambda h: (-h["score"], -h["ts"]))
    return hits[:limit]


def search_hubs(hubs, query, limit=DEFAULT_LIMIT):
    """Search every room buffer of every hub and return ranked hits.

    hubs may be a dict of hub-hash to hub objects or any iterable of hub
    objects. Each hit is a dict with hub_hash, hub_name, room, seq, ts,
    nick, src, text, kind, mention, and score. Results sort by score
    descending then ts descending and are capped at limit (clamped to
    1..MAX_LIMIT). Scanning stops after MAX_SCAN_MESSAGES messages to
    bound CPU.
    """
    parsed = parse_query(query) if isinstance(query, str) else query
    if not parsed:
        return []
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    kinds = _allowed_kinds(parsed)
    hub_iter = hubs.values() if isinstance(hubs, dict) else hubs

    hits = []
    scanned = 0
    for hub in hub_iter or []:
        if hub is None:
            continue
        messages = getattr(hub, "messages", None)
        if not isinstance(messages, dict) or not messages:
            continue
        lock = getattr(hub, "_lock", None)
        ctx = lock if lock is not None else contextlib.nullcontext()
        with ctx:
            snapshot = [
                (room, list(msgs))
                for room, msgs in messages.items()
                if isinstance(msgs, (list, tuple))
            ]
        hub_hash = _hub_hash_hex(hub)
        names = _hub_names(hub)
        hub_name = names[0] if names else hub_hash
        for room, msgs in snapshot:
            for msg in msgs:
                scanned += 1
                if scanned > MAX_SCAN_MESSAGES:
                    return _sorted_hits(hits, limit)
                kind = _msg_field(msg, "kind")
                kind = kind.lower() if isinstance(kind, str) else "msg"
                if kind not in kinds:
                    continue
                score = score_message(msg, parsed, room=room, hub=hub)
                if score <= 0:
                    continue
                text = _msg_field(msg, "text")
                hits.append(
                    {
                        "hub_hash": hub_hash,
                        "hub_name": hub_name,
                        "room": room,
                        "seq": _msg_field(msg, "seq"),
                        "ts": _safe_int(_msg_field(msg, "ts")),
                        "nick": _msg_field(msg, "nick"),
                        "src": _src_hex(msg) or None,
                        "text": text if isinstance(text, str) else "",
                        "kind": kind,
                        "mention": bool(_msg_field(msg, "mention", False)),
                        "score": score,
                    },
                )
    return _sorted_hits(hits, limit)
