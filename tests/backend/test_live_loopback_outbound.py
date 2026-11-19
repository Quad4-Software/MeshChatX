# SPDX-License-Identifier: 0BSD

"""Loopback live e2e: two real RNS instances on 127.0.0.1.

Alice runs in this pytest process so every RNS.Transport.request_path call is
counted directly. Bob runs as a subprocess with a TCPServerInterface, an LXMF
delivery destination, and a nomadnetwork.node destination that serves a page
and a file over RNS link requests.

Enable with MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import textwrap
import time
from unittest.mock import patch

import pytest

from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1"),
]

_BOB_SCRIPT = textwrap.dedent(
    """\
    import json
    import os
    import sys
    import time

    import LXMF
    import RNS

    config_dir, share_dir = sys.argv[1], sys.argv[2]
    ready_path = os.path.join(share_dir, "ready.json")
    stop_path = os.path.join(share_dir, "stop")
    announce_path = os.path.join(share_dir, "announce")
    inbox_path = os.path.join(share_dir, "inbox.json")

    # Live tests skip PoW stamps on announce/path requests (RNS 1.6.1 enables
    # them by default; 1.6.0 had them off and CI runners are slow).
    RNS.Transport.STAMP_DESTINATIONS = False
    RNS.Transport.STAMP_PRS = False
    RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)

    # LXMF delivery endpoint
    identity = RNS.Identity()
    storage = os.path.join(config_dir, "lxmf_storage")
    os.makedirs(storage, exist_ok=True)
    router = LXMF.LXMRouter(storagepath=storage)
    lxmf_dest = router.register_delivery_identity(identity, display_name="bob")

    def on_delivery(message):
        with open(inbox_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "ok": True,
                    "content": message.content_as_string(),
                    "title": message.title_as_string(),
                },
                handle,
            )

    router.register_delivery_callback(on_delivery)

    # nomadnetwork.node endpoint serving one page and one file
    node_identity = RNS.Identity()
    node_dest = RNS.Destination(
        node_identity, RNS.Destination.IN, RNS.Destination.SINGLE,
        "nomadnetwork", "node",
    )

    PAGE_BODY = b"[`c`f4`b0 Hello from Bob's node `a]"
    FILE_BODY = b"loopback-file-payload-0123456789"

    def page_response(path, data, request_id, remote_identity, requested_at):
        return PAGE_BODY

    def file_response(path, data, request_id, remote_identity, requested_at):
        return [b"blob.bin", FILE_BODY]

    node_dest.register_request_handler(
        "/page/index.mu", response_generator=page_response,
        allow=RNS.Destination.ALLOW_ALL,
    )
    node_dest.register_request_handler(
        "/file/blob.bin", response_generator=file_response,
        allow=RNS.Destination.ALLOW_ALL,
    )

    with open(ready_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "lxmf_dest": lxmf_dest.hash.hex(),
                "lxmf_pub": identity.get_public_key().hex(),
                "node_dest": node_dest.hash.hex(),
            },
            handle,
        )

    announced = False
    deadline = time.time() + 600
    while time.time() < deadline and not os.path.isfile(stop_path):
        if os.path.isfile(announce_path) and not announced:
            lxmf_dest.announce()
            node_dest.announce()
            announced = True
        time.sleep(0.2)
    RNS.exit(0)
    """,
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _write_config(
    config_dir, port: int, role: str, listen_port: int | None = None
) -> None:
    os.makedirs(config_dir, exist_ok=True)
    if role == "client":
        iface = (
            f"  [[Loopback]]\n"
            f"    type = TCPClientInterface\n"
            f"    enabled = yes\n"
            f"    target_host = 127.0.0.1\n"
            f"    target_port = {port}\n"
        )
    else:
        iface = (
            f"  [[Loopback]]\n"
            f"    type = TCPServerInterface\n"
            f"    enabled = yes\n"
            f"    listen_ip = 127.0.0.1\n"
            f"    listen_port = {listen_port}\n"
        )
    with open(os.path.join(config_dir, "config"), "w", encoding="utf-8") as handle:
        handle.write(
            "[reticulum]\n"
            "  enable_transport = no\n"
            "  share_instance = no\n"
            "  auto_introspect = False\n"
            "[interfaces]\n" + iface
        )


@pytest.fixture(scope="module")
def loopback_pair(tmp_path_factory, loopback_available):
    if not loopback_available:
        pytest.skip("Loopback TCP is blocked by local firewall/policy.")
    import RNS

    tmp_path = tmp_path_factory.mktemp("loopback_pair")
    port = _free_port()
    share_dir = tmp_path / "share"
    share_dir.mkdir()

    bob_dir = tmp_path / "bob"
    _write_config(bob_dir, port, "server", listen_port=port)
    env = subprocess_test_env({"MESHCHAT_LIVE_PEER_DIR": str(share_dir)})
    bob = subprocess.Popen(
        [sys.executable, "-c", _BOB_SCRIPT, str(bob_dir), str(share_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    ready = share_dir / "ready.json"
    deadline = time.time() + 30
    while time.time() < deadline and not ready.is_file():
        if bob.poll() is not None:
            out, err = bob.communicate(timeout=5)
            raise AssertionError(f"bob exited {bob.returncode}: {err}\n{out}")
        time.sleep(0.1)
    assert ready.is_file(), "bob did not come up"

    alice_dir = tmp_path / "alice"
    _write_config(alice_dir, port, "client")
    reticulum = RNS.Reticulum(configdir=str(alice_dir), loglevel=RNS.LOG_ERROR)

    # RNS 1.6.1 stamp jobs retry outstanding path requests internally with
    # kwargs (on_interface/tag/recursive/ext_payload). The app calls
    # request_path(destination_hash) with no kwargs, so the two are easy to
    # tell apart. Count both; assertions use the app-initiated number.
    request_path_calls = {"app": 0, "internal": 0}
    original_request_path = RNS.Transport.request_path

    def counting_request_path(dest_hash, **kwargs):
        if kwargs:
            request_path_calls["internal"] += 1
        else:
            request_path_calls["app"] += 1
        return original_request_path(dest_hash, **kwargs)

    identity = RNS.Identity()

    yield {
        "bob": bob,
        "share": share_dir,
        "ready": json.loads(ready.read_text()),
        "identity": identity,
        "reticulum": reticulum,
        "request_path_calls": request_path_calls,
        "patch": lambda: patch.object(
            RNS.Transport, "request_path", counting_request_path
        ),
    }

    (share_dir / "stop").touch()
    # RNS.exit() calls os._exit, which would kill the pytest process.
    # Run the exit handler directly so interfaces/threads shut down cleanly.
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass
    try:
        bob.wait(timeout=15)
    except subprocess.TimeoutExpired:
        bob.kill()
        bob.wait(timeout=5)


def test_lxmf_delivery_without_announce_requests_path_once(loopback_pair):
    """No announce yet: path request goes out once and Bob answers."""
    import RNS

    from meshchatx.src.backend import reticulum_pathfinding

    bob_dest = bytes.fromhex(loopback_pair["ready"]["lxmf_dest"])
    assert not RNS.Transport.has_path(bob_dest)

    with loopback_pair["patch"]():
        measure = reticulum_pathfinding.prepare_fresh_path_request(
            loopback_pair["reticulum"], bob_dest
        )
        deadline = time.time() + 30
        while not RNS.Transport.has_path(bob_dest) and time.time() < deadline:
            reticulum_pathfinding.nudge_path_request(bob_dest)
            time.sleep(0.5)
    assert RNS.Transport.has_path(bob_dest), "no path after single request"
    # one request sufficed; the dedup window stopped nudges from spamming
    assert loopback_pair["request_path_calls"]["app"] <= 2
    assert measure == "new_path_requested"


def test_lxmf_delivery_after_announce_sends_no_path_request(loopback_pair):
    """Bob announces first: Alice has the path and requests nothing."""
    import LXMF
    import RNS

    bob_dest = bytes.fromhex(loopback_pair["ready"]["lxmf_dest"])
    (loopback_pair["share"] / "announce").touch()
    deadline = time.time() + 30
    while not RNS.Transport.has_path(bob_dest) and time.time() < deadline:
        time.sleep(0.2)
    assert RNS.Transport.has_path(bob_dest), "announce never arrived"

    loopback_pair["request_path_calls"]["app"] = 0
    loopback_pair["request_path_calls"]["internal"] = 0
    with loopback_pair["patch"]():
        # Direct send path: local router handles outbound over the live link.
        local = RNS.Identity()
        storage = loopback_pair["share"] / "alice_lxmf"
        storage.mkdir()
        router = LXMF.LXMRouter(storagepath=str(storage))
        own_dest = router.register_delivery_identity(local, display_name="alice")
        bob_ident = RNS.Identity.recall(bob_dest)
        assert bob_ident is not None
        out_dest = RNS.Destination(
            bob_ident,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )
        msg = LXMF.LXMessage(
            out_dest,
            own_dest,
            content="after announce",
            title="t",
            desired_method=LXMF.LXMessage.DIRECT,
        )
        router.handle_outbound(msg)
        deadline = time.time() + 30
        inbox = loopback_pair["share"] / "inbox.json"
        while not inbox.is_file() and time.time() < deadline:
            time.sleep(0.3)
        assert inbox.is_file(), "LXMF was not delivered"
        assert loopback_pair["request_path_calls"]["app"] == 0


def test_nomadnet_page_and_file_request_loopback(loopback_pair):
    """Real page + file fetch over an RNS link through the app downloaders."""
    import RNS

    from meshchatx.src.backend.nomadnet_downloader import (
        NomadnetFileDownloader,
        NomadnetPageDownloader,
    )

    node_dest = bytes.fromhex(loopback_pair["ready"]["node_dest"])
    (loopback_pair["share"] / "announce").touch()
    deadline = time.time() + 30
    while not RNS.Transport.has_path(node_dest) and time.time() < deadline:
        time.sleep(0.2)
    assert RNS.Transport.has_path(node_dest), "node announce never arrived"

    outcomes = {}

    page_dl = NomadnetPageDownloader(
        node_dest,
        "/page/index.mu",
        None,
        lambda text: outcomes.setdefault("page_ok", text),
        lambda reason: outcomes.setdefault("page_err", reason),
        lambda p: None,
        private=True,
    )
    loopback_pair["request_path_calls"]["app"] = 0
    loopback_pair["request_path_calls"]["internal"] = 0
    with loopback_pair["patch"]():
        asyncio.run(
            page_dl.download(path_lookup_timeout=30, link_establishment_timeout=30)
        )
    assert "page_ok" in outcomes, outcomes.get("page_err")
    assert "Hello from Bob's node" in outcomes["page_ok"]
    # announce already delivered the path: no app request_path needed
    assert loopback_pair["request_path_calls"]["app"] == 0

    file_dl = NomadnetFileDownloader(
        node_dest,
        "/file/blob.bin",
        lambda name, data: outcomes.setdefault("file_ok", (name, data)),
        lambda reason: outcomes.setdefault("file_err", reason),
        lambda p: None,
        private=True,
    )
    asyncio.run(file_dl.download(path_lookup_timeout=30, link_establishment_timeout=30))
    assert "file_ok" in outcomes, outcomes.get("file_err")
    name, data = outcomes["file_ok"]
    assert name == "blob.bin"
    assert data == b"loopback-file-payload-0123456789"
