# SPDX-License-Identifier: 0BSD

"""Wire protocol primitives for Reticulum Relay Chat.

This module mirrors the constants and envelope structure defined by the RRC
specification (https://rrc.kc1awv.net/) and the reference rrcd implementation.
It deliberately avoids importing Reticulum so the encoding rules, envelope
construction, and hub notice parsers can be exercised by unit tests without a
running mesh.
"""

import base64
import os
import re
import time

import cbor2

RRC_VERSION = 1

K_V = 0
K_T = 1
K_ID = 2
K_TS = 3
K_SRC = 4
K_ROOM = 5
K_BODY = 6
K_NICK = 7

T_HELLO = 1
T_WELCOME = 2

T_JOIN = 10
T_JOINED = 11
T_PART = 12
T_PARTED = 13

T_MSG = 20
T_NOTICE = 21
T_ACTION = 22

T_PING = 30
T_PONG = 31

T_ERROR = 40

T_RESOURCE_ENVELOPE = 50

B_HELLO_NAME = 0
B_HELLO_VER = 1
B_HELLO_CAPS = 2

B_WELCOME_HUB = 0
B_WELCOME_VER = 1
B_WELCOME_CAPS = 2
B_WELCOME_LIMITS = 3

L_MAX_NICK_BYTES = 0
L_MAX_ROOM_NAME_BYTES = 1
L_MAX_MSG_BODY_BYTES = 2
L_MAX_ROOMS_PER_SESSION = 3
L_RATE_LIMIT_MSGS_PER_MINUTE = 4

CAP_RESOURCE_ENVELOPE = 0
CAP_ACTION = 1

B_RES_ID = 0
B_RES_KIND = 1
B_RES_SIZE = 2
B_RES_SHA256 = 3
B_RES_ENCODING = 4

RES_KIND_NOTICE = "notice"
RES_KIND_MOTD = "motd"
RES_KIND_BLOB = "blob"

HUB_HASH_BYTES = 16

DEFAULT_DEST_NAME = "rrc.hub"
DEFAULT_MAX_NICK_BYTES = 32
DEFAULT_MAX_ROOM_BYTES = 64
DEFAULT_MAX_MSG_BYTES = 350
DEFAULT_MAX_ROOMS = 32
DEFAULT_RATE_PER_MINUTE = 240

HELLO_CLIENT_NAME = "meshchatx"
HELLO_CLIENT_VERSION = "1"


def encode(obj):
    """Encode an object into canonical CBOR bytes for the wire."""
    return cbor2.dumps(obj, canonical=True)


def decode(data):
    """Decode CBOR bytes into a Python object."""
    return cbor2.loads(data)


def load(fp):
    """Read a single CBOR value from a stream, raising ``EOFError`` at the end."""
    try:
        return cbor2.load(fp)
    except cbor2.CBORDecodeEOF as exc:
        raise EOFError from exc


def now_ms():
    """Return the current time in milliseconds."""
    return int(time.time() * 1000)


def new_msg_id():
    """Generate a random 8-byte message identifier."""
    return os.urandom(8)


_MENTION_RE_CACHE = {}


