# SPDX-License-Identifier: 0BSD

"""Identity hash parsing and session lookup helpers for RRC hub moderation."""

IDENTITY_HASH_LENS = (16, 32)


def parse_identity_hash(value):
    """Parse a hex identity hash (optional 0x prefix). Returns bytes or None."""
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if not s or len(s) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(s)
    except ValueError:
        return None
    if len(raw) not in IDENTITY_HASH_LENS:
        return None
    return raw


def peer_hex(peer, limit=12):
    if isinstance(peer, (bytes, bytearray)):
        return bytes(peer).hex()[:limit]
    return "?"


def find_sessions_by_token(server, token, room=None):
    """Return links whose nick or identity hash matches token (room-scoped if set)."""
    if not isinstance(token, str) or not token.strip():
        return []
    token_l = token.strip().lower()
    matches = []
    with server._lock:
        sessions = list(server._sessions.items())
    for link, sess in sessions:
        if room is not None:
            if room not in sess.rooms:
                continue
        nick = sess.nick
        if isinstance(nick, str) and nick.lower() == token_l:
            matches.append(link)
            continue
        peer = sess.peer
        if isinstance(peer, (bytes, bytearray)):
            hx = bytes(peer).hex()
            if hx.startswith(token_l) or hx[:12] == token_l:
                matches.append(link)
    return matches


def find_session_by_token(server, token, room=None):
    matches = find_sessions_by_token(server, token, room=room)
    if len(matches) == 1:
        return matches[0]
    return None


def resolve_identity_hash(server, token, room=None):
    """Resolve token to a full identity hash using connected sessions."""
    matches = find_sessions_by_token(server, token, room=room)
    hashes = []
    seen = set()
    for link in matches:
        sess = server._sessions.get(link)
        if sess is None:
            continue
        peer = sess.peer
        if isinstance(peer, (bytes, bytearray)):
            ph = bytes(peer)
            if ph not in seen:
                seen.add(ph)
                hashes.append(ph)
    if len(hashes) == 1:
        return hashes[0], matches
    if len(hashes) == 0:
        direct = parse_identity_hash(token)
        if direct is not None:
            return direct, []
    return None, matches


def format_ambiguous_targets(token, matches):
    n = len(matches)
    if n == 0:
        return f"no match for {token}"
    if n > 1:
        return f"ambiguous target {token} ({n} matches)"
    return f"no match for {token}"
