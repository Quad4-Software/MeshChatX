# SPDX-License-Identifier: 0BSD

"""History and message persistence mixin for RRCHub."""

import bisect
import contextlib
import os
import time
from collections import deque

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.constants import (
    H_KIND,
    H_MENTION,
    H_NICK,
    H_SRC,
    H_TEXT,
    H_TS,
)


class RRCHubHistoryMixin:
    """History persistence and timeline query methods for RRCHub."""

    def _per_room_cap(self):
        v = self.manager.history_per_room_cap
        try:
            v = int(v)
        except Exception:
            return None
        return v if v > 0 else None

    def _filter_history(self):
        return bool(self.manager.filter_loaded_history)

    def _ephemeral_notices_history(self):
        return self.manager.ephemeral_notices

    def _entry_for(self, msg):
        return {
            H_KIND: msg.kind,
            H_SRC: bytes(msg.src) if isinstance(msg.src, (bytes, bytearray)) else None,
            H_NICK: msg.nick if isinstance(msg.nick, str) else None,
            H_TEXT: msg.text if isinstance(msg.text, str) else "",
            H_TS: int(msg.ts) if isinstance(msg.ts, int) else proto.now_ms(),
            H_MENTION: bool(getattr(msg, "mention", False)),
        }

    def _msg_from_entry(self, room, entry):
        if not isinstance(entry, dict):
            return None
        m = proto.RRCMessage(
            entry.get(H_KIND) if isinstance(entry.get(H_KIND), str) else "msg",
            room,
            entry.get(H_SRC)
            if isinstance(entry.get(H_SRC), (bytes, bytearray))
            else None,
            entry.get(H_NICK) if isinstance(entry.get(H_NICK), str) else None,
            entry.get(H_TEXT) if isinstance(entry.get(H_TEXT), str) else "",
            entry.get(H_TS) if isinstance(entry.get(H_TS), int) else 0,
        )
        m.mention = bool(entry.get(H_MENTION, False))
        return m

    def _persistable_room(self, room):
        return isinstance(room, str) and room and room != "*"

    def _append_history(self, room, msg):
        if not self._persistable_room(room):
            return
        try:
            self.manager._ensure_history_dir(self)
            path = self.manager._history_path(self, room)
            with open(path, "ab") as f:
                f.write(proto.encode(self._entry_for(msg)))
            self._history_write_failed = False
        except Exception as e:
            if not self._history_write_failed:
                self._history_write_failed = True
                self._log(
                    "history persistence failed, suppressing further warnings "
                    "until recovery: " + str(e),
                    RNS.LOG_ERROR,
                )

    def _delete_history(self, room):
        if not self._persistable_room(room):
            return
        path = self.manager._history_path(self, room)
        with contextlib.suppress(Exception):
            if os.path.isfile(path):
                os.unlink(path)

    def _load_history(self):
        with self._lock:
            rooms = list(self.messages.keys())
        for room in rooms:
            if not self._persistable_room(room):
                continue
            path = self.manager._history_path(self, room)
            if not os.path.isfile(path):
                continue
            window = deque(maxlen=self._per_room_cap())
            decode_error = None
            try:
                with open(path, "rb") as f:
                    while True:
                        pos = f.tell()
                        try:
                            window.append(proto.load(f))
                        except EOFError:
                            break
                        except Exception as ex:
                            decode_error = ex
                            try:
                                f.seek(pos + 1)
                            except OSError:
                                break
                            if f.tell() <= pos:
                                break
            except OSError as ex:
                self._log(
                    "history load failed for #" + room + ": " + str(ex),
                    RNS.LOG_ERROR,
                )
                continue
            if decode_error is not None:
                self._log(
                    "history file for #"
                    + room
                    + " has a corrupt record, kept "
                    + str(len(window))
                    + " valid messages: "
                    + str(decode_error),
                    RNS.LOG_ERROR,
                )
            msgs = []
            filter_msgs = self._filter_history()
            for e in window:
                m = self._msg_from_entry(room, e)
                if m is None:
                    continue
                if filter_msgs and m.kind in ("system", "notice"):
                    continue
                m.seq = self._next_seq()
                msgs.append(m)
            with self._lock:
                self.messages[room] = msgs

    def _clean_history(self):
        now = time.time()
        cleaned = False
        remove_after = self._ephemeral_notices_history()
        if now > self._last_history_clean + self.CLEAN_HISTORY_INTERVAL:
            with self._lock:
                try:
                    for r in self.messages:
                        old = set()
                        for m in self.messages[r]:
                            age = now - m.ts / 1000.0
                            if m.kind in ("system", "notice") and age > remove_after:
                                old.add(m)
                        for m in old:
                            self.messages[r].remove(m)
                            cleaned = True
                except Exception as e:
                    RNS.trace_exception(e)
        self._last_history_clean = time.time()
        if cleaned:
            self.clean_last_removed = time.time()

    def _record_message(self, msg, local=False):
        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
            buf = self.messages.setdefault(msg.room or "*", [])
            buf.append(msg)
            if cap is not None and len(buf) > cap:
                del buf[: len(buf) - cap]
            if (
                not local
                and msg.room
                and msg.room != self.manager.active_room_for(self)
            ):
                self._bump_unread(msg.room)
                if msg.mention:
                    self.mention_rooms.add(msg.room)
            self.manager._notify_messages(self, msg)
        self._append_history(msg.room, msg)
        self._clean_history()

    def _record_system(self, room, text):
        if not room:
            return
        msg = proto.RRCMessage("system", room, None, None, text, proto.now_ms())
        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
            buf = self.messages.setdefault(room, [])
            buf.append(msg)
            if cap is not None and len(buf) > cap:
                del buf[: len(buf) - cap]
            self.manager._notify_messages(self, msg)
        self._append_history(room, msg)
        self._clean_history()

    def _record_connection_event(self, text, rooms=None):
        """Write a connection status line into each joined room timeline."""
        if rooms is None:
            with self._lock:
                rooms = list(self.rooms)
        for room in rooms:
            with contextlib.suppress(Exception):
                self._record_system(room, text)

    def _record_notice(self, msg):
        target_room = msg.room
        if not target_room:
            target_room = self.manager.active_room_for(self)
            if target_room:
                msg.room = target_room

        cap = self._per_room_cap()
        with self._lock:
            msg.seq = self._next_seq()
            self.notices.append(msg)
            if len(self.notices) > 200:
                del self.notices[: len(self.notices) - 200]
            if target_room:
                buf = self.messages.setdefault(target_room, [])
                buf.append(msg)
                if cap is not None and len(buf) > cap:
                    del buf[: len(buf) - cap]
                if target_room != self.manager.active_room_for(self):
                    # After kick/rollback the room is already removed from
                    # self.rooms. Do not re-bump unread from the ERROR notice.
                    if target_room in self.rooms:
                        self._bump_unread(target_room)
            self.manager._notify_messages(self, msg)
        if target_room:
            self._append_history(target_room, msg)
            self._clean_history()

    def get_messages(self, room):
        with self._lock:
            return list(self.messages.get(room, []))

    def room_messages(self, room, limit=None, before_seq=None):
        """Return (messages, has_more) for a room, newest page last.

        before_seq, when given, restricts results to messages recorded
        before that sequence number, letting callers page backwards through
        history. limit caps how many of the most recent matching messages
        are returned; has_more reports whether older messages remain.
        """
        msgs = self.get_messages(proto.normalize_room(room))
        if before_seq is not None:
            seqs = [m.seq or 0 for m in msgs]
            cut = bisect.bisect_left(seqs, before_seq)
            msgs = msgs[:cut]
        has_more = False
        if limit is not None and len(msgs) > limit:
            has_more = True
            msgs = msgs[-limit:]
        return [m.to_dict() for m in msgs], has_more

    def clear_messages(self, room):
        r = proto.normalize_room(room)
        with self._lock:
            if r in self.messages:
                self.messages[r] = []
            self.unread_rooms.discard(r)
            self.unread_counts.pop(r, None)
            self.mention_rooms.discard(r)
        self._delete_history(r)
        self.manager._notify_change(self)
