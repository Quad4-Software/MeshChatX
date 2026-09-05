# SPDX-License-Identifier: 0BSD

"""Inbound packet handlers and resource processing mixin for RRCHub."""

import contextlib
import hashlib
import time

import RNS

from meshchatx.src.backend.rrc import protocol as proto


class RRCHubPacketHandlersMixin:
    """Inbound packet decoding, dispatch, and resource reception for RRCHub."""

    def _on_packet(self, data):
        try:
            env = proto.decode(data)
        except Exception as e:
            self._log("decode failed: " + str(e), RNS.LOG_DEBUG)
            return
        if not isinstance(env, dict):
            return
        t = env.get(proto.K_T)
        if t is None:
            return

        handler = self._PACKET_HANDLERS.get(t)
        if handler is not None:
            handler(self, env)

    def _handle_ping(self, env):
        with contextlib.suppress(Exception):
            pong = proto.make_envelope(
                proto.T_PONG,
                src=self.manager.identity.hash,
                body=env.get(proto.K_BODY),
            )
            self._send_env(pong)

    def _handle_pong(self, env):
        body = env.get(proto.K_BODY)
        if not isinstance(body, (bytes, bytearray)):
            return
        key = bytes(body)
        with self._lock:
            pending = self._pending_pings.pop(key, None)
        if pending is not None:
            sent_ms, room = pending
            rtt_ms = max(0, proto.now_ms() - sent_ms)
            self._record_system(room, "Pong from hub: " + str(rtt_ms) + " ms")

    def _handle_welcome(self, env):
        self.welcomed = True
        body = env.get(proto.K_BODY)
        if isinstance(body, dict):
            hub_name = body.get(proto.B_WELCOME_HUB)
            if isinstance(hub_name, str):
                self.hub_name = hub_name
            ver = body.get(proto.B_WELCOME_VER)
            if isinstance(ver, str):
                self.hub_version = ver
            caps = body.get(proto.B_WELCOME_CAPS)
            if isinstance(caps, dict):
                self.hub_caps = dict(caps)
            limits = body.get(proto.B_WELCOME_LIMITS)
            if isinstance(limits, dict):
                self._apply_limits(limits)
        with self._lock:
            was_reconnect = self._had_session
            self._reconnect_attempts = 0
            self._had_session = True
            rooms = list(self.rooms)
        self._set_status(self.STATUS_CONNECTED, "Connected")
        if was_reconnect and rooms:
            self._record_connection_event("Reconnected to hub", rooms=rooms)
        self.manager._on_welcome(self)
        if self.auto_list:
            self._request_room_list()

    def _handle_joined(self, env):
        room = env.get(proto.K_ROOM)
        if not (isinstance(room, str) and room):
            return
        r = room.strip().lower()
        body = env.get(proto.K_BODY)
        joiner_nick = env.get(proto.K_NICK)
        own_hash = self._own_hash()

        body_hashes = []
        if isinstance(body, list):
            body_hashes = [bytes(e) for e in body if isinstance(e, (bytes, bytearray))]

        with self._lock:
            self_join = r in self._pending_joins
            silent = r in self._silent_joins
            if self_join:
                self._pending_joins.discard(r)
            if silent:
                self._silent_joins.discard(r)

            self.rooms.add(r)
            if r not in self.messages:
                self.messages[r] = []
            members = self.members.setdefault(r, set())
            for h in body_hashes:
                members.add(h)
            if own_hash is not None:
                members.add(own_hash)

            if (
                (not self_join)
                and isinstance(joiner_nick, str)
                and joiner_nick
                and len(body_hashes) == 1
            ):
                jh = body_hashes[0]
                if own_hash is None or jh != own_hash:
                    self.nicks[jh] = joiner_nick

        if self_join:
            if silent:
                self._record_system(r, "You rejoined #" + r)
            else:
                self._record_system(r, "You joined #" + r)
            if self.auto_who:
                try:
                    with self._lock:
                        self._silent_who_rooms.add(r)
                    self.send_command("/who " + r, room=r, record_local=False)
                except Exception:
                    with self._lock:
                        self._silent_who_rooms.discard(r)
            self.manager.save()
        else:
            joiner = None
            if len(body_hashes) == 1 and (
                own_hash is None or body_hashes[0] != own_hash
            ):
                joiner = body_hashes[0]
            if joiner is not None:
                self._record_system(r, self.display_name_for(joiner) + " joined")
        self.manager._notify_change(self)

    def _handle_parted(self, env):
        room = env.get(proto.K_ROOM)
        if not (isinstance(room, str) and room):
            return
        r = room.strip().lower()
        body = env.get(proto.K_BODY)
        parter_nick = env.get(proto.K_NICK)
        own_hash = self._own_hash()

        body_hashes = []
        if isinstance(body, list):
            body_hashes = [bytes(e) for e in body if isinstance(e, (bytes, bytearray))]

        with self._lock:
            self_part = r in self._pending_parts
            if self_part:
                self._pending_parts.discard(r)

            if (
                (not self_part)
                and isinstance(parter_nick, str)
                and parter_nick
                and len(body_hashes) == 1
            ):
                ph = body_hashes[0]
                if own_hash is None or ph != own_hash:
                    self.nicks[ph] = parter_nick

            members = self.members.get(r)
            if members is not None:
                for h in body_hashes:
                    members.discard(h)
            if self_part:
                self.rooms.discard(r)
                self.members.pop(r, None)

        if self_part:
            self.manager.save()
        else:
            parter = None
            if len(body_hashes) == 1 and (
                own_hash is None or body_hashes[0] != own_hash
            ):
                parter = body_hashes[0]
            if parter is not None:
                self._record_system(r, self.display_name_for(parter) + " left")
        self.manager._notify_change(self)

    def _handle_chat(self, env, kind):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        src = env.get(proto.K_SRC)
        nick = env.get(proto.K_NICK)
        mid = env.get(proto.K_ID)
        own_hash = self._own_hash()
        is_own = (
            isinstance(src, (bytes, bytearray))
            and own_hash is not None
            and bytes(src) == own_hash
        )
        if (
            is_own
            and isinstance(mid, (bytes, bytearray))
            and bytes(mid) in self._sent_ids
        ):
            return
        if isinstance(src, (bytes, bytearray)) and isinstance(nick, str) and nick:
            with self._lock:
                self.nicks[bytes(src)] = nick
        if not isinstance(body, str):
            return
        msg = proto.RRCMessage(
            kind,
            room.strip().lower() if isinstance(room, str) else None,
            bytes(src) if isinstance(src, (bytes, bytearray)) else None,
            nick if isinstance(nick, str) else None,
            body,
            proto.now_ms(),
        )
        if not is_own and proto.text_mentions(body, self.get_effective_nick()):
            msg.mention = True
        self._record_message(msg)

    def _handle_msg(self, env):
        self._handle_chat(env, "msg")

    def _handle_action(self, env):
        self._handle_chat(env, "action")

    def _handle_notice(self, env):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        src = env.get(proto.K_SRC)
        if not isinstance(body, str):
            return

        nick_prefix = "nickname set to "
        if body.startswith(nick_prefix):
            new_nick = body[len(nick_prefix) :].strip()
            if new_nick:
                self.set_nick_override(new_nick)

        parsed = proto.parse_room_list_notice_details(body)
        if parsed is not None:
            with self._lock:
                self.available_rooms = {
                    name: info.get("topic") for name, info in parsed.items()
                }
                self.available_keyed_rooms = sorted(
                    name for name, info in parsed.items() if info.get("has_key")
                )
                silent = self._silent_list_pending > 0
                if silent:
                    self._silent_list_pending -= 1
            self.manager._notify_change(self)
            if silent:
                return

        parsed_who = proto.parse_who_notice(body)
        if parsed_who is not None:
            who_room, who_entries = parsed_who
            with self._lock:
                members = self.members.setdefault(who_room, set())
                for nick, hash_hex in who_entries:
                    try:
                        hash_bytes = bytes.fromhex(hash_hex)
                    except Exception:
                        continue
                    if nick is None:
                        members.add(hash_bytes)
                        continue
                    for ph in members:
                        if ph.startswith(hash_bytes):
                            self.nicks[ph] = nick
                            break
                silent_who = who_room in self._silent_who_rooms
                if silent_who:
                    self._silent_who_rooms.discard(who_room)
            self.manager._notify_change(self)
            if silent_who:
                return

        room_n = room.strip().lower() if isinstance(room, str) else None
        if room_n is None and isinstance(body, str) and body.strip():
            with self._lock:
                self.motd = body
            self.manager._notify_change(self)
        msg = proto.RRCMessage(
            "notice",
            room_n,
            bytes(src) if isinstance(src, (bytes, bytearray)) else None,
            None,
            body,
            proto.now_ms(),
        )
        self._record_notice(msg)

    def _handle_error(self, env):
        body = env.get(proto.K_BODY)
        room = env.get(proto.K_ROOM)
        text = body if isinstance(body, str) else "(error)"
        r = room.strip().lower() if isinstance(room, str) else None
        rollback_join = False
        leave_rooms = []
        with self._lock:
            if r:
                if r in self._pending_joins:
                    rollback_join = True
                self._pending_joins.discard(r)
                self._silent_joins.discard(r)
                self._pending_parts.discard(r)
                if rollback_join:
                    self.rooms.discard(r)
                    self.unread_rooms.discard(r)
                    self.mention_rooms.discard(r)
                    self.unread_counts.pop(r, None)
                    leave_rooms.append(r)
                elif self.manager.is_forced_leave_error(text) and r in self.rooms:
                    self.rooms.discard(r)
                    self.members.pop(r, None)
                    self.unread_rooms.discard(r)
                    self.mention_rooms.discard(r)
                    self.unread_counts.pop(r, None)
                    leave_rooms.append(r)
            elif self.manager.is_forced_leave_error(text):
                leave_rooms = list(self.rooms)
                self._pending_joins.clear()
                self._silent_joins.clear()
                self._pending_parts.clear()
                for room_name in leave_rooms:
                    self.rooms.discard(room_name)
                    self.members.pop(room_name, None)
                    self.unread_rooms.discard(room_name)
                    self.mention_rooms.discard(room_name)
                    self.unread_counts.pop(room_name, None)
        if r and self.manager.is_bad_key_error(text):
            with contextlib.suppress(Exception):
                self.manager.forget_room_key(self, r)
        msg = proto.RRCMessage("error", r, None, None, text, proto.now_ms())
        self._record_notice(msg)
        if rollback_join or leave_rooms:
            with self._lock:
                for room_name in leave_rooms:
                    self.messages.pop(room_name, None)
                    self.members.pop(room_name, None)
            for room_name in leave_rooms:
                self._delete_history(room_name)
                if self.manager.active_room_for(self) == room_name:
                    self.manager.set_active(self, None)
            self.manager.save()
            self.manager._notify_change(self)

    def _handle_resource_envelope(self, env):
        body = env.get(proto.K_BODY)
        if not isinstance(body, dict):
            return
        with contextlib.suppress(Exception):
            rid = body.get(proto.B_RES_ID)
            kind = body.get(proto.B_RES_KIND)
            size = body.get(proto.B_RES_SIZE)
            sha256 = body.get(proto.B_RES_SHA256)
            encoding = body.get(proto.B_RES_ENCODING)
            if not isinstance(rid, (bytes, bytearray)):
                return
            if not isinstance(kind, str):
                return
            if not isinstance(size, int) or size <= 0:
                return
            room = env.get(proto.K_ROOM)
            with self._lock:
                self._resource_expectations[bytes(rid)] = {
                    "kind": kind,
                    "size": size,
                    "sha256": bytes(sha256)
                    if isinstance(sha256, (bytes, bytearray))
                    else None,
                    "encoding": encoding if isinstance(encoding, str) else "utf-8",
                    "room": room.strip().lower() if isinstance(room, str) else None,
                    "expires": time.monotonic() + 30.0,
                }

    _PACKET_HANDLERS = {
        proto.T_PING: _handle_ping,
        proto.T_PONG: _handle_pong,
        proto.T_WELCOME: _handle_welcome,
        proto.T_JOINED: _handle_joined,
        proto.T_PARTED: _handle_parted,
        proto.T_MSG: _handle_msg,
        proto.T_ACTION: _handle_action,
        proto.T_NOTICE: _handle_notice,
        proto.T_ERROR: _handle_error,
        proto.T_RESOURCE_ENVELOPE: _handle_resource_envelope,
    }

    def _resource_advertised(self, resource):
        try:
            if hasattr(resource, "get_data_size"):
                size = resource.get_data_size()
            elif hasattr(resource, "total_size"):
                size = resource.total_size
            else:
                size = getattr(resource, "size", 0)
        except Exception:
            return False
        return size <= 262144

    def _resource_concluded(self, resource):
        try:
            if resource.status != RNS.Resource.COMPLETE:
                with contextlib.suppress(Exception):
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
                return
            data = None
            try:
                data = resource.data.read()
            finally:
                with contextlib.suppress(Exception):
                    if hasattr(resource, "data") and resource.data:
                        resource.data.close()
            if data is None:
                return

            now = time.monotonic()
            matched = None
            with self._lock:
                expired = [
                    k
                    for k, v in self._resource_expectations.items()
                    if v["expires"] < now
                ]
                for k in expired:
                    self._resource_expectations.pop(k, None)
                for k, exp in list(self._resource_expectations.items()):
                    if exp["size"] == len(data):
                        matched = exp
                        self._resource_expectations.pop(k, None)
                        break

            kind = matched["kind"] if matched else proto.RES_KIND_BLOB
            room = matched["room"] if matched else None
            encoding = matched["encoding"] if matched else "utf-8"
            sha = matched["sha256"] if matched else None
            if sha is not None and hashlib.sha256(data).digest() != sha:
                return
            if kind in (proto.RES_KIND_NOTICE, proto.RES_KIND_MOTD):
                try:
                    text = data.decode(encoding, errors="replace")
                except Exception:
                    return
                if kind == proto.RES_KIND_MOTD:
                    with self._lock:
                        self.motd = text
                    self.manager._notify_change(self)
                msg = proto.RRCMessage("notice", room, None, None, text, proto.now_ms())
                self._record_notice(msg)
        except Exception as e:
            self._log("resource handling failed: " + str(e), RNS.LOG_ERROR)
