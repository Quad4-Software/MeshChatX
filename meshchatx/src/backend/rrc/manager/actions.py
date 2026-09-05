# SPDX-License-Identifier: 0BSD

"""Room action and command mixin for RRCHub."""

import contextlib
import os

from meshchatx.src.backend.rrc import protocol as proto


class RRCHubActionsMixin:
    """User and room actions (join, part, message, action, ping, command) for RRCHub."""

    def request_room_list(self):
        """Request a fresh public room list from the hub (/list).

        The hub reply replaces available_rooms (adds new rooms and drops
        removed ones). The list notice is silent so it does not appear in
        chat history.
        """
        with self._lock:
            self._silent_list_pending += 1
        try:
            self.send_command("/list", room=None, record_local=False)
        except Exception:
            with self._lock:
                if self._silent_list_pending > 0:
                    self._silent_list_pending -= 1
            raise

    def _request_room_list(self):
        with contextlib.suppress(Exception):
            self.request_room_list()

    def join_room(self, room, key=None, silent=False):
        r = proto.normalize_room(room)
        body = None
        if isinstance(key, str):
            stripped = key.strip()
            if stripped:
                body = stripped
        env = proto.make_envelope(
            proto.T_JOIN,
            src=self.manager.identity.hash,
            room=r,
            body=body,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        with self._lock:
            self._pending_joins.add(r)
            if silent:
                self._silent_joins.add(r)
        try:
            self._send_env(env)
        except Exception:
            with self._lock:
                self._pending_joins.discard(r)
                self._silent_joins.discard(r)
            raise
        with self._lock:
            if r not in self.messages:
                self.messages[r] = []
        self.manager._notify_change(self)

    def send_command(self, text, room=None, record_local=True):
        if not isinstance(text, str) or not text.startswith("/"):
            msg = "command must start with /"
            raise ValueError(msg)
        r = None
        if isinstance(room, str) and room.strip():
            r = proto.normalize_room(room)
        nick = self.get_effective_nick()
        env = proto.make_envelope(
            proto.T_MSG,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        if nick:
            env[proto.K_NICK] = nick
        local_msg = None
        if record_local:
            local_msg = proto.RRCMessage(
                "msg",
                r,
                self.manager.identity.hash,
                nick,
                self._redact_command_for_history(text),
                proto.now_ms(),
            )
        self._send_env_then_maybe_record(env, local_msg)

    @staticmethod
    def _redact_command_for_history(text):
        """Omit +k secrets from locally recorded command history."""
        parts = text.split()
        if len(parts) >= 4 and parts[0].lower() == "/mode" and parts[2].lower() == "+k":
            return " ".join([*parts[:3], "***"])
        return text

    def send_ping(self, room=None):
        body = os.urandom(8)
        env = proto.make_envelope(
            proto.T_PING,
            src=self.manager.identity.hash,
            body=body,
        )
        with self._lock:
            now = proto.now_ms()
            self._pending_pings[body] = (now, room)
            expired = [k for k, v in self._pending_pings.items() if now - v[0] > 15000]
            for k in expired:
                self._pending_pings.pop(k, None)
        self._send_env(env)
        return body

    def part_room(self, room):
        room_n = proto.normalize_room(room)
        env = proto.make_envelope(
            proto.T_PART,
            src=self.manager.identity.hash,
            room=room_n,
        )
        with self._lock:
            self._pending_parts.add(room_n)
        with contextlib.suppress(Exception):
            self._send_env(env)
        with self._lock:
            self.rooms.discard(room_n)
            self.messages.pop(room_n, None)
            self.unread_rooms.discard(room_n)
            self.unread_counts.pop(room_n, None)
            self.mention_rooms.discard(room_n)
            self.members.pop(room_n, None)
        self._delete_history(room_n)
        self.manager.save()
        self.manager._notify_change(self)

    def send_message(self, room, text):
        r = proto.normalize_room(room)
        if not isinstance(text, str) or not text.strip():
            msg = "message text must be non-empty"
            raise ValueError(msg)
        if len(text.encode("utf-8")) > self.max_msg_body_bytes:
            msg = "message too long for hub limit"
            raise ValueError(msg)
        env = proto.make_envelope(
            proto.T_MSG,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        mid = env[proto.K_ID]
        if isinstance(mid, (bytes, bytearray)):
            self._sent_ids.append(bytes(mid))
        self._send_env_then_maybe_record(
            env,
            proto.RRCMessage(
                "msg",
                r,
                self.manager.identity.hash,
                nick,
                text,
                proto.now_ms(),
            ),
        )
        return mid

    def send_action(self, room, text):
        r = proto.normalize_room(room)
        if not isinstance(text, str) or not text.strip():
            msg = "action text must be non-empty"
            raise ValueError(msg)
        if len(text.encode("utf-8")) > self.max_msg_body_bytes:
            msg = "action too long for hub limit"
            raise ValueError(msg)
        env = proto.make_envelope(
            proto.T_ACTION,
            src=self.manager.identity.hash,
            room=r,
            body=text,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        mid = env[proto.K_ID]
        if isinstance(mid, (bytes, bytearray)):
            self._sent_ids.append(bytes(mid))
        self._send_env_then_maybe_record(
            env,
            proto.RRCMessage(
                "action",
                r,
                self.manager.identity.hash,
                nick,
                text,
                proto.now_ms(),
            ),
        )
        return mid