def mention_re(nick):
    """Return a compiled regex matching ``@nick`` mentions, or ``None``."""
    if not isinstance(nick, str) or not nick:
        return None
    pat = _MENTION_RE_CACHE.get(nick)
    if pat is None:
        pat = re.compile(
            r"(?<![A-Za-z0-9_])@" + re.escape(nick) + r"(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )
        if len(_MENTION_RE_CACHE) > 32:
            _MENTION_RE_CACHE.clear()
        _MENTION_RE_CACHE[nick] = pat
    return pat


def text_mentions(text, nick):
    """Return ``True`` when ``text`` mentions ``nick``."""
    pat = mention_re(nick)
    return bool(pat is not None and isinstance(text, str) and pat.search(text))


def make_envelope(msg_type, src, room=None, body=None, nick=None, mid=None, ts=None):
    """Build an RRC envelope dict ready for CBOR encoding."""
    env = {
        K_V: RRC_VERSION,
        K_T: int(msg_type),
        K_ID: mid or new_msg_id(),
        K_TS: ts or now_ms(),
        K_SRC: src,
    }
    if room is not None:
        env[K_ROOM] = room
    if body is not None:
        env[K_BODY] = body
    if nick is not None and nick != "":
        env[K_NICK] = nick
    return env


def display_name_from_hub_app_data(app_data_b64):
    """Return the hub name from a base64-encoded RRC announce, or ``None``.

    Hosted hubs announce CBOR ``app_data`` of the form
    ``{"proto": "rrc", "v": 1, "hub": name}``.
    """
    if not app_data_b64:
        return None
    try:
        raw = base64.b64decode(app_data_b64)
        obj = decode(raw)
    except Exception:
        return None
    if isinstance(obj, dict):
        name = obj.get("hub")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def normalize_nick(nick, max_bytes=DEFAULT_MAX_NICK_BYTES):
    """Normalize a nickname, returning ``None`` when empty or invalid."""
    if not isinstance(nick, str):
        return None
    n = " ".join(nick.split()).strip()
    if not n:
        return None
    encoded = n.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        n = encoded[:max_bytes].decode("utf-8", errors="ignore").strip()
        if not n:
            return None
    return n


def normalize_room(room):
    """Normalize a room name to its canonical lowercase form."""
    r = (room or "").strip().lower()
    if not r:
        msg = "room must not be empty"
        raise ValueError(msg)
    return r


# greedy .+ intentionally captures nicks containing parens like
# "user (alt) (deadbeefcafe)"
_WHO_ENTRY_RE = re.compile(
    r"(?:^|,\s)"
    r"(?:(?P<bh>[0-9a-fA-F]{32})|(?P<nick>.+?)\s\((?P<np>[0-9a-fA-F]{12})\))"
    r"(?=,\s|$)",
)


def parse_who_notice(text):
    """Parse a hub ``/who`` notice into ``(room, [(nick, hex), ...])``.

    Nicked users carry only a 12-hex prefix of their identity hash, while
    un-nicked users appear as their full hex hash. Returns ``None`` when the
    notice is not a ``/who`` response.
    """
    if not isinstance(text, str):
        return None
    prefix = "members in "
    if not text.startswith(prefix):
        return None
    sep_idx = text.find(": ", len(prefix))
    if sep_idx < 0:
        return None
    room = text[len(prefix) : sep_idx].strip().lower()
    if not room:
        return None
    body = text[sep_idx + 2 :].strip()
    entries = []
    if body and body != "(none)":
        for m in _WHO_ENTRY_RE.finditer(body):
            if m.group("nick") is not None:
                entries.append((m.group("nick").strip(), m.group("np").lower()))
            elif m.group("bh") is not None:
                entries.append((None, m.group("bh").lower()))
    return (room, entries)


def parse_room_list_notice(text):
    """Parse a hub ``/list`` notice into ``{room: topic_or_None}`` or ``None``."""
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    if stripped == "No public rooms registered":
        return {}
    lines = text.split("\n")
    if not lines or not lines[0].lstrip().startswith("Registered public rooms"):
        return None
    rooms = {}
    for line in lines[1:]:
        s = line.strip()
        if not s:
            continue
        if " - " in s:
            name, topic = s.split(" - ", 1)
            rooms[name.strip().lower()] = topic.strip() or None
        else:
            rooms[s.strip().lstrip("#").lower()] = None
    return rooms


class RRCMessage:
    """A single chat event (message, action, notice, or system line)."""

    def __init__(self, kind, room, src, nick, text, ts):
        self.kind = kind
        self.room = room
        self.src = src
        self.nick = nick
        self.text = text
        self.ts = ts
        self.mention = False

    def to_dict(self):
        """Return a JSON-serializable representation of the message."""
        src = self.src
        return {
            "kind": self.kind,
            "room": self.room,
            "src": src.hex() if isinstance(src, (bytes, bytearray)) else None,
            "nick": self.nick,
            "text": self.text if isinstance(self.text, str) else "",
            "ts": int(self.ts) if isinstance(self.ts, int) else 0,
            "mention": bool(self.mention),
        }
