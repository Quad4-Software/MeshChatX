# SPDX-License-Identifier: 0BSD

"""Live three-peer LXMF propagation-node delivery over loopback TCP.

Spins up a full-mesh trio on 127.0.0.1: a propagation node (pn), a sender
(alice) and a recipient (bob). Alice sends an LXMessage with method
PROPAGATED through the propagation node's mailbox; bob receives it after
the node peers with him and syncs. Exercises real LXMF 1.3.0 peering,
mailbox storage and sync against RNS 1.6.0 transport.

Enable with MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

_PROP_TIMEOUT_S = int(os.environ.get("MESHCHAT_LIVE_PROP_TIMEOUT", "180"))

# LXMessage.PROPAGATED == 0x03 (LXMF/LXMessage.py). Duplicated so this module
# stays importable without LXMF at collection time.
LXMF_METHOD_PROPAGATED = 0x03

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
    """,
)

# Each node gets its own TCPServerInterface plus TCPClientInterfaces to the
# other two, so every pair has a direct path and announces propagate
# trivially. shared_instance_port offsets keep the three instances apart.
_PN_SCRIPT = _FIELD_CODEC + textwrap.dedent(
    """\
    import json
    import os
    import sys
    import time

    import LXMF
    import RNS

    config_dir, share_dir, timeout_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
    stop_path = os.path.join(share_dir, "stop")
    ready_path = os.path.join(share_dir, "pn_ready.json")
    store_path = os.path.join(share_dir, "pn_store.json")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    router.PROCESSING_INTERVAL = 1
    router.enable_propagation()

    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "prop_dest": router.propagation_destination.hash.hex(),
                "pub": identity.get_public_key().hex(),
            },
            handle,
        )

    deadline = time.time() + timeout_s + 60
    announced = 0.0
    while time.time() < deadline and not os.path.isfile(stop_path):
        router.propagation_destination.announce(
            app_data=router.get_propagation_node_app_data()
        )
        announced += 1
        # Report mailbox contents so the parent can verify store-then-sync.
        entries = getattr(router, "propagation_entries", {}) or {}
        if entries and not os.path.isfile(store_path):
            with open(store_path, "w", encoding="utf-8") as handle:
                json.dump({"count": len(entries)}, handle)
        time.sleep(2)
    RNS.exit(0)
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
    ready_path = os.path.join(share_dir, "bob_ready.json")
    pn_ready = os.path.join(share_dir, "pn_ready.json")
    inbox_path = os.path.join(share_dir, "inbox.json")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    router.PROCESSING_INTERVAL = 1
    dest = router.register_delivery_identity(identity, display_name="bob")

    # Regular peers pull from propagation nodes; peering is PN-to-PN only.
    # Point bob at the node and poll for mailbox messages, the same way
    # MeshChatX's sync_propagation_nodes drives request_messages_from_propagation_node.
    pn_prop_hash = None
    deadline = time.time() + 60
    while time.time() < deadline and not os.path.isfile(pn_ready):
        time.sleep(0.2)
    if os.path.isfile(pn_ready):
        with open(pn_ready, encoding="utf-8") as handle:
            pn_prop_hash = bytes.fromhex(json.load(handle)["prop_dest"])
        router.set_outbound_propagation_node(pn_prop_hash)

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
                    "method": int(getattr(message, "method", -1)),
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

    deadline = time.time() + timeout_s + 60
    last_sync = 0.0
    while time.time() < deadline and not os.path.isfile(stop_path):
        dest.announce()
        if pn_prop_hash is not None and time.time() - last_sync > 8:
            last_sync = time.time()
            try:
                router.request_messages_from_propagation_node(identity)
            except Exception:
                pass
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
    pn_ready = os.path.join(share_dir, "pn_ready.json")
    bob_ready = os.path.join(share_dir, "bob_ready.json")
    result_path = os.path.join(share_dir, "send.json")

    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    router.PROCESSING_INTERVAL = 1
    local = router.register_delivery_identity(identity, display_name="alice")

    deadline = time.time() + 60
    while time.time() < deadline and not (
        os.path.isfile(pn_ready) and os.path.isfile(bob_ready)
    ):
        time.sleep(0.2)
    if not (os.path.isfile(pn_ready) and os.path.isfile(bob_ready)):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_ready"}, handle)
        RNS.exit(1)

    with open(pn_ready, encoding="utf-8") as handle:
        pn = json.load(handle)
    with open(bob_ready, encoding="utf-8") as handle:
        bob = json.load(handle)

    # Route outbound PROPAGATED traffic through the propagation node.
    router.set_outbound_propagation_node(bytes.fromhex(pn["prop_dest"]))

    pn_prop_hash = bytes.fromhex(pn["prop_dest"])
    bob_delivery_hash = bytes.fromhex(bob["dest"])

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        local.announce()
        ready = RNS.Transport.has_path(pn_prop_hash) and RNS.Transport.has_path(
            bob_delivery_hash
        )
        if ready:
            break
        RNS.Transport.request_path(pn_prop_hash)
        RNS.Transport.request_path(bob_delivery_hash)
        time.sleep(1)
    if not (
        RNS.Transport.has_path(pn_prop_hash)
        and RNS.Transport.has_path(bob_delivery_hash)
    ):
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump({"ok": False, "reason": "no_path"}, handle)
        RNS.exit(1)

    bob_identity = RNS.Identity(create_keys=False)
    bob_identity.load_public_key(bytes.fromhex(bob["pub"]))
    destination = RNS.Destination(
        bob_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery",
    )

    msg = LXMF.LXMessage(
        destination,
        local,
        content="hello via propagation node",
        title="prop-test",
        fields={},
        desired_method=LXMF.LXMessage.PROPAGATED,
    )
    router.handle_outbound(msg)

    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "ok": True,
                "state": int(msg.state) if msg.state is not None else None,
                "msg_hash": msg.hash.hex() if msg.hash else None,
                "pn": pn["prop_dest"],
                "bob": bob["dest"],
            },
            handle,
        )

    # Keep the router alive so the outbound sync can complete.
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(1)
    RNS.exit(0)
    """,
)


