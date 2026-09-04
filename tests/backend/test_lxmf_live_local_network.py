# SPDX-License-Identifier: 0BSD

"""Live two-peer LXMF delivery over loopback TCP.

Spins up a TCPServerInterface peer and a TCPClientInterface peer on
127.0.0.1, announces lxmf.delivery, finds a path, and delivers real
LXMF messages across the link. Parent process can feed received
payloads into MeshChatX on_lxmf_delivery for store/reject oracles.

Covers text, images, voice notes, file attachments, Sideband/bot
commands, telemetry, icon appearance, and reactions.

Enable with MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from unittest.mock import MagicMock

import LXMF
import pytest

from meshchatx.src.backend.lxmf_utils import (
    FIELD_REACTION,
    REACTION_CONTENT,
    REACTION_TO,
    convert_lxmf_message_to_dict,
)
from meshchatx.src.backend.sideband_commands import SidebandCommands
from meshchatx.src.backend.telemetry_utils import Telemeter
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)
from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

_PATH_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_LOCAL_PATH_TIMEOUT", "40"))
_DELIVERY_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_LOCAL_DELIVERY_TIMEOUT", "45"))

# Shared recursive JSON field codec used inside Bob/Alice subprocesses.
_FIELD_CODEC = textwrap.dedent(
    """\
    import base64

    def _jsonify(obj):
        if isinstance(obj, (bytes, bytearray)):
            return {"__b64__": base64.b64encode(bytes(obj)).decode()}
        if isinstance(obj, dict):
            return {str(k): _jsonify(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_jsonify(x) for x in obj]
        if isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        return str(obj)

    def _parse_key(key):
        if isinstance(key, int):
            return key
        text = str(key)
        if text.startswith("0x"):
            try:
                return int(text, 16)
            except ValueError:
                return key
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        return key

    def _unjsonify(obj):
        if isinstance(obj, dict):
            if set(obj.keys()) == {"__b64__"}:
                return base64.b64decode(obj["__b64__"])
            return {_parse_key(k): _unjsonify(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_unjsonify(x) for x in obj]
        return obj
    """,
)

_BOB_SCRIPT = _FIELD_CODEC + textwrap.dedent(
    """\
    import json
    import os
    import sys
    import time

    import LXMF
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    stop_path = os.path.join(share_dir, "stop")
    ready_path = os.path.join(share_dir, "ready.json")
    inbox_path = os.path.join(share_dir, "inbox.json")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    dest = router.register_delivery_identity(identity, display_name="bob")

    def on_delivery(message):
        with open(inbox_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "content": message.content_as_string(),
                    "title": message.title_as_string(),
                    "src": message.source_hash.hex(),
                    "dst": message.destination_hash.hex(),
                    "hash": message.hash.hex(),
                    "sig_ok": bool(message.signature_validated),
                    "unverified_reason": message.unverified_reason,
                    "fields": _jsonify(message.get_fields() or {}),
                },
                handle,
            )

    router.register_delivery_callback(on_delivery)
    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "dest": dest.hash.hex(),
                "pub": identity.get_public_key().hex(),
            },
            handle,
        )

    deadline = time.time() + timeout_s + 30
    while time.time() < deadline and not os.path.isfile(stop_path):
        dest.announce()
        if os.path.isfile(inbox_path):
            time.sleep(0.5)
            break
        time.sleep(2)
    RNS.exit(0)
    """,
)

_ALICE_SCRIPT = _FIELD_CODEC + textwrap.dedent(
    """\
    import json
    import os
    import sys
    import time

    import LXMF
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    payload_path = os.path.join(share_dir, "payload.json")
    ready_path = os.path.join(share_dir, "ready.json")
    result_path = os.path.join(share_dir, "send.json")
    inbox_path = os.path.join(share_dir, "inbox.json")

    payload = {"content": "hello local mesh", "title": "ping", "fields": {}}
    if os.path.isfile(payload_path):
        with open(payload_path, encoding="utf-8") as handle:
            payload = json.load(handle)

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    local = router.register_delivery_identity(identity, display_name="alice")

    deadline = time.time() + 30
    while time.time() < deadline and not os.path.isfile(ready_path):
        time.sleep(0.2)
    if not os.path.isfile(ready_path):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_ready"}, handle)
        RNS.exit(1)

    with open(ready_path, encoding="utf-8") as handle:
        peer = json.load(handle)

    bob = RNS.Identity(create_keys=False)
    bob.load_public_key(bytes.fromhex(peer["pub"]))
    bob_hash = bytes.fromhex(peer["dest"])

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        local.announce()
        if RNS.Transport.has_path(bob_hash):
            break
        RNS.Transport.request_path(bob_hash)
        time.sleep(1)
    if not RNS.Transport.has_path(bob_hash):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_path"}, handle)
        RNS.exit(1)

    destination = RNS.Destination(
        bob, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery",
    )

    fields = _unjsonify(payload.get("fields") or {})
    msg = LXMF.LXMessage(
        destination,
        local,
        content=payload.get("content") or "",
        title=payload.get("title") or "",
        fields=fields,
        desired_method=LXMF.LXMessage.DIRECT,
    )
    router.handle_outbound(msg)

    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "ok": True,
                "state": int(msg.state) if msg.state is not None else None,
                "src": local.hash.hex(),
                "dst": peer["dest"],
                "has_path": bool(RNS.Transport.has_path(bob_hash)),
                "msg_hash": msg.hash.hex() if msg.hash else None,
            },
            handle,
        )

    deadline = time.time() + 25
    while time.time() < deadline:
        if os.path.isfile(inbox_path):
            break
        time.sleep(0.3)
    time.sleep(0.5)
    RNS.exit(0)
    """,
)


def _jsonify(obj):
    if isinstance(obj, (bytes, bytearray)):
        return {"__b64__": base64.b64encode(bytes(obj)).decode()}
    if isinstance(obj, dict):
        return {str(k): _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(x) for x in obj]
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def _parse_key(key):
    if isinstance(key, int):
        return key
    text = str(key)
    if text.startswith("0x"):
        try:
            return int(text, 16)
        except ValueError:
            return key
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    return key


def _unjsonify(obj):
    if isinstance(obj, dict):
        if set(obj.keys()) == {"__b64__"}:
            return base64.b64decode(obj["__b64__"])
        return {_parse_key(k): _unjsonify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_unjsonify(x) for x in obj]
    return obj


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _write_pair(server_dir: Path, client_dir: Path, port: int) -> None:
    server_dir.mkdir(parents=True, exist_ok=True)
    client_dir.mkdir(parents=True, exist_ok=True)
    (server_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        f"shared_instance_port = {37000 + (port % 1000)}\n"
        f"instance_name = lxmf_bob_{port}\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        "  [[TCP Server]]\n"
        "    type = TCPServerInterface\n"
        "    enabled = Yes\n"
        "    listen_ip = 127.0.0.1\n"
        f"    listen_port = {port}\n",
        encoding="utf-8",
    )
    (client_dir / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        f"shared_instance_port = {38000 + (port % 1000)}\n"
        f"instance_name = lxmf_alice_{port}\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 3\n"
        "\n"
        "[interfaces]\n"
        "  [[TCP Client]]\n"
        "    type = TCPClientInterface\n"
        "    enabled = Yes\n"
        "    target_host = 127.0.0.1\n"
        f"    target_port = {port}\n",
        encoding="utf-8",
    )


def _run_local_delivery(tmp_path: Path, payload: dict | None = None) -> dict:
    port = _free_port()
    bob_dir = tmp_path / "bob"
    alice_dir = tmp_path / "alice"
    share_dir = tmp_path / "share"
    share_dir.mkdir(parents=True, exist_ok=True)
    _write_pair(bob_dir, alice_dir, port)

    if payload is not None:
        wire_payload = {
            "content": payload.get("content") or "",
            "title": payload.get("title") or "",
            "fields": _jsonify(payload.get("fields") or {}),
        }
        (share_dir / "payload.json").write_text(
            json.dumps(wire_payload),
            encoding="utf-8",
        )

    env = subprocess_test_env()
    bob = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _BOB_SCRIPT,
            str(bob_dir),
            str(share_dir),
            str(_PATH_TIMEOUT_S),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    alice = None
    try:
        ready = share_dir / "ready.json"
        deadline = time.time() + 25
        while time.time() < deadline and not ready.is_file():
            if bob.poll() is not None:
                stdout, stderr = bob.communicate(timeout=5)
                raise AssertionError(
                    f"bob exited {bob.returncode}: {stderr}\n{stdout}",
                )
            time.sleep(0.2)
        assert ready.is_file(), "bob did not write ready.json"

        alice = subprocess.Popen(
            [
                sys.executable,
                "-c",
                _ALICE_SCRIPT,
                str(alice_dir),
                str(share_dir),
                str(_PATH_TIMEOUT_S),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        inbox = share_dir / "inbox.json"
        send_path = share_dir / "send.json"
        deadline = time.time() + _DELIVERY_TIMEOUT_S
        while time.time() < deadline and not inbox.is_file():
            if alice.poll() is not None and not inbox.is_file():
                stdout, stderr = alice.communicate(timeout=5)
                send_body = ""
                if send_path.is_file():
                    send_body = send_path.read_text(encoding="utf-8")
                raise AssertionError(
                    f"alice exited {alice.returncode} without inbox: "
                    f"{stderr}\n{stdout}\n{send_body}",
                )
            time.sleep(0.2)

        assert inbox.is_file(), "bob did not receive LXMF over local TCP"
        deadline = time.time() + 10
        while time.time() < deadline and not send_path.is_file():
            time.sleep(0.1)
        inbox_data = json.loads(inbox.read_text(encoding="utf-8"))
        send_data = {}
        if send_path.is_file():
            send_data = json.loads(send_path.read_text(encoding="utf-8"))
        return {
            "inbox": inbox_data,
            "send": send_data,
            "ready": json.loads(ready.read_text(encoding="utf-8")),
        }
    finally:
        (share_dir / "stop").write_text("1", encoding="utf-8")
        if alice is not None and alice.poll() is None:
            try:
                alice.wait(timeout=8)
            except subprocess.TimeoutExpired:
                alice.kill()
        if bob.poll() is None:
            try:
                bob.wait(timeout=8)
            except subprocess.TimeoutExpired:
                bob.kill()


def _fields_from_live(live: dict) -> dict:
    return _unjsonify(live.get("fields") or {})


def _delivery_from_local(app, live: dict):
    msg = make_inbound_lxmf(
        source_hash=live["src"],
        destination_hash=LOCAL_LXMF,
        content=live.get("content") or "",
        title=live.get("title") or "",
        fields=_fields_from_live(live),
        msg_hash=bytes.fromhex(live["hash"]) if live.get("hash") else None,
    )
    msg.signature_validated = bool(live.get("sig_ok"))
    if live.get("unverified_reason") is not None:
        msg.unverified_reason = live["unverified_reason"]
    app.on_lxmf_delivery(msg)
    return msg


def _b64_field(live: dict, field_id: int):
    raw = (live.get("fields") or {}).get(str(field_id))
    if raw is None:
        raw = (live.get("fields") or {}).get(field_id)
    return raw


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_text_delivery(tmp_path):
    result = _run_local_delivery(
        tmp_path,
        payload={"content": "hello local mesh", "title": "ping", "fields": {}},
    )
    inbox = result["inbox"]
    send = result["send"]
    assert inbox["ok"] is True
    assert inbox["content"] == "hello local mesh"
    assert inbox["title"] == "ping"
    assert inbox["sig_ok"] is True
    assert inbox["unverified_reason"] is None
    assert send.get("ok") is True
    assert send.get("has_path") is True
    assert inbox["src"] == send["src"]
    assert inbox["dst"] == result["ready"]["dest"]


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_image_attachment_delivery(tmp_path):
    secret = b"LOCAL_TCP_IMG_SECRET_19"
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "see attached",
            "title": "pic",
            "fields": {LXMF.FIELD_IMAGE: ["png", b"\x89PNG" + secret]},
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True
    image = _b64_field(inbox, LXMF.FIELD_IMAGE)
    assert image is not None
    assert image[0] == "png"
    assert base64.b64decode(image[1]["__b64__"]).endswith(secret)


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_voice_note_delivery(tmp_path, mock_app):
    secret = b"LOCAL_TCP_VOICE_NOTE_91"
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "",
            "title": "voice",
            "fields": {LXMF.FIELD_AUDIO: [LXMF.AM_OPUS_OGG, secret]},
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True
    audio = _b64_field(inbox, LXMF.FIELD_AUDIO)
    assert audio is not None
    assert audio[0] == LXMF.AM_OPUS_OGG
    assert base64.b64decode(audio[1]["__b64__"]) == secret

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    fields = json.loads(row["fields"] or "{}")
    assert fields["audio"]["audio_mode"] == LXMF.AM_OPUS_OGG
    assert fields["audio"]["audio_size"] == len(secret)
    converted = convert_lxmf_message_to_dict(msg, include_attachments=True)
    assert (
        converted["fields"]["audio"]["audio_bytes"]
        == base64.b64encode(
            secret,
        ).decode()
    )


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_file_attachment_delivery(tmp_path, mock_app):
    secret = b"LOCAL_TCP_FILE_BYTES_33"
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "docs",
            "title": "files",
            "fields": {
                LXMF.FIELD_FILE_ATTACHMENTS: [["notes.txt", secret]],
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    files = _b64_field(inbox, LXMF.FIELD_FILE_ATTACHMENTS)
    assert files is not None
    assert files[0][0] == "notes.txt"
    assert base64.b64decode(files[0][1]["__b64__"]) == secret

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    fields = json.loads(row["fields"] or "{}")
    assert fields["file_attachments"][0]["file_name"] == "notes.txt"
    assert fields["file_attachments"][0]["file_size"] == len(secret)


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_sideband_telemetry_request_command(tmp_path, mock_app):
    ts = int(time.time())
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "",
            "title": "",
            "fields": {
                LXMF.FIELD_COMMANDS: [
                    {SidebandCommands.TELEMETRY_REQUEST: ts},
                ],
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True
    cmds = _b64_field(inbox, LXMF.FIELD_COMMANDS)
    assert cmds is not None
    assert cmds[0][str(SidebandCommands.TELEMETRY_REQUEST)] == ts

    app = prepare_messaging_app(mock_app)
    app.config.telemetry_enabled.set(True)
    app.config.location_source.set("manual")
    app.config.location_manual_lat.set(51.5)
    app.config.location_manual_lon.set(-0.12)
    app.handle_telemetry_request = MagicMock()
    app.database.contacts.add_contact(
        "Trusted",
        inbox["src"],
        lxmf_address=inbox["src"],
        is_telemetry_trusted=True,
    )
    msg = _delivery_from_local(app, inbox)
    app.handle_telemetry_request.assert_called_once_with(inbox["src"])
    converted = convert_lxmf_message_to_dict(msg, include_attachments=False)
    assert converted["fields"]["commands"][0]["0x01"] == ts


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_legacy_field01_telemetry_request(tmp_path, mock_app):
    """Sideband-shaped field 0x01 still counts as a telemetry request."""
    ts = int(time.time())
    secret = b"LOCAL_TCP_TELEM_STRIP_44"
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "ping",
            "title": "",
            "fields": {
                0x01: [{SidebandCommands.TELEMETRY_REQUEST: ts}],
                LXMF.FIELD_IMAGE: ["png", b"\x89PNG" + secret],
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert _b64_field(inbox, 0x01) is not None
    assert _b64_field(inbox, LXMF.FIELD_IMAGE) is not None

    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    app.config.telemetry_enabled.set(True)
    app.handle_telemetry_request = MagicMock()
    msg = _delivery_from_local(app, inbox)
    # Stranger: no respond, but attachments stripped and message kept.
    app.handle_telemetry_request.assert_not_called()
    row = stored_message(app, msg)
    assert row is not None
    assert int(row["attachments_stripped"] or 0) == 1
    assert LXMF.FIELD_IMAGE not in msg.get_fields()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_plugin_bot_command_requires_signature(tmp_path, mock_app):
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "",
            "title": "",
            "fields": {
                LXMF.FIELD_COMMANDS: [
                    {SidebandCommands.PLUGIN_COMMAND: "do_thing"},
                ],
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True

    app = prepare_messaging_app(mock_app)
    app.sideband_plugin_loader = MagicMock()
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    _delivery_from_local(app, inbox)
    app.sideband_plugin_loader.handle_plugin_command.assert_called_once()
    assert (
        app.sideband_plugin_loader.handle_plugin_command.call_args[0][0] == "do_thing"
    )

    # Unsigned must not invoke plugin handlers.
    app2 = prepare_messaging_app(mock_app)
    app2.sideband_plugin_loader = MagicMock()
    inbox_bad = dict(inbox)
    inbox_bad["sig_ok"] = False
    inbox_bad["hash"] = os.urandom(32).hex()
    _delivery_from_local(app2, inbox_bad)
    app2.sideband_plugin_loader.handle_plugin_command.assert_not_called()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_telemetry_ingest(tmp_path, mock_app):
    ts = 1_736_264_575
    packed = Telemeter.pack(
        time_utc=ts,
        location={"latitude": 52.52, "longitude": 13.405, "last_update": ts},
    )
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "here",
            "title": "telemetry",
            "fields": {LXMF.FIELD_TELEMETRY: packed},
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True
    wire = _b64_field(inbox, LXMF.FIELD_TELEMETRY)
    assert wire is not None
    assert base64.b64decode(wire["__b64__"]) == packed

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    telem = app.database.telemetry.get_latest_telemetry(inbox["src"])
    assert telem is not None
    assert bytes(telem["data"]) == packed
    decoded = Telemeter.from_packed(bytes(telem["data"]))
    assert decoded["location"]["latitude"] == 52.52
    assert decoded["location"]["longitude"] == 13.405


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_icon_appearance(tmp_path, mock_app):
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "hi",
            "title": "",
            "fields": {
                LXMF.FIELD_ICON_APPEARANCE: [
                    "user",
                    b"\xff\xff\xff",
                    b"\x00\x00\x00",
                ],
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    icon = _b64_field(inbox, LXMF.FIELD_ICON_APPEARANCE)
    assert icon is not None
    assert icon[0] == "user"
    assert base64.b64decode(icon[1]["__b64__"]) == b"\xff\xff\xff"

    app = prepare_messaging_app(mock_app)
    app.update_lxmf_user_icon = MagicMock()
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    _delivery_from_local(app, inbox)
    app.update_lxmf_user_icon.assert_called_once()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_reaction_delivery(tmp_path, mock_app):
    target = os.urandom(32)
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "",
            "title": "",
            "fields": {
                FIELD_REACTION: {
                    REACTION_TO: target,
                    REACTION_CONTENT: b"+1",
                },
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    reaction = _b64_field(inbox, FIELD_REACTION)
    assert reaction is not None
    assert base64.b64decode(reaction[str(REACTION_TO)]["__b64__"]) == target
    assert base64.b64decode(reaction[str(REACTION_CONTENT)]["__b64__"]) == b"+1"

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    converted = convert_lxmf_message_to_dict(msg, include_attachments=False)
    assert converted["fields"]["reaction"]["reaction_to"] == target.hex()
    assert converted["fields"]["reaction"]["reaction_content"] == "+1"


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_stores_in_meshchatx(tmp_path, mock_app):
    result = _run_local_delivery(
        tmp_path,
        payload={"content": "persist me", "title": "store", "fields": {}},
    )
    inbox = result["inbox"]
    assert inbox["sig_ok"] is True

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    assert row["content"] == "persist me"
    assert row["title"] == "store"


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_spam_attachment_dropped_by_meshchatx(tmp_path, mock_app):
    secret = b"LOCAL_TCP_SPAM_SECRET_55"
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "buy VIAGRA now",
            "title": "deal",
            "fields": {LXMF.FIELD_IMAGE: ["png", b"\x89PNG" + secret]},
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    assert inbox["sig_ok"] is True

    app = prepare_messaging_app(mock_app)
    app.database.misc.add_spam_keyword("viagra")
    app.database.contacts.add_contact(
        "LiveFriend",
        inbox["src"],
        lxmf_address=inbox["src"],
    )
    msg = _delivery_from_local(app, inbox)
    assert stored_message(app, msg) is None


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_blocked_peer_dropped_by_meshchatx(tmp_path, mock_app):
    result = _run_local_delivery(
        tmp_path,
        payload={"content": "should be blocked", "title": "nope", "fields": {}},
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True

    app = prepare_messaging_app(mock_app)
    app.database.misc.add_blocked_destination(inbox["src"])
    msg = _delivery_from_local(app, inbox)
    assert stored_message(app, msg) is None


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_local_tcp_codec2_voice_and_telemetry_together(tmp_path, mock_app):
    """Combined payload: codec2 voice note + packed telemetry over one hop."""
    voice = b"LOCAL_TCP_C2_VOICE_17"
    ts = int(time.time())
    packed = Telemeter.pack(
        time_utc=ts,
        location={"latitude": 1.0, "longitude": 2.0, "last_update": ts},
    )
    result = _run_local_delivery(
        tmp_path,
        payload={
            "content": "status",
            "title": "combo",
            "fields": {
                LXMF.FIELD_AUDIO: [LXMF.AM_CODEC2_1200, voice],
                LXMF.FIELD_TELEMETRY: packed,
            },
        },
    )
    inbox = result["inbox"]
    assert inbox["ok"] is True
    audio = _b64_field(inbox, LXMF.FIELD_AUDIO)
    assert audio[0] == LXMF.AM_CODEC2_1200
    assert base64.b64decode(audio[1]["__b64__"]) == voice

    app = prepare_messaging_app(mock_app)
    app.database.contacts.add_contact("Alice", inbox["src"], lxmf_address=inbox["src"])
    msg = _delivery_from_local(app, inbox)
    row = stored_message(app, msg)
    assert row is not None
    fields = json.loads(row["fields"] or "{}")
    assert fields["audio"]["audio_mode"] == LXMF.AM_CODEC2_1200
    telem = app.database.telemetry.get_latest_telemetry(inbox["src"])
    assert telem is not None
    assert bytes(telem["data"]) == packed
