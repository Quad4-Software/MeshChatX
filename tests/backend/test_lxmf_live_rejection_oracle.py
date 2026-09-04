# SPDX-License-Identifier: 0BSD

"""Live LXMF pack/unpack + MeshChatX on_lxmf_delivery rejection oracles.

Packs real LXMF bytes in an isolated Reticulum subprocess (same gate as
test_lxmf_tools_live.py), then unpacks in the parent and feeds
on_lxmf_delivery against SQLite via lxmf_tools_support.

Enable with MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import textwrap

import LXMF
import pytest

from meshchatx.src.backend.lxmf_utils import convert_lxmf_message_to_dict
from meshchatx.src.backend.sideband_commands import SidebandCommands
from tests.backend.lxmf_tools_support import (
    LOCAL_LXMF,
    PEER_SPAMMER,
    make_inbound_lxmf,
    prepare_messaging_app,
    stored_message,
)

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

_MINIMAL_RNS_CONFIG = """\
[reticulum]
  enable_transport = False
  share_instance = No
  panic_on_interface_error = No

[interfaces]
"""

_SUBPROCESS_PREAMBLE = textwrap.dedent(f"""\
import tempfile, os, json, base64, time
import RNS, LXMF

_tmpdir = tempfile.mkdtemp(prefix="meshchat_lxmf_live_reject_")
_config_path = os.path.join(_tmpdir, "config")
with open(_config_path, "w") as f:
    f.write({_MINIMAL_RNS_CONFIG!r})

_reticulum = RNS.Reticulum(configdir=_tmpdir, loglevel=RNS.LOG_NONE)

def _emit(data):
    print(json.dumps(data), flush=True)

def _cleanup():
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass

def _pack(content, title="", fields=None, tamper=False):
    sender_id = RNS.Identity()
    receiver_id = RNS.Identity()
    sender_dest = RNS.Destination(
        sender_id, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery",
    )
    receiver_dest = RNS.Destination(
        receiver_id, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery",
    )
    msg = LXMF.LXMessage(
        receiver_dest, sender_dest,
        content=content,
        title=title,
        fields=fields or {{}},
        desired_method=LXMF.LXMessage.DIRECT,
    )
    msg.pack()
    packed = bytearray(msg.packed)
    if tamper and len(packed) > 40:
        packed[-5] ^= 0xFF
    unpacked = LXMF.LXMessage.unpack_from_bytes(bytes(packed))
    return msg, unpacked, sender_id, receiver_id
