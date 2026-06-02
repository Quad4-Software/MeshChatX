# SPDX-License-Identifier: 0BSD

"""Server-wide trusted and banned identity lists for hosted RRC hubs."""

import os
import threading
import tomllib

from meshchatx.src.backend.rrc.identity_util import parse_identity_hash


def load_hub_policy(path):
    """Load trusted_identities and banned_identities from hub.toml."""
    trusted = set()
    banned = set()
    if not path or not os.path.isfile(path):
        return trusted, banned
    try:
        with open(path, "rb") as f:
            doc = tomllib.load(f)
    except Exception:
        return trusted, banned
    for key, target in (("trusted_identities", trusted), ("banned_identities", banned)):
        items = doc.get(key)
        if isinstance(items, list):
            for item in items:
                h = parse_identity_hash(str(item))
                if h is not None:
                    target.add(h)
    return trusted, banned


def save_hub_policy(path, trusted, banned):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    lines = []
    if trusted:
        items = ", ".join(
            '"' + bytes(h).hex() + '"' for h in sorted(trusted, key=bytes)
        )
        lines.append(f"trusted_identities = [{items}]")
    else:
        lines.append("trusted_identities = []")
    if banned:
        items = ", ".join('"' + bytes(h).hex() + '"' for h in sorted(banned, key=bytes))
        lines.append(f"banned_identities = [{items}]")
    else:
        lines.append("banned_identities = []")
    text = "\n".join(lines) + "\n"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class HubPolicy:
    """Trusted (server operator) and globally banned identity sets."""

    def __init__(self, path=None):
        self.path = path
        self._lock = threading.Lock()
        self.trusted = set()
        self.banned = set()
        if path:
            self.load()

    def load(self):
        if not self.path:
            return
        trusted, banned = load_hub_policy(self.path)
        with self._lock:
            self.trusted = trusted
            self.banned = banned

    def save(self):
        if not self.path:
            return
        with self._lock:
            trusted = set(self.trusted)
            banned = set(self.banned)
        save_hub_policy(self.path, trusted, banned)

    def is_trusted(self, peer_hash):
        if not isinstance(peer_hash, (bytes, bytearray)):
            return False
        with self._lock:
            return bytes(peer_hash) in self.trusted

    def is_server_op(self, peer_hash):
        return self.is_trusted(peer_hash)

    def is_banned(self, peer_hash):
        if not isinstance(peer_hash, (bytes, bytearray)):
            return False
        with self._lock:
            return bytes(peer_hash) in self.banned

    def add_ban(self, peer_hash):
        with self._lock:
            self.banned.add(bytes(peer_hash))

    def remove_ban(self, peer_hash):
        with self._lock:
            self.banned.discard(bytes(peer_hash))

    def list_banned_hex(self):
        with self._lock:
            return sorted(h.hex() for h in self.banned)

    def to_dict(self):
        with self._lock:
            return {
                "trusted_identities": sorted(h.hex() for h in self.trusted),
                "banned_identities": sorted(h.hex() for h in self.banned),
            }

    def apply_config(self, trusted_list=None, banned_list=None):
        if trusted_list is not None:
            trusted = set()
            for item in trusted_list:
                h = parse_identity_hash(str(item))
                if h is not None:
                    trusted.add(h)
            with self._lock:
                self.trusted = trusted
        if banned_list is not None:
            banned = set()
            for item in banned_list:
                h = parse_identity_hash(str(item))
                if h is not None:
                    banned.add(h)
            with self._lock:
                self.banned = banned
