"""Live Alice/Bob LXMF tests over local TCP loopback.

Two LXMFy bots (Alice = TCP server, Bob = TCP client) exchange messages on
127.0.0.1 and verify:

- ping/pong roundtrip
- reply tickets and outbound stamp cost wiring
- file / image / audio attachments
- icon appearance fields
- structured FIELD_COMMANDS / FIELD_RESULTS
- titled messages
- valid LXMF signatures on real traffic
- rejection of forged invalid signatures (even with verification off)

Requires LXMFY_LIVE_LOCAL=1. Skips otherwise. No public network needed.
"""

from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import time
from pathlib import Path

import pytest

LIVE_ENABLED = os.environ.get("LXMFY_LIVE_LOCAL", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
PATH_TIMEOUT_S = int(os.environ.get("LXMFY_LIVE_LOCAL_PATH_TIMEOUT", "45"))
ROUNDTRIP_TIMEOUT_S = int(os.environ.get("LXMFY_LIVE_LOCAL_ROUNDTRIP_TIMEOUT", "90"))

FILE_BYTES = b"hello-from-bob-file"
IMAGE_BYTES = b"PNGFAKE" + b"\x00" * 24
AUDIO_BYTES = b"AUD" + b"\x01" * 16
ICON_NAME = "account"


def _log(msg: str) -> None:
    print(msg, flush=True)


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _write_rns_config(path: Path, *, server: bool, port: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if server:
        iface = (
            "[[AliceTCP]]\n"
            "  type = TCPServerInterface\n"
            "  enabled = Yes\n"
            "  listen_ip = 127.0.0.1\n"
            f"  listen_port = {port}\n"
        )
    else:
        iface = (
            "[[BobTCP]]\n"
            "  type = TCPClientInterface\n"
            "  enabled = Yes\n"
            "  target_host = 127.0.0.1\n"
            f"  target_port = {port}\n"
        )
    (path / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        f"{iface}",
        encoding="utf-8",
    )


def _drain_outbound(bot) -> None:
    while not bot.queue.empty():
        try:
            lxm = bot.queue.get(block=False)
        except Exception:
            break
        try:
            if bot.router:
                bot.router.handle_outbound(lxm)
        except Exception as e:
            _log(f"outbound error: {e}")


def _remember_peer(peer_hash_hex: str, peer_pub_hex: str) -> None:
    import RNS

    peer = bytes.fromhex(peer_hash_hex)
    RNS.Identity.remember(
        RNS.Identity.full_hash(peer),
        peer,
        bytes.fromhex(peer_pub_hex),
    )


def _wait_path_and_identity(
    peer_hash_hex: str,
    bot,
    stop_event,
    timeout_s: float,
) -> bool:
    import RNS

    peer = bytes.fromhex(peer_hash_hex)
    deadline = time.time() + timeout_s
    while time.time() < deadline and not stop_event.is_set():
        if RNS.Transport.has_path(peer) and RNS.Identity.recall(peer):
            return True
        RNS.Transport.request_path(peer)
        bot.announce_now(force=True)
        _drain_outbound(bot)
        time.sleep(0.4)
    return bool(RNS.Transport.has_path(peer) and RNS.Identity.recall(peer))


def _summarize_fields(fields: dict | None) -> dict:
    import LXMF

    from lxmfy.lxmf_fields import (
        FIELD_COMMANDS,
        FIELD_RESULTS,
        unpack_commands,
        unpack_reply,
    )

    fields = fields or {}
    reply = unpack_reply(fields) or {}
    summary: dict = {
        "keys": sorted(int(k) for k in fields),
        "has_ticket": LXMF.FIELD_TICKET in fields,
        "has_file": LXMF.FIELD_FILE_ATTACHMENTS in fields,
        "has_image": LXMF.FIELD_IMAGE in fields,
        "has_audio": LXMF.FIELD_AUDIO in fields,
        "has_icon": LXMF.FIELD_ICON_APPEARANCE in fields,
        "has_commands": FIELD_COMMANDS in fields,
        "has_results": FIELD_RESULTS in fields,
        "reply_to": reply.get("reply_to"),
        "reply_quote": reply.get("quote"),
        "thread": reply.get("thread"),
    }

    files = fields.get(LXMF.FIELD_FILE_ATTACHMENTS)
    if isinstance(files, list) and files:
        first = files[0]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            summary["file_name"] = first[0]
            summary["file_size"] = (
                len(first[1]) if isinstance(first[1], bytes) else None
            )
            summary["file_data"] = first[1] if isinstance(first[1], bytes) else None

    image = fields.get(LXMF.FIELD_IMAGE)
    if isinstance(image, (list, tuple)) and len(image) >= 2:
        summary["image_format"] = image[0]
        summary["image_size"] = len(image[1]) if isinstance(image[1], bytes) else None
        summary["image_data"] = image[1] if isinstance(image[1], bytes) else None

    audio = fields.get(LXMF.FIELD_AUDIO)
    if isinstance(audio, (list, tuple)) and len(audio) >= 2:
        summary["audio_mode"] = audio[0]
        summary["audio_size"] = len(audio[1]) if isinstance(audio[1], bytes) else None
        summary["audio_data"] = audio[1] if isinstance(audio[1], bytes) else None

    icon = fields.get(LXMF.FIELD_ICON_APPEARANCE)
    if isinstance(icon, (list, tuple)) and len(icon) >= 3:
        summary["icon_name"] = icon[0]
        summary["icon_fg"] = icon[1].hex() if isinstance(icon[1], bytes) else None
        summary["icon_bg"] = icon[2].hex() if isinstance(icon[2], bytes) else None

    cmds = unpack_commands(fields)
    if cmds:
        summary["commands"] = cmds

    results = fields.get(FIELD_RESULTS)
    if results is not None:
        summary["results"] = results

    return summary


def _record_message(sender, message) -> dict:
    raw = message.content
    content = raw.decode("utf-8") if isinstance(raw, bytes) else (raw or "")
    title_raw = getattr(message, "title", None) or b""
    title = (
        title_raw.decode("utf-8") if isinstance(title_raw, bytes) else str(title_raw)
    )
    msg_hash = getattr(message, "hash", None)
    return {
        "sender": sender,
        "content": content,
        "title": title,
        "hash": msg_hash.hex() if isinstance(msg_hash, bytes) else None,
        "signature_validated": bool(getattr(message, "signature_validated", False)),
        "unverified_reason": getattr(message, "unverified_reason", None),
        "fields": _summarize_fields(getattr(message, "fields", None)),
    }


def _alice_worker(
    config_dir: str,
    ready_q: multiprocessing.Queue,
    result_q: multiprocessing.Queue,
    cmd_q: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
) -> None:
    import RNS
    from LXMF import LXMessage

    from lxmfy import (
        BotConfig,
        IconAppearance,
        LXMFBot,
        pack_icon_appearance_field,
    )
    from lxmfy.lxmf_fields import FIELD_RESULTS, pack_result
    from lxmfy.signatures import verify_incoming_message

    os.environ.pop("LXMFY_RETICULUM_CONFIG_DIR", None)
    try:
        bot = LXMFBot(
            **BotConfig(
                name="Alice",
                config_path=config_dir,
                reticulum_config_dir=config_dir,
                storage_path=str(Path(config_dir) / "storage"),
                announce_enabled=True,
                announce_immediately=True,
                first_message_enabled=False,
                landlock_enabled=False,
                cogs_enabled=False,
                message_persistence_enabled=False,
                propagation_fallback_enabled=False,
                signature_verification_enabled=False,
                include_tickets=True,
                lxmf_commands_enabled=True,
                test_mode=False,
            ).__dict__,
        )

        received: list[dict] = []
        alice_icon = pack_icon_appearance_field(
            IconAppearance(ICON_NAME, b"\xff\x00\x00", b"\x00\x00\xff"),
        )

        @bot.command("quiz")
        def quiz(msg):
            answer = msg.ask("quiz_q:what?", timeout=60)
            if answer is None:
                msg.reply("quiz_timeout")
            else:
                msg.reply(f"quiz_done:{answer.content}")
            _drain_outbound(bot)

        @bot.on_message()
        def on_msg(sender, message):
            entry = _record_message(sender, message)
            received.append(entry)
            content = entry["content"]
            fields = entry["fields"]
            _log(f"alice: recv {content!r} title={entry['title']!r} fields={fields}")

            if content.startswith("/"):
                return False

            if content.startswith("ping2:"):
                token = content.split(":", 1)[1]
                bot.send(
                    sender,
                    f"pong2:{token}",
                    title="Pong2",
                    method=LXMessage.OPPORTUNISTIC,
                    reply_to=message.hash,
                    quote=content[:80],
                )
                _drain_outbound(bot)
                return True

            if content.startswith("ping:"):
                token = content.split(":", 1)[1]
                bot.send(
                    sender,
                    f"pong:{token}",
                    title="Pong",
                    method=LXMessage.OPPORTUNISTIC,
                    lxmf_fields=alice_icon,
                )
                _drain_outbound(bot)
                return True

            if fields.get("has_file"):
                bot.send(
                    sender,
                    f"file_ok:{fields.get('file_name')}:{fields.get('file_size')}",
                    title="FileAck",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
                return True

            if fields.get("has_image"):
                bot.send(
                    sender,
                    f"image_ok:{fields.get('image_format')}:{fields.get('image_size')}",
                    title="ImageAck",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
                return True

            if fields.get("has_audio"):
                bot.send(
                    sender,
                    f"audio_ok:{fields.get('audio_mode')}:{fields.get('audio_size')}",
                    title="AudioAck",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
                return True

            if fields.get("has_icon") and content.startswith("icon:"):
                bot.send(
                    sender,
                    f"icon_ok:{fields.get('icon_name')}:{fields.get('icon_fg')}:{fields.get('icon_bg')}",
                    title="IconAck",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
                return True

            if fields.get("has_commands"):
                cmds = fields.get("commands") or []
                cmd = cmds[0] if cmds else {}
                cmd_name = cmd.get("command") or cmd.get("cmd") or "unknown"
                request_id = cmd.get("request_id")
                reply_fields = {
                    FIELD_RESULTS: pack_result(
                        {"echo": cmd_name, "args": cmd.get("args", [])},
                        request_id=request_id,
                        status="ok",
                    ),
                }
                bot.send(
                    sender,
                    f"cmd_ok:{cmd_name}",
                    title="CmdAck",
                    method=LXMessage.OPPORTUNISTIC,
                    lxmf_fields=reply_fields,
                )
                _drain_outbound(bot)
                return True

            if content.startswith("titleprobe:"):
                bot.send(
                    sender,
                    f"title_ok:{entry['title']}",
                    title="TitleAck",
                    method=LXMessage.OPPORTUNISTIC,
                )
                _drain_outbound(bot)
                return True

            return True

        assert bot.local is not None
        local_hash = RNS.hexrep(bot.local.hash, delimit=False)
        local_pub = bot.identity.get_public_key().hex()
        ready_q.put(("alice", local_hash, local_pub))
        bot.announce_now(force=True)
        _drain_outbound(bot)

        while not stop_event.is_set():
            while not cmd_q.empty():
                cmd = cmd_q.get()
                if not isinstance(cmd, tuple) or not cmd:
                    continue
                action = cmd[0]
                if action == "forge_invalid_signature":
                    try:
                        lxm = LXMessage(
                            bot.local,
                            bot.local,
                            b"forged-invalid",
                            title=b"",
                            desired_method=LXMessage.OPPORTUNISTIC,
                        )
                        lxm.defer_stamp = False
                        lxm.pack()
                        packed = bytearray(lxm.packed)
                        sig_start = LXMessage.DESTINATION_LENGTH * 2
                        packed[sig_start] ^= 0xFF
                        forged = LXMessage.unpack_from_bytes(bytes(packed))
                        sender = RNS.hexrep(forged.source_hash, delimit=False)
                        dropped = verify_incoming_message(bot, forged, sender) is False
                        result_q.put(
                            (
                                "alice",
                                "forge_result",
                                {
                                    "signature_validated": bool(
                                        forged.signature_validated,
                                    ),
                                    "unverified_reason": forged.unverified_reason,
                                    "dropped": dropped,
                                    "expected_reason": LXMessage.SIGNATURE_INVALID,
                                },
                            ),
                        )
                    except Exception as e:
                        result_q.put(("alice", "forge_error", str(e)))
                elif action == "snapshot":
                    # Strip raw bytes from snapshot for queue friendliness.
                    snap = []
                    for item in received:
                        copy = dict(item)
                        fields = dict(copy.get("fields") or {})
                        for key in ("file_data", "image_data", "audio_data"):
                            fields.pop(key, None)
                        copy["fields"] = fields
                        snap.append(copy)
                    result_q.put(("alice", "snapshot", snap))
                elif action == "remember_peer":
                    _remember_peer(cmd[1], cmd[2])
            if int(time.time()) % 8 == 0:
                bot.announce_now(force=True)
            _drain_outbound(bot)
            time.sleep(0.2)

        result_q.put(("alice", "stopped", len(received)))
    except Exception as e:
        _log(f"alice: error {e}")
        result_q.put(("alice", "error", str(e)))
    finally:
        try:
            import RNS

            RNS.Reticulum.exit_handler()
        except Exception:
            pass
        os._exit(0)


def _bob_worker(
    config_dir: str,
    alice_hash_hex: str,
    alice_pub_hex: str,
    ready_q: multiprocessing.Queue,
    result_q: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
) -> None:
    import RNS
    from LXMF import LXMessage

    from lxmfy import (
        Attachment,
        AttachmentType,
        BotConfig,
        IconAppearance,
        LXMFBot,
        pack_icon_appearance_field,
    )
    from lxmfy.lxmf_fields import FIELD_COMMANDS

    os.environ.pop("LXMFY_RETICULUM_CONFIG_DIR", None)
    try:
        bot = LXMFBot(
            **BotConfig(
                name="Bob",
                config_path=config_dir,
                reticulum_config_dir=config_dir,
                storage_path=str(Path(config_dir) / "storage"),
                announce_enabled=True,
                announce_immediately=True,
                first_message_enabled=False,
                landlock_enabled=False,
                cogs_enabled=False,
                message_persistence_enabled=False,
                propagation_fallback_enabled=False,
                signature_verification_enabled=False,
                include_tickets=True,
                test_mode=False,
            ).__dict__,
        )

        received: list[dict] = []
        send_meta: dict = {}

        @bot.on_message()
        def on_msg(sender, message):
            entry = _record_message(sender, message)
            # Drop raw bytes before queueing results later.
            fields = dict(entry["fields"])
            for key in ("file_data", "image_data", "audio_data"):
                fields.pop(key, None)
            entry["fields"] = fields
            received.append(entry)
            _log(f"bob: recv {entry['content']!r} title={entry['title']!r}")
            return True

        assert bot.local is not None
        local_hash = RNS.hexrep(bot.local.hash, delimit=False)
        local_pub = bot.identity.get_public_key().hex()
        ready_q.put(("bob", local_hash, local_pub))
        _remember_peer(alice_hash_hex, alice_pub_hex)
        bot.announce_now(force=True)
        _drain_outbound(bot)

        if not _wait_path_and_identity(
            alice_hash_hex,
            bot,
            stop_event,
            PATH_TIMEOUT_S,
        ):
            result_q.put(
                (
                    "bob",
                    "no_identity_or_path",
                    {
                        "has_path": RNS.Transport.has_path(
                            bytes.fromhex(alice_hash_hex),
                        ),
                        "identity": RNS.Identity.recall(bytes.fromhex(alice_hash_hex))
                        is not None,
                    },
                ),
            )
            return

        token = f"alice-bob-{os.getpid()}-{int(time.time())}"
        _log(f"bob: path+identity ok, starting scenarios token={token}")

        original_enqueue = bot._enqueue_outbound
        sent_lxms: list = []

        def enqueue_with_meta(lxm):
            sent_lxms.append(lxm)
            send_meta.setdefault("sends", [])
            send_meta["sends"].append(
                {
                    "include_ticket": bool(getattr(lxm, "include_ticket", False)),
                    "stamp_cost": getattr(lxm, "stamp_cost", "missing"),
                    "desired_method": getattr(lxm, "desired_method", None),
                    "has_fields": bool(getattr(lxm, "fields", None)),
                },
            )
            send_meta["include_ticket"] = bool(getattr(lxm, "include_ticket", False))
            send_meta["stamp_cost"] = getattr(lxm, "stamp_cost", "missing")
            return original_enqueue(lxm)

        bot._enqueue_outbound = enqueue_with_meta

        def wait_for(prefix: str, timeout: float = ROUNDTRIP_TIMEOUT_S) -> dict | None:
            deadline = time.time() + timeout
            while time.time() < deadline and not stop_event.is_set():
                _drain_outbound(bot)
                for item in received:
                    if item["content"].startswith(prefix):
                        return item
                time.sleep(0.2)
            return None

        # 1) Plain ping/pong with title + icon on reply
        if not bot.send(
            alice_hash_hex,
            f"ping:{token}",
            title="Ping",
            method=LXMessage.OPPORTUNISTIC,
        ):
            result_q.put(("bob", "send_failed", "ping"))
            return
        _drain_outbound(bot)
        pong = wait_for(f"pong:{token}")
        if pong is None:
            result_q.put(
                ("bob", "timeout", {"stage": "ping", "received": received[-5:]}),
            )
            return

        # 2) File attachment
        bot.send_with_attachment(
            alice_hash_hex,
            f"file:{token}",
            Attachment(
                type=AttachmentType.FILE,
                name="note.txt",
                data=FILE_BYTES,
            ),
            title="FileSend",
        )
        _drain_outbound(bot)
        file_ack = wait_for("file_ok:")
        if file_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "file", "received": received[-5:]}),
            )
            return

        # 3) Image attachment
        bot.send(
            alice_hash_hex,
            f"image:{token}",
            title="ImageSend",
            method=LXMessage.OPPORTUNISTIC,
            lxmf_fields={
                __import__("LXMF").FIELD_IMAGE: ["png", IMAGE_BYTES],
            },
        )
        _drain_outbound(bot)
        image_ack = wait_for("image_ok:")
        if image_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "image", "received": received[-5:]}),
            )
            return

        # 4) Audio attachment
        bot.send_with_attachment(
            alice_hash_hex,
            f"audio:{token}",
            Attachment(
                type=AttachmentType.AUDIO,
                name="clip",
                data=AUDIO_BYTES,
                format="1",
            ),
            title="AudioSend",
        )
        _drain_outbound(bot)
        audio_ack = wait_for("audio_ok:")
        if audio_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "audio", "received": received[-5:]}),
            )
            return

        # 5) Icon appearance field
        bot.send(
            alice_hash_hex,
            f"icon:{token}",
            title="IconSend",
            method=LXMessage.OPPORTUNISTIC,
            lxmf_fields=pack_icon_appearance_field(
                IconAppearance(ICON_NAME, b"\x11\x22\x33", b"\xaa\xbb\xcc"),
            ),
        )
        _drain_outbound(bot)
        icon_ack = wait_for("icon_ok:")
        if icon_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "icon", "received": received[-5:]}),
            )
            return

        # 6) Structured LXMF command field
        bot.send(
            alice_hash_hex,
            f"cmdbody:{token}",
            title="CmdSend",
            method=LXMessage.OPPORTUNISTIC,
            lxmf_fields={
                FIELD_COMMANDS: {
                    "command": "echo",
                    "args": ["hi", token],
                    "request_id": f"req-{token}",
                },
            },
        )
        _drain_outbound(bot)
        cmd_ack = wait_for("cmd_ok:")
        if cmd_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "cmd", "received": received[-5:]}),
            )
            return

        # 7) Title roundtrip
        bot.send(
            alice_hash_hex,
            f"titleprobe:{token}",
            title="Fancy Title",
            method=LXMessage.OPPORTUNISTIC,
        )
        _drain_outbound(bot)
        title_ack = wait_for("title_ok:")
        if title_ack is None:
            result_q.put(
                ("bob", "timeout", {"stage": "title", "received": received[-5:]}),
            )
            return

        # 8) Reply threading: alice quotes the ping2 hash back
        ping2_idx = len(sent_lxms)
        if not bot.send(
            alice_hash_hex,
            f"ping2:{token}",
            title="Ping2",
            method=LXMessage.OPPORTUNISTIC,
        ):
            result_q.put(("bob", "send_failed", "ping2"))
            return
        _drain_outbound(bot)
        pong2 = wait_for(f"pong2:{token}")
        if pong2 is None:
            result_q.put(
                ("bob", "timeout", {"stage": "pong2", "received": received[-5:]}),
            )
            return

        # 9) Conversation API: /quiz asks, bob's next message answers
        quiz_idx = len(sent_lxms)
        if not bot.send(
            alice_hash_hex,
            "/quiz",
            method=LXMessage.OPPORTUNISTIC,
        ):
            result_q.put(("bob", "send_failed", "quiz"))
            return
        _drain_outbound(bot)
        quiz_prompt = wait_for("quiz_q:")
        if quiz_prompt is None:
            result_q.put(
                ("bob", "timeout", {"stage": "quiz_q", "received": received[-5:]}),
            )
            return
        bot.send(
            alice_hash_hex,
            f"quizanswer:{token}",
            method=LXMessage.OPPORTUNISTIC,
        )
        _drain_outbound(bot)
        quiz_done = wait_for(f"quiz_done:quizanswer:{token}")
        if quiz_done is None:
            result_q.put(
                ("bob", "timeout", {"stage": "quiz_done", "received": received[-5:]}),
            )
            return

        ping2_lxm = sent_lxms[ping2_idx] if ping2_idx < len(sent_lxms) else None
        ping2_hash = ping2_lxm.hash.hex() if getattr(ping2_lxm, "hash", None) else None
        quiz_lxm = sent_lxms[quiz_idx] if quiz_idx < len(sent_lxms) else None
        quiz_hash = quiz_lxm.hash.hex() if getattr(quiz_lxm, "hash", None) else None

        # 10) Peer announce metadata + inbound introspection
        peer_app_data = bot.get_peer_app_data(alice_hash_hex)
        peer_lxmf = bot.get_peer_lxmf_data(alice_hash_hex)
        peer_announce = bot.get_peer_announce(alice_hash_hex)
        inbound = {
            "count": bot.inbound_count(),
            "transfers": bot.inbound_transfers(),
            "has_pong2": bot.has_message(pong2.get("hash") or ""),
            "has_bogus": bot.has_message(b"\x00" * 32),
        }

        result_q.put(
            (
                "bob",
                "ok",
                {
                    "token": token,
                    "pong": pong,
                    "file_ack": file_ack,
                    "image_ack": image_ack,
                    "audio_ack": audio_ack,
                    "icon_ack": icon_ack,
                    "cmd_ack": cmd_ack,
                    "title_ack": title_ack,
                    "pong2": pong2,
                    "ping2_hash": ping2_hash,
                    "quiz_hash": quiz_hash,
                    "quiz_prompt": quiz_prompt,
                    "quiz_done": quiz_done,
                    "peer_app_data": peer_app_data,
                    "peer_lxmf": peer_lxmf,
                    "peer_announce": peer_announce,
                    "inbound": inbound,
                    "send_meta": send_meta,
                    "received": received,
                },
            ),
        )
    except Exception as e:
        _log(f"bob: error {e}")
        result_q.put(("bob", "error", str(e)))
    finally:
        try:
            import RNS

            RNS.Reticulum.exit_handler()
        except Exception:
            pass
        os._exit(0)


