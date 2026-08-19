# SPDX-License-Identifier: 0BSD

"""Live LXMF pack/unpack oracles for sieve matching, alias identities, and paper URIs.

Pack and unpack require an isolated Reticulum instance. Enable with
MESHCHAT_LIVE_RETICULUM=1 (same gate as test_lxmf_communication.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import pytest

from meshchatx.src.backend.lxmf_sieve import (
    first_matching_lxmf_sieve_rule,
    normalize_lxmf_sieve_filters,
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
import tempfile, os, json, base64
import RNS, LXMF

_tmpdir = tempfile.mkdtemp(prefix="meshchat_lxmf_tools_")
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


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_packed_lxmf_content_matches_sieve_oracle():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
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
            content="please ignore this SPAM offer",
            title="mesh mail",
            desired_method=LXMF.LXMessage.DIRECT,
        )
        msg.pack()
        unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
        _emit({
            "content": unpacked.content_as_string(),
            "title": unpacked.title_as_string(),
            "src": unpacked.source_hash.hex(),
            "dst": unpacked.destination_hash.hex(),
            "sig_ok": bool(unpacked.signature_validated),
            "hash_match": unpacked.hash == msg.hash,
        })
    finally:
        _cleanup()
    """)
    data = _parse_result(_run_lxmf_script(script))
    assert data["sig_ok"] is True
    assert data["hash_match"] is True
    haystack = f"{data['title']} {data['content']}".strip()
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "ignore",
                "terms": ["spam"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    got = first_matching_lxmf_sieve_rule(
        rules,
        data["src"],
        message_haystack=haystack,
    )
    assert got is not None
    assert got["action"] == "ignore"


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_forwarding_alias_identity_roundtrip():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
        alias = RNS.Identity()
        priv = alias.get_private_key()
        restored = RNS.Identity.from_bytes(priv)
        dest = RNS.Destination.hash(alias, "lxmf", "delivery")
        dest2 = RNS.Destination.hash(restored, "lxmf", "delivery")
        _emit({
            "hash_match": alias.hash == restored.hash,
            "dest_match": dest == dest2,
            "hash_len": len(alias.hash),
            "priv_b64": base64.b64encode(priv).decode(),
        })
    finally:
        _cleanup()
    """)
    data = _parse_result(_run_lxmf_script(script))
    assert data["hash_match"] is True
    assert data["dest_match"] is True
    assert data["hash_len"] == 16
    restored = __import__("base64").b64decode(data["priv_b64"])
    assert len(restored) > 0


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_paper_uri_roundtrip_ingest_bytes():
    script = _SUBPROCESS_PREAMBLE + textwrap.dedent("""\
    try:
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
            content="paper sieve token UNIQUEPAPER42",
            desired_method=LXMF.LXMessage.PAPER,
        )
        msg.pack()
        uri = msg.as_uri()
        unpacked = LXMF.LXMessage.unpack_from_bytes(msg.packed)
        _emit({
            "uri_ok": uri.startswith("lxm://"),
            "content": unpacked.content_as_string(),
            "method_paper": msg.method == LXMF.LXMessage.PAPER,
        })
    finally:
        _cleanup()
    """)
    data = _parse_result(_run_lxmf_script(script))
    assert data["uri_ok"] is True
    assert data["method_paper"] is True
    rules = normalize_lxmf_sieve_filters(
        [
            {
                "action": "hide",
                "terms": ["uniquepaper42"],
                "match_peer_fields": False,
                "match_message": True,
            },
        ],
    )
    got = first_matching_lxmf_sieve_rule(
        rules,
        "paper-peer",
        message_haystack=data["content"],
    )
    assert got is not None
    assert got["action"] == "hide"
