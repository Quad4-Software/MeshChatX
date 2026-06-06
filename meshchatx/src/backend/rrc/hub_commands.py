# SPDX-License-Identifier: 0BSD

"""Operator and moderation commands for hosted RRC hubs (rrcd-compatible)."""

import time

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.identity_util import (
    format_ambiguous_targets,
    parse_identity_hash,
    resolve_identity_hash,
    find_session_by_token,
    find_sessions_by_token,
)
from meshchatx.src.backend.rrc.rooms_toml import INVITE_DEFAULT_TTL_S

HELP_TEXT = (
    "commands: /list, /who [room], /nick <name>, /topic <room> [text], "
    "/kick <room> <nick|hash>, /ban <room> add|del|list [target], "
    "/invite <room> add|del|list [target], /mode <room> <flags>, "
    "/register <room>, /unregister <room>, /op|/deop|/voice|/devoice <room> <target>, "
    "/kline add|del|list [hash], /help"
)


class HubCommandHandler:
    """Dispatches in-room slash commands for RRCHubServer."""

    def handle(self, server, link, sess, room, text, outgoing):
        cmdline = text.strip()
        if not cmdline.startswith("/"):
            return False
        parts = [p for p in cmdline[1:].split() if p]
        if not parts:
            return False
        cmd = parts[0].lower()
        peer = sess.peer if isinstance(sess.peer, (bytes, bytearray)) else None

        if cmd == "help":
            server._queue_notice(outgoing, link, room, HELP_TEXT)
            return True

        if cmd == "list":
            return self._cmd_list(server, link, outgoing)

        if cmd in ("who", "names"):
            return self._cmd_who(server, link, room, parts, outgoing, peer)

        if cmd == "nick":
            return self._cmd_nick(server, link, sess, room, parts, outgoing)

        if cmd == "topic":
            return self._cmd_topic(server, link, room, parts, outgoing, peer)

        if cmd == "kick":
            return self._cmd_kick(server, link, room, parts, outgoing, peer)

        if cmd == "kline":
            return self._cmd_kline(server, link, parts, outgoing, peer)

        if cmd == "register":
            return self._cmd_register(server, link, sess, room, parts, outgoing, peer)

        if cmd == "unregister":
            return self._cmd_unregister(server, link, sess, room, parts, outgoing, peer)

        if cmd in ("op", "deop", "voice", "devoice"):
            return self._cmd_op_voice(server, link, room, parts, outgoing, peer, cmd)

        if cmd == "mode":
            return self._cmd_mode(server, link, room, parts, outgoing, peer)

        if cmd == "ban":
            return self._cmd_ban(server, link, room, parts, outgoing, peer)

        if cmd == "invite":
            return self._cmd_invite(server, link, room, parts, outgoing, peer)

        return False

    def _cmd_list(self, server, link, outgoing):
        public = []
        for room_name, st in server.rooms._state.items():
            if st.get("registered") and not st.get("private"):
                public.append((room_name, st.get("topic")))
        for room_name, st in server.rooms._registry.items():
            if room_name not in server.rooms._state and not st.get("private"):
                public.append((room_name, st.get("topic")))
        if not public:
            server._queue_notice(outgoing, link, None, "No public rooms registered")
            return True
        lines = ["Registered public rooms:"]
        for name, topic in sorted(public, key=lambda x: x[0]):
            lines.append("  " + name + " - " + topic if topic else "  " + name)
        server._queue_notice(outgoing, link, None, "\n".join(lines))
        return True

    def _cmd_who(self, server, link, room, parts, outgoing, peer):
        target = parts[1] if len(parts) >= 2 else room
        if not isinstance(target, str) or not target:
            server._queue_notice(outgoing, link, None, "usage: /who [room]")
            return True
        try:
            r = server._norm_room(target)
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        st = server.rooms.get_state(r)
        if (
            st is not None
            and st.get("private")
            and not server.policy.is_server_op(peer)
        ):
            server._queue_notice(outgoing, link, None, f"room {r} is private")
            return True
        members = []
        for member in server._room_members.get(r, set()):
            s = server._sessions.get(member)
            if s is None:
                continue
            ident = (
                bytes(s.peer).hex() if isinstance(s.peer, (bytes, bytearray)) else "?"
            )
            if s.nick:
                members.append(s.nick + " (" + ident[:12] + ")")
            else:
                members.append(ident)
        server._queue_notice(
            outgoing,
            link,
            None,
            "members in " + r + ": " + (", ".join(members) if members else "(none)"),
        )
        return True

    def _cmd_nick(self, server, link, sess, room, parts, outgoing):
        if len(parts) < 2:
            server._queue_notice(outgoing, link, room, "usage: /nick <name>")
            return True
        n = proto.normalize_nick(" ".join(parts[1:]), server.max_nick_bytes)
        if n is None:
            server._queue_notice(outgoing, link, room, "invalid nickname")
            return True
        sess.nick = n
        server._queue_notice(outgoing, link, room, "nickname set to " + n)
        return True

    def _cmd_topic(self, server, link, room, parts, outgoing, peer):
        if len(parts) < 2:
            server._queue_notice(outgoing, link, None, "usage: /topic <room> [topic]")
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        st = server.rooms.ensure_state(r)
        if len(parts) == 2:
            topic = st.get("topic")
            server._queue_notice(
                outgoing, link, room, f"topic for {r}: {topic if topic else '(none)'}"
            )
            return True
        if not server.rooms.is_room_op(r, peer):
            if bool(st.get("topic_ops_only")):
                server._queue_error(outgoing, link, "not authorized (+t)", room=r)
                return True
        topic = " ".join(parts[2:]).strip()
        st["topic"] = topic if topic else None
        server.rooms.touch_room(r)
        server.rooms.persist(r)
        for member in list(server._room_members.get(r, set())):
            server._queue_notice(
                outgoing,
                member,
                r,
                f"topic for {r} is now: {topic if topic else '(cleared)'}",
            )
        return True

    def _cmd_kick(self, server, link, room, parts, outgoing, peer):
        if len(parts) < 3:
            server._queue_notice(
                outgoing, link, None, "usage: /kick <room> <nick|hashprefix>"
            )
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, room, "bad room: " + str(e))
            return True
        if not server.rooms.is_room_op(r, peer):
            server._queue_error(outgoing, link, "not authorized", room=r)
            return True
        target_link = find_session_by_token(server, parts[2], room=r)
        if target_link is None:
            matches = find_sessions_by_token(server, parts[2], room=r)
            server._queue_notice(
                outgoing,
                link,
                room,
                format_ambiguous_targets(parts[2], matches),
            )
            return True
        tsess = server._sessions.get(target_link)
        if tsess is None or r not in tsess.rooms:
            server._queue_notice(outgoing, link, room, "target not in room")
            return True
        tsess.rooms.discard(r)
        members = server._room_members.get(r)
        if members is not None:
            members.discard(target_link)
        server._queue_error(outgoing, target_link, f"kicked from {r}", room=r)
        server._queue_notice(outgoing, link, room, f"kicked {parts[2]} from {r}")
        return True

    def _cmd_kline(self, server, link, parts, outgoing, peer):
        if not server.policy.is_server_op(peer):
            server._queue_error(outgoing, link, "not authorized")
            return True
        if len(parts) < 2:
            server._queue_notice(
                outgoing,
                link,
                None,
                "usage: /kline add|del|list [nick|hashprefix|hash]",
            )
            return True
        op = parts[1].lower()
        if op == "list":
            items = server.policy.list_banned_hex()
            server._queue_notice(
                outgoing,
                link,
                None,
                "klines: " + (", ".join(items) if items else "(none)"),
            )
            return True
        if op not in ("add", "del"):
            server._queue_notice(
                outgoing,
                link,
                None,
                "usage: /kline add|del|list [nick|hashprefix|hash]",
            )
            return True
        if len(parts) < 3:
            server._queue_notice(
                outgoing, link, None, f"usage: /kline {op} <nick|hashprefix|hash>"
            )
            return True
        target_hash, _ = resolve_identity_hash(server, parts[2])
        if target_hash is None:
            target_hash = parse_identity_hash(parts[2])
        if target_hash is None:
            server._queue_notice(outgoing, link, None, f"no match for {parts[2]}")
            return True
        if op == "add":
            server.policy.add_ban(target_hash)
            server.policy.save()
            server._disconnect_banned(target_hash, outgoing, "banned (kline)")
            server._queue_notice(
                outgoing, link, None, f"kline added for {target_hash.hex()}"
            )
        else:
            if server.policy.is_banned(target_hash):
                server.policy.remove_ban(target_hash)
                server.policy.save()
                server._queue_notice(
                    outgoing, link, None, f"kline removed for {target_hash.hex()}"
                )
            else:
                server._queue_notice(
                    outgoing, link, None, f"not klined: {target_hash.hex()}"
                )
        return True

    def _cmd_register(self, server, link, sess, room, parts, outgoing, peer):
        if len(parts) < 2:
            server._queue_notice(outgoing, link, None, "usage: /register <room>")
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, room, "bad room: " + str(e))
            return True
        if r not in sess.rooms:
            server._queue_notice(
                outgoing, link, room, "must be present in the room to register it"
            )
            return True
        st = server.rooms.ensure_state(r, founder=peer)
        if st.get("registered") and st.get("founder") not in (None, peer):
            if not server.rooms.is_room_op(r, peer):
                server._queue_error(
                    outgoing, link, "only the room founder can register", room=r
                )
                return True
        st["registered"] = True
        if st.get("founder") is None and peer is not None:
            st["founder"] = peer
            st.setdefault("ops", set()).add(peer)
        server.rooms.touch_room(r)
        server.rooms.persist(r)
        server._queue_notice(outgoing, link, room, f"registered room {r}")
        server.manager._notify_change(server)
        return True

    def _cmd_unregister(self, server, link, sess, room, parts, outgoing, peer):
        if len(parts) < 2:
            server._queue_notice(outgoing, link, None, "usage: /unregister <room>")
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, room, "bad room: " + str(e))
            return True
        if r not in sess.rooms:
            server._queue_notice(
                outgoing, link, room, "must be present in the room to unregister it"
            )
            return True
        st = server.rooms.ensure_state(r)
        founder = st.get("founder")
        if founder is not None and peer is not None and bytes(founder) != bytes(peer):
            if not server.policy.is_server_op(peer):
                server._queue_error(
                    outgoing, link, "only the room founder can unregister", room=r
                )
                return True
        if not st.get("registered"):
            server._queue_notice(outgoing, link, room, f"room {r} is not registered")
            return True
        st["registered"] = False
        server.rooms.delete_from_registry(r)
        server._queue_notice(outgoing, link, room, f"unregistered room {r}")
        server.manager._notify_change(server)
        return True

    def _cmd_op_voice(self, server, link, room, parts, outgoing, peer, cmd):
        if len(parts) < 3:
            server._queue_notice(
                outgoing, link, None, f"usage: /{cmd} <room> <nick|hashprefix|hash>"
            )
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        if not server.rooms.is_room_op(r, peer):
            server._queue_error(outgoing, link, "not authorized", room=r)
            return True
        target_hash, matches = resolve_identity_hash(server, parts[2], room=r)
        if target_hash is None:
            server._queue_notice(
                outgoing, link, room, format_ambiguous_targets(parts[2], matches)
            )
            return True
        st = server.rooms.ensure_state(r)
        founder = st.get("founder")
        founder_b = bytes(founder) if isinstance(founder, (bytes, bytearray)) else None
        if cmd in ("op", "deop"):
            ops = st.setdefault("ops", set())
            if cmd == "op":
                ops.add(target_hash)
                server._queue_notice(outgoing, link, room, f"op granted in {r}")
            else:
                if founder_b is not None and target_hash == founder_b:
                    server._queue_notice(outgoing, link, room, "cannot deop founder")
                    return True
                ops.discard(target_hash)
                server._queue_notice(outgoing, link, room, f"op removed in {r}")
        else:
            voiced = st.setdefault("voiced", set())
            if cmd == "voice":
                voiced.add(target_hash)
                server._queue_notice(outgoing, link, room, f"voice granted in {r}")
            else:
                voiced.discard(target_hash)
                server._queue_notice(outgoing, link, room, f"voice removed in {r}")
        server.rooms.touch_room(r)
        server.rooms.persist(r)
        return True

    def _cmd_mode(self, server, link, room, parts, outgoing, peer):
        if len(parts) < 3:
            server._queue_notice(
                outgoing,
                link,
                None,
                "usage: /mode <room> (+m|-m|+i|-i|+t|-t|+n|-n|+p|-p|+k|-k) [key] | "
                "/mode <room> (+o|-o|+v|-v) <nick|hash>",
            )
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        if not server.rooms.is_room_op(r, peer):
            server._queue_error(outgoing, link, "not authorized", room=r)
            return True
        flag = parts[2].lower()
        st = server.rooms.ensure_state(r)
        if flag in ("+m", "-m"):
            st["moderated"] = flag == "+m"
        elif flag in ("+i", "-i"):
            st["invite_only"] = flag == "+i"
        elif flag in ("+t", "-t"):
            st["topic_ops_only"] = flag == "+t"
        elif flag in ("+n", "-n"):
            st["no_outside_msgs"] = flag == "+n"
        elif flag in ("+p", "-p"):
            st["private"] = flag == "+p"
        elif flag in ("+k", "-k"):
            if flag == "+k":
                if len(parts) < 4:
                    server._queue_notice(
                        outgoing, link, room, "usage: /mode <room> +k <key>"
                    )
                    return True
                key = " ".join(parts[3:]).strip()
                if not key:
                    server._queue_notice(outgoing, link, room, "key must not be empty")
                    return True
                st["key"] = key
            else:
                st["key"] = None
        elif flag in ("+r", "-r"):
            server._queue_notice(
                outgoing, link, room, "use /register or /unregister to change +r"
            )
            return True
        elif flag in ("+o", "-o", "+v", "-v"):
            if len(parts) < 4:
                server._queue_notice(
                    outgoing,
                    link,
                    room,
                    "usage: /mode <room> (+o|-o|+v|-v) <nick|hashprefix|hash>",
                )
                return True
            target_hash, matches = resolve_identity_hash(server, parts[3], room=r)
            if target_hash is None:
                server._queue_notice(
                    outgoing, link, room, format_ambiguous_targets(parts[3], matches)
                )
                return True
            founder = st.get("founder")
            founder_b = (
                bytes(founder) if isinstance(founder, (bytes, bytearray)) else None
            )
            if flag in ("+o", "-o"):
                ops = st.setdefault("ops", set())
                if flag == "+o":
                    ops.add(target_hash)
                elif founder_b is not None and target_hash == founder_b:
                    server._queue_notice(outgoing, link, room, "cannot deop founder")
                    return True
                else:
                    ops.discard(target_hash)
            else:
                voiced = st.setdefault("voiced", set())
                if flag == "+v":
                    voiced.add(target_hash)
                else:
                    voiced.discard(target_hash)
        else:
            server._queue_notice(
                outgoing,
                link,
                room,
                "supported modes: +m -m +i -i +k -k +t -t +n -n +p -p +r -r +o -o +v -v",
            )
            return True
        server.rooms.touch_room(r)
        server.rooms.persist(r)
        server.rooms.broadcast_mode(r, outgoing)
        server.manager._notify_change(server)
        return True

    def _cmd_ban(self, server, link, room, parts, outgoing, peer):
        if len(parts) < 3:
            server._queue_notice(
                outgoing,
                link,
                None,
                "usage: /ban <room> add|del|list [nick|hashprefix|hash]",
            )
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        op = parts[2].lower()
        st = server.rooms.ensure_state(r)
        bans = st.setdefault("bans", set())
        if op == "list":
            if not bans:
                server._queue_notice(outgoing, link, room, f"no bans in {r}")
            else:
                items = sorted(bytes(x).hex() for x in bans)
                server._queue_notice(
                    outgoing, link, room, f"bans in {r}: " + ", ".join(items)
                )
            return True
        if op not in ("add", "del"):
            server._queue_notice(
                outgoing,
                link,
                room,
                "usage: /ban <room> add|del|list [nick|hashprefix|hash]",
            )
            return True
        if len(parts) < 4:
            server._queue_notice(
                outgoing, link, room, f"usage: /ban {r} {op} <nick|hashprefix|hash>"
            )
            return True
        if not server.rooms.is_room_op(r, peer):
            server._queue_error(outgoing, link, "not authorized", room=r)
            return True
        target_hash, matches = resolve_identity_hash(server, parts[3], room=r)
        if target_hash is None:
            server._queue_notice(
                outgoing, link, room, format_ambiguous_targets(parts[3], matches)
            )
            return True
        if op == "add":
            bans.add(target_hash)
            server.rooms.touch_room(r)
            server.rooms.persist(r)
            for member in list(server._room_members.get(r, set())):
                ms = server._sessions.get(member)
                if ms is not None and isinstance(ms.peer, (bytes, bytearray)):
                    if bytes(ms.peer) == target_hash:
                        ms.rooms.discard(r)
                        server._room_members[r].discard(member)
                        server._queue_error(
                            outgoing, member, f"banned from {r}", room=r
                        )
            server._queue_notice(outgoing, link, room, f"ban added in {r}")
        else:
            bans.discard(target_hash)
            server.rooms.touch_room(r)
            server.rooms.persist(r)
            server._queue_notice(outgoing, link, room, f"ban removed in {r}")
        return True

    def _cmd_invite(self, server, link, room, parts, outgoing, peer):
        if len(parts) < 3:
            server._queue_notice(
                outgoing,
                link,
                None,
                "usage: /invite <room> add|del|list [nick|hashprefix|hash]",
            )
            return True
        try:
            r = server._norm_room(parts[1])
        except ValueError as e:
            server._queue_notice(outgoing, link, None, "bad room: " + str(e))
            return True
        if not server.rooms.is_room_op(r, peer):
            server._queue_error(outgoing, link, "not authorized", room=r)
            return True
        op = parts[2].lower()
        st = server.rooms.ensure_state(r)
        invited = st.setdefault("invited", {})
        if server.rooms.prune_expired_invites(r):
            server.rooms.persist(r)
        if op == "list":
            now = float(time.time())
            items = []
            for h, exp in invited.items():
                try:
                    exp_f = float(exp)
                except (TypeError, ValueError):
                    continue
                if exp_f > now:
                    items.append(f"{bytes(h).hex()} expires_in={int(exp_f - now)}s")
            server._queue_notice(
                outgoing,
                link,
                room,
                f"invites in {r}: " + (", ".join(sorted(items)) if items else "(none)"),
            )
            return True
        if op not in ("add", "del"):
            server._queue_notice(
                outgoing,
                link,
                room,
                "usage: /invite <room> add|del|list [nick|hashprefix|hash]",
            )
            return True
        if len(parts) < 4:
            server._queue_notice(
                outgoing, link, room, f"usage: /invite {r} {op} <nick|hashprefix|hash>"
            )
            return True
        if op == "add":
            target_link = find_session_by_token(server, parts[3], room=None)
            if target_link is None:
                matches = find_sessions_by_token(server, parts[3], room=None)
                server._queue_error(
                    outgoing,
                    link,
                    f"invite failed: {format_ambiguous_targets(parts[3], matches)}",
                    room=r,
                )
                return True
            tsess = server._sessions.get(target_link)
            ph = tsess.peer if tsess else None
            if not isinstance(ph, (bytes, bytearray)):
                server._queue_error(
                    outgoing, link, "invite failed: target not identified", room=r
                )
                return True
            target_hash = bytes(ph)
            key_val = st.get("key")
            is_keyed = isinstance(key_val, str) and bool(key_val)
            is_invite_only = bool(st.get("invite_only"))
            if is_keyed:
                msg = (
                    f"You have been invited to join {r}. "
                    "This invite allows joining without the key (+k)."
                )
            else:
                msg = f"You have been invited to join {r}."
            server._queue_notice(outgoing, target_link, r, msg)
            if is_keyed or is_invite_only:
                server.rooms.add_invite(r, target_hash, INVITE_DEFAULT_TTL_S)
                server.rooms.touch_room(r)
                server.rooms.persist(r)
                server._queue_notice(
                    outgoing,
                    link,
                    room,
                    f"invite added in {r} (expires in {int(INVITE_DEFAULT_TTL_S)}s)",
                )
            else:
                server._queue_notice(
                    outgoing, link, room, f"invite sent to {parts[3]} for {r}"
                )
            return True
        target_hash, matches = resolve_identity_hash(server, parts[3], room=None)
        if target_hash is None:
            server._queue_notice(
                outgoing, link, room, format_ambiguous_targets(parts[3], matches)
            )
            return True
        invited.pop(target_hash, None)
        server.rooms.touch_room(r)
        server.rooms.persist(r)
        server._queue_notice(outgoing, link, room, f"invite removed in {r}")
        return True
