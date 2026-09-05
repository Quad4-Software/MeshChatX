# SPDX-License-Identifier: 0BSD

"""Encrypted client room key storage and moderation error helpers for RRCManager."""

import contextlib

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.constants import (
    BAD_KEY_MARKERS,
    DEFAULT_DEST_NAME,
    FORCED_LEAVE_MARKERS,
)
from meshchatx.src.backend.rrc.room_key_crypto import decrypt_room_key, encrypt_room_key


class RRCManagerRoomKeysMixin:
    """Room key encryption, storage querying, and error categorization for RRCManager."""

    def _private_key_bytes(self):
        identity = self.identity
        if identity is None:
            return None
        with contextlib.suppress(Exception):
            key = identity.get_private_key()
            if isinstance(key, (bytes, bytearray)) and key:
                return bytes(key)
        return None

    def _room_key_dao(self):
        db = self.database
        if db is None:
            return None
        return getattr(db, "rrc_room_keys", None)

    @staticmethod
    def _hub_hash_hex(hub_or_hash):
        from meshchatx.src.backend.rrc.manager.hub import RRCHub

        if isinstance(hub_or_hash, RRCHub):
            return hub_or_hash.hub_hash.hex()
        if isinstance(hub_or_hash, (bytes, bytearray)):
            return bytes(hub_or_hash).hex()
        if isinstance(hub_or_hash, str):
            return hub_or_hash.strip().lower()
        msg = "invalid hub hash"
        raise TypeError(msg)

    @staticmethod
    def _dest_name_for(hub_or_dest):
        from meshchatx.src.backend.rrc.manager.hub import RRCHub

        if isinstance(hub_or_dest, RRCHub):
            return hub_or_dest.dest_name or DEFAULT_DEST_NAME
        if isinstance(hub_or_dest, str) and hub_or_dest.strip():
            return hub_or_dest.strip()
        return DEFAULT_DEST_NAME

    def remember_room_key(self, hub, room, key):
        """Encrypt and persist a room key for later joins."""
        dao = self._room_key_dao()
        private_key = self._private_key_bytes()
        if dao is None or private_key is None:
            msg = "room key storage is unavailable"
            raise RuntimeError(msg)
        room_n = proto.normalize_room(room)
        nonce, ciphertext = encrypt_room_key(private_key, key)
        dao.upsert(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
            nonce,
            ciphertext,
        )

    def forget_room_key(self, hub, room):
        dao = self._room_key_dao()
        if dao is None:
            return 0
        room_n = proto.normalize_room(room)
        return dao.delete(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )

    def get_room_key(self, hub, room):
        """Return the decrypted room key, or None when missing or undecryptable."""
        dao = self._room_key_dao()
        private_key = self._private_key_bytes()
        if dao is None or private_key is None:
            return None
        room_n = proto.normalize_room(room)
        row = dao.get(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )
        if not row:
            return None
        try:
            return decrypt_room_key(private_key, row["nonce"], row["ciphertext"])
        except Exception:
            return None

    def has_stored_room_key(self, hub, room):
        dao = self._room_key_dao()
        if dao is None:
            return False
        room_n = proto.normalize_room(room)
        row = dao.get(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
            room_n,
        )
        return row is not None

    def list_stored_room_keys(self, hub):
        dao = self._room_key_dao()
        if dao is None:
            return []
        rows = dao.list_for_hub(
            self._hub_hash_hex(hub),
            self._dest_name_for(hub),
        )
        return [
            {
                "hub_hash": row["hub_hash"],
                "dest_name": row["dest_name"],
                "room": row["room"],
                "updated_at": row.get("updated_at"),
            }
            for row in rows or []
        ]

    @staticmethod
    def is_bad_key_error(text):
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        # Require the words "bad key" so mode hints like "enable +k" do not wipe storage.
        return any(marker in lowered for marker in BAD_KEY_MARKERS)

    @staticmethod
    def is_forced_leave_error(text):
        if not isinstance(text, str):
            return False
        lowered = text.strip().lower()
        return any(marker in lowered for marker in FORCED_LEAVE_MARKERS)