def _collect(result_q: multiprocessing.Queue) -> list:
    out = []
    while not result_q.empty():
        out.append(result_q.get())
    return out


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="Set LXMFY_LIVE_LOCAL=1 to run Alice/Bob local LXMF live tests",
)
def test_alice_bob_local_roundtrip_and_signatures(tmp_path):
    """Alice and Bob exercise LXMF messaging features on localhost."""
    port = _free_port()
    alice_dir = tmp_path / "alice"
    bob_dir = tmp_path / "bob"
    _write_rns_config(alice_dir, server=True, port=port)
    _write_rns_config(bob_dir, server=False, port=port)

    ready_q: multiprocessing.Queue = multiprocessing.Queue()
    result_q: multiprocessing.Queue = multiprocessing.Queue()
    cmd_q: multiprocessing.Queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    alice = multiprocessing.Process(
        target=_alice_worker,
        args=(str(alice_dir), ready_q, result_q, cmd_q, stop_event),
    )
    alice.start()

    alice_hash = alice_pub = None
    ready_deadline = time.time() + 45
    while time.time() < ready_deadline:
        if not ready_q.empty():
            role, value, pub = ready_q.get()
            if role == "alice":
                alice_hash, alice_pub = value, pub
                break
        if not alice.is_alive():
            break
        time.sleep(0.2)

    if not alice_hash or not alice_pub:
        stop_event.set()
        alice.terminate()
        alice.join(timeout=5)
        pytest.fail(f"alice failed to start: {_collect(result_q)}")

    cmd_q.put(("forge_invalid_signature",))
    forge = None
    forge_deadline = time.time() + 20
    while time.time() < forge_deadline:
        results = _collect(result_q)
        for item in results:
            if item[0] == "alice" and item[1] == "forge_result":
                forge = item[2]
                break
            if item[0] == "alice" and item[1] in {"forge_error", "error"}:
                stop_event.set()
                alice.terminate()
                alice.join(timeout=5)
                pytest.fail(f"forge check failed: {item}")
        if forge is not None:
            break
        if not alice.is_alive():
            pytest.fail(f"alice died during forge check: {_collect(result_q)}")
        time.sleep(0.2)

    assert forge is not None, "alice did not report forge_result"
    assert forge["signature_validated"] is False
    assert forge["unverified_reason"] == forge["expected_reason"]
    assert forge["dropped"] is True
    _log(f"LIVE_LOCAL_FORGE_PROVED {forge}")

    bob = multiprocessing.Process(
        target=_bob_worker,
        args=(
            str(bob_dir),
            alice_hash,
            alice_pub,
            ready_q,
            result_q,
            stop_event,
        ),
    )
    bob.start()

    bob_hash = bob_pub = None
    ready_deadline = time.time() + 45
    while time.time() < ready_deadline:
        if not ready_q.empty():
            role, value, pub = ready_q.get()
            if role == "bob":
                bob_hash, bob_pub = value, pub
                break
        if not bob.is_alive():
            break
        time.sleep(0.2)

    if bob_hash and bob_pub:
        cmd_q.put(("remember_peer", bob_hash, bob_pub))

    bob.join(timeout=PATH_TIMEOUT_S + ROUNDTRIP_TIMEOUT_S + 60)
    stop_event.set()
    cmd_q.put(("snapshot",))
    alice.join(timeout=10)
    for proc in (bob, alice):
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=5)

    results = _collect(result_q)
    _log(f"results: {results}")

    bob_ok = next((r for r in results if r[0] == "bob" and r[1] == "ok"), None)
    assert bob_ok is not None, f"bob scenarios failed: {results}"
    payload = bob_ok[2]
    token = payload["token"]

    pong = payload["pong"]
    assert pong["signature_validated"] is True
    assert pong["title"] == "Pong"
    assert pong["fields"]["has_icon"] is True
    assert pong["fields"]["icon_name"] == ICON_NAME

    assert payload["file_ack"]["content"] == f"file_ok:note.txt:{len(FILE_BYTES)}"
    assert payload["image_ack"]["content"] == f"image_ok:png:{len(IMAGE_BYTES)}"
    assert payload["audio_ack"]["content"] == f"audio_ok:1:{len(AUDIO_BYTES)}"
    assert payload["icon_ack"]["content"] == "icon_ok:account:112233:aabbcc"
    assert payload["cmd_ack"]["content"] == "cmd_ok:echo"
    assert payload["cmd_ack"]["fields"]["has_results"] is True
    assert payload["cmd_ack"]["fields"]["results"]["request_id"] == f"req-{token}"
    assert payload["cmd_ack"]["fields"]["results"]["status"] == "ok"
    assert payload["title_ack"]["content"] == "title_ok:Fancy Title"

    pong2 = payload["pong2"]
    assert payload["ping2_hash"] is not None
    assert pong2["fields"]["reply_to"] == payload["ping2_hash"]
    assert pong2["fields"]["reply_quote"] == f"ping2:{token}"
    assert pong2["fields"]["thread"] == payload["ping2_hash"]

    assert payload["quiz_prompt"]["content"] == "quiz_q:what?"
    assert payload["quiz_done"]["content"] == f"quiz_done:quizanswer:{token}"
    assert payload["quiz_done"]["fields"]["reply_to"] == payload["quiz_hash"]

    assert isinstance(payload["peer_app_data"], bytes)
    assert payload["peer_lxmf"]["display_name"] == "Alice"
    announce = payload["peer_announce"]
    assert announce["destination"] == alice_hash
    assert announce["app_data"] == payload["peer_app_data"]
    assert announce["received_at"] > 0

    inbound = payload["inbound"]
    assert inbound["count"] == 0
    assert inbound["transfers"] == []
    assert inbound["has_pong2"] is True
    assert inbound["has_bogus"] is False

    assert payload["send_meta"].get("include_ticket") is True
    assert payload["send_meta"].get("stamp_cost") is None
    assert len(payload["send_meta"].get("sends") or []) >= 10

    alice_snap = next(
        (r for r in results if r[0] == "alice" and r[1] == "snapshot"),
        None,
    )
    if alice_snap:
        alice_msgs = alice_snap[2]
        file_msg = next((m for m in alice_msgs if m["fields"].get("has_file")), None)
        assert file_msg is not None
        assert file_msg["fields"]["file_name"] == "note.txt"
        assert file_msg["fields"]["has_ticket"] is True

    _log(
        f"LIVE_LOCAL_ALICE_BOB_PROVED token={token} "
        f"sends={len(payload['send_meta'].get('sends') or [])}",
    )


if __name__ == "__main__":
    if not LIVE_ENABLED:
        print("Set LXMFY_LIVE_LOCAL=1", file=sys.stderr)
        raise SystemExit(2)
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        test_alice_bob_local_roundtrip_and_signatures(Path(td))
