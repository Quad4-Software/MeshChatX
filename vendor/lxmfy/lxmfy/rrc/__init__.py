"""Reticulum Relay Chat (RRC) support for LXMFy bots.

Bots are ordinary RRC clients: they open an RNS Link to a hub, send HELLO,
join rooms, and exchange CBOR-encoded envelopes. See https://rrc.kc1awv.net/
"""

from .client import RRCClient, RRCMessage
from .constants import (
    CLIENT_NAME,
    CLIENT_VERSION,
    DEFAULT_DEST_NAME,
    RRC_VERSION,
    STATUS_CONNECTED,
    STATUS_CONNECTING,
    STATUS_DISCONNECTED,
    STATUS_FAILED,
    T_ACTION,
    T_ERROR,
    T_HELLO,
    T_JOIN,
    T_JOINED,
    T_MSG,
    T_NOTICE,
    T_PART,
    T_PARTED,
    T_PING,
    T_PONG,
    T_RESOURCE_ENVELOPE,
    T_WELCOME,
)
from .envelope import (
    decode_envelope,
    encode_envelope,
    make_envelope,
    normalize_room,
    validate_envelope,
)
from .manager import RRCManager

__all__ = [
    "CLIENT_NAME",
    "CLIENT_VERSION",
    "DEFAULT_DEST_NAME",
    "RRCClient",
    "RRCManager",
    "RRCMessage",
    "RRC_VERSION",
    "STATUS_CONNECTED",
    "STATUS_CONNECTING",
    "STATUS_DISCONNECTED",
    "STATUS_FAILED",
    "T_ACTION",
    "T_ERROR",
    "T_HELLO",
    "T_JOIN",
    "T_JOINED",
    "T_MSG",
    "T_NOTICE",
    "T_PART",
    "T_PARTED",
    "T_PING",
    "T_PONG",
    "T_RESOURCE_ENVELOPE",
    "T_WELCOME",
    "decode_envelope",
    "encode_envelope",
    "make_envelope",
    "normalize_room",
    "validate_envelope",
]