""")


def _run_lxmf_script(script_body, timeout=90):
    return subprocess.run(
        [sys.executable, "-c", script_body],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _parse_result(proc):
    assert proc.returncode == 0, f"Script failed:\n{proc.stderr}\n{proc.stdout}"
    lines = proc.stdout.strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"No JSON in output:\n{proc.stdout}")


def _delivery_from_live(app, live: dict, *, source_override: str | None = None):
    """Rebuild an inbound LXMF-shaped object from live pack/unpack JSON."""
    fields = {}
    for key, value in (live.get("fields") or {}).items():
        ikey = int(key)
        if isinstance(value, dict) and value.get("__b64__"):
            fields[ikey] = base64.b64decode(value["__b64__"])
        elif isinstance(value, list):
            rebuilt = []
            for item in value:
                if isinstance(item, dict) and item.get("__b64__"):
                    rebuilt.append(base64.b64decode(item["__b64__"]))
                elif isinstance(item, list) and len(item) >= 2:
                    name = item[0]
                    data = item[1]
                    if isinstance(data, dict) and data.get("__b64__"):
                        data = base64.b64decode(data["__b64__"])
                    rebuilt.append([name, data])
                else:
                    rebuilt.append(item)
            fields[ikey] = rebuilt
        else:
            fields[ikey] = value

    source = source_override or live["src"]
    dest = live.get("dst") or LOCAL_LXMF
    msg = make_inbound_lxmf(
        source_hash=source,
        destination_hash=dest if len(dest) == 32 else LOCAL_LXMF,
        content=live.get("content") or "",
        title=live.get("title") or "",
        fields=fields,
        msg_hash=bytes.fromhex(live["hash"]) if live.get("hash") else None,
    )
    msg.signature_validated = bool(live.get("sig_ok"))
    if live.get("unverified_reason") is not None:
        msg.unverified_reason = live["unverified_reason"]
    app.on_lxmf_delivery(msg)
    return msg


def _encode_fields_for_json(fields: dict) -> dict:
    """Helper used only in docstring examples; live scripts encode inline."""
    out = {}
    for k, v in fields.items():
        if isinstance(v, (bytes, bytearray)):
            out[str(k)] = {"__b64__": base64.b64encode(v).decode()}
        else:
            out[str(k)] = v
    return out


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_signature_validated_roundtrip():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        msg, unpacked, sender, receiver = _pack("live hello", title="t1")
        _emit({
            "content": unpacked.content_as_string(),
            "title": unpacked.title_as_string(),
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "hash": unpacked.hash.hex(),
            "sig_ok": bool(unpacked.signature_validated),
            "unverified_reason": unpacked.unverified_reason,
            "fields": {},
        })
    finally:
        _cleanup()
    """)
    data = _parse_result(_run_lxmf_script(script))
    assert data["sig_ok"] is True
    assert data["content"] == "live hello"
    assert data["unverified_reason"] is None


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_tampered_pack_marks_signature_invalid():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        msg, unpacked, sender, receiver = _pack("tamper me", tamper=True)
        _emit({
            "sig_ok": bool(unpacked.signature_validated),
            "unverified_reason": unpacked.unverified_reason,
            "reason_invalid": unpacked.unverified_reason == LXMF.LXMessage.SIGNATURE_INVALID,
        })
    finally:
        _cleanup()
    """)
    data = _parse_result(_run_lxmf_script(script))
    assert data["sig_ok"] is False
    assert data["reason_invalid"] is True


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_spam_attachment_drop_through_delivery(mock_app):
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        secret = b"LIVE_REJECT_SECRET_41"
        fields = {LXMF.FIELD_IMAGE: ["png", b"\\x89PNG" + secret]}
        msg, unpacked, sender, receiver = _pack(
            "buy VIAGRA now", title="deal", fields=fields,
        )
        raw_fields = unpacked.get_fields()
        enc = {}
        for k, v in raw_fields.items():
            if k == LXMF.FIELD_IMAGE:
                enc[str(k)] = [v[0], {"__b64__": base64.b64encode(v[1]).decode()}]
            else:
                enc[str(k)] = v
        _emit({
            "content": unpacked.content_as_string(),
            "title": unpacked.title_as_string(),
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "hash": unpacked.hash.hex(),
            "sig_ok": bool(unpacked.signature_validated),
            "fields": enc,
        })
    finally:
        _cleanup()
    """)
    live = _parse_result(_run_lxmf_script(script))
    assert live["sig_ok"] is True

    app = prepare_messaging_app(mock_app)
    app.database.misc.add_spam_keyword("viagra")
    # Force contact so stranger drop does not apply; spam+attachment should drop.
    app.database.contacts.add_contact(
        "LiveFriend",
        live["src"],
        lxmf_address=live["src"],
    )
    msg = _delivery_from_live(app, live)
    assert stored_message(app, msg) is None


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_telemetry_request_still_strips_stranger_attachments(mock_app):
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent(f"""\
    try:
        secret = b"LIVE_TELEM_STRIP_SECRET_77"
        fields = {{
            0x01: [{{ {SidebandCommands.TELEMETRY_REQUEST}: int(time.time()) }}],
            LXMF.FIELD_IMAGE: ["png", b"\\x89PNG" + secret],
        }}
        msg, unpacked, sender, receiver = _pack("ping", fields=fields)
        raw_fields = unpacked.get_fields()
        enc = {{}}
        for k, v in raw_fields.items():
            if k == LXMF.FIELD_IMAGE:
                enc[str(k)] = [v[0], {{"__b64__": base64.b64encode(v[1]).decode()}}]
            elif k == 0x01:
                enc[str(k)] = v
            else:
                enc[str(k)] = v
        _emit({{
            "content": unpacked.content_as_string(),
            "title": unpacked.title_as_string() or "",
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "hash": unpacked.hash.hex(),
            "sig_ok": bool(unpacked.signature_validated),
            "fields": enc,
        }})
    finally:
        _cleanup()
    """)
    live = _parse_result(_run_lxmf_script(script))
    app = prepare_messaging_app(mock_app)
    app.config.block_attachments_from_strangers.set(True)
    msg = _delivery_from_live(app, live, source_override=PEER_SPAMMER)
    row = stored_message(app, msg)
    assert row is not None
    assert int(row["attachments_stripped"] or 0) == 1
    assert LXMF.FIELD_IMAGE not in msg.get_fields()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_embedded_lxms_not_converted_as_commands():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        inner_sender = RNS.Identity()
        inner_receiver = RNS.Identity()
        inner_src = RNS.Destination(
            inner_sender, RNS.Destination.IN, RNS.Destination.SINGLE, "lxmf", "delivery",
        )
        inner_dst = RNS.Destination(
            inner_receiver, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery",
        )
        inner = LXMF.LXMessage(
            inner_dst, inner_src, content="nested", desired_method=LXMF.LXMessage.DIRECT,
        )
        inner.pack()
        msg, unpacked, sender, receiver = _pack(
            "wrapper",
            fields={LXMF.FIELD_EMBEDDED_LXMS: [inner.packed]},
        )
        raw = unpacked.get_fields().get(LXMF.FIELD_EMBEDDED_LXMS)
        enc = {
            str(LXMF.FIELD_EMBEDDED_LXMS): [
                {"__b64__": base64.b64encode(raw[0]).decode()},
            ],
        }
        _emit({
            "content": unpacked.content_as_string(),
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "hash": unpacked.hash.hex(),
            "sig_ok": bool(unpacked.signature_validated),
            "fields": enc,
            "embedded_len": len(raw[0]),
        })
    finally:
        _cleanup()
    """)
    live = _parse_result(_run_lxmf_script(script))
    assert live["sig_ok"] is True
    assert live["embedded_len"] > 0

    fields = {}
    for key, value in live["fields"].items():
        rebuilt = []
        for item in value:
            rebuilt.append(base64.b64decode(item["__b64__"]))
        fields[int(key)] = rebuilt
    msg = make_inbound_lxmf(
        source_hash=live["src"],
        destination_hash=LOCAL_LXMF,
        content=live["content"],
        fields=fields,
    )
    out = convert_lxmf_message_to_dict(msg, include_attachments=False)
    assert "commands" not in out["fields"]
    assert out["fields"]["embedded_lxms"] == [{"size": live["embedded_len"]}]


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_signature_invalid_never_upserts(mock_app):
    # Build a signed message then force SIGNATURE_INVALID on the delivery object.
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        msg, unpacked, sender, receiver = _pack("should drop")
        _emit({
            "content": unpacked.content_as_string(),
            "title": "",
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "hash": unpacked.hash.hex(),
            "sig_ok": True,
            "fields": {},
            "force_invalid": LXMF.LXMessage.SIGNATURE_INVALID,
        })
    finally:
        _cleanup()
    """)
    live = _parse_result(_run_lxmf_script(script))
    app = prepare_messaging_app(mock_app)
    live["sig_ok"] = False
    live["unverified_reason"] = live["force_invalid"]
    msg = _delivery_from_live(app, live)
    assert stored_message(app, msg) is None