def _free_ports(count: int) -> list[int]:
    ports = []
    while len(ports) < count:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
        sock.close()
        if port not in ports:
            ports.append(port)
    return ports


def _node_config(
    name: str, own_port: int, peer_ports: list[int], shared_port: int
) -> str:
    lines = [
        "[reticulum]",
        "enable_transport = Yes",
        "share_instance = No",
        f"shared_instance_port = {shared_port}",
        f"instance_name = lxmf_prop_{name}_{own_port}",
        "panic_on_interface_error = No",
        "",
        "[logging]",
        "loglevel = 3",
        "",
        "[interfaces]",
        "  [[TCP Server]]",
        "    type = TCPServerInterface",
        "    enabled = Yes",
        "    listen_ip = 127.0.0.1",
        f"    listen_port = {own_port}",
    ]
    for idx, peer_port in enumerate(peer_ports, start=1):
        lines += [
            f"  [[TCP Client {idx}]]",
            "    type = TCPClientInterface",
            "    enabled = Yes",
            "    target_host = 127.0.0.1",
            f"    target_port = {peer_port}",
        ]
    return "\n".join(lines) + "\n"


def _spawn(
    script: str, config_dir: Path, share_dir: Path, timeout_s: float
) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", script, str(config_dir), str(share_dir), str(timeout_s)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=subprocess_test_env(),
    )


def _stop_all(procs: list[subprocess.Popen], share_dir: Path) -> None:
    try:
        (share_dir / "stop").write_text("1", encoding="utf-8")
    except OSError:
        pass
    for proc in procs:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1")
def test_live_lxmf_propagation_node_delivery(tmp_path):
    share_dir = tmp_path / "share"
    share_dir.mkdir(parents=True, exist_ok=True)
    pn_dir = tmp_path / "pn"
    alice_dir = tmp_path / "alice"
    bob_dir = tmp_path / "bob"
    for d in (pn_dir, alice_dir, bob_dir):
        d.mkdir(parents=True, exist_ok=True)

    pn_port, alice_port, bob_port = _free_ports(3)
    (pn_dir / "config").write_text(
        _node_config("pn", pn_port, [alice_port, bob_port], 41000 + pn_port % 500),
        encoding="utf-8",
    )
    (alice_dir / "config").write_text(
        _node_config(
            "alice", alice_port, [pn_port, bob_port], 42000 + alice_port % 500
        ),
        encoding="utf-8",
    )
    (bob_dir / "config").write_text(
        _node_config("bob", bob_port, [pn_port, alice_port], 43000 + bob_port % 500),
        encoding="utf-8",
    )

    procs = [
        _spawn(_PN_SCRIPT, pn_dir, share_dir, _PROP_TIMEOUT_S),
        _spawn(_BOB_SCRIPT, bob_dir, share_dir, _PROP_TIMEOUT_S),
        _spawn(_ALICE_SCRIPT, alice_dir, share_dir, _PROP_TIMEOUT_S),
    ]
    try:
        inbox = share_dir / "inbox.json"
        send_result = share_dir / "send.json"
        deadline = time.time() + _PROP_TIMEOUT_S
        while time.time() < deadline and not inbox.is_file():
            for proc in procs:
                if proc.poll() is not None and not inbox.is_file():
                    # Alice exiting early is fatal; pn/bob may still be
                    # waiting on the stop file after delivering.
                    if proc is procs[2]:
                        out, err = proc.communicate(timeout=5)
                        send_body = (
                            send_result.read_text(encoding="utf-8")
                            if send_result.is_file()
                            else ""
                        )
                        raise AssertionError(
                            f"alice exited {proc.returncode} without delivery: "
                            f"{err}\n{out}\n{send_body}",
                        )
            time.sleep(0.5)

        assert inbox.is_file(), "bob never received the propagated message"
        payload = json.loads(inbox.read_text(encoding="utf-8"))
        assert payload["ok"] is True
        assert payload["content"] == "hello via propagation node"
        assert payload["sig_ok"] is True
        assert payload["method"] == LXMF_METHOD_PROPAGATED

        if send_result.is_file():
            send = json.loads(send_result.read_text(encoding="utf-8"))
            assert send["ok"] is True
    finally:
        _stop_all(procs, share_dir)
