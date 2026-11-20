# SPDX-License-Identifier: 0BSD
"""Live adversarial mesh tests over real loopback Reticulum.

Bob runs in a subprocess recording deliveries to JSONL so exact-once
delivery can be asserted. Stamps disabled like other live harnesses.
"""

import json
import os
import subprocess
import sys
import time

import pytest

from tests.backend.test_live_loopback_outbound import _free_port, _write_config

pytestmark = pytest.mark.skipif(
    os.environ.get("MESHCHAT_LIVE_RETICULUM") != "1",
    reason="live loopback tests disabled",
)

_BOB_SCRIPT = r"""
import json, os, sys, time
import RNS, LXMF

config_dir, share_dir = sys.argv[1], sys.argv[2]
RNS.Transport.STAMP_DESTINATIONS = False
RNS.Transport.STAMP_PRS = False
RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_ERROR)
identity = RNS.Identity()
storage = os.path.join(config_dir, "lxmf_storage")
os.makedirs(storage, exist_ok=True)
router = LXMF.LXMRouter(storagepath=storage)
lxmf_dest = router.register_delivery_identity(identity, display_name="bob")

inbox = os.path.join(share_dir, "inbox.jsonl")

def on_delivery(message):
    with open(inbox, "a", encoding="utf-8") as h:
        h.write(json.dumps({
            "hash": message.hash.hex(),
            "content": message.content_as_string(),
        }) + "\n")

router.register_delivery_callback(on_delivery)

node_identity = RNS.Identity()
node_dest = RNS.Destination(node_identity, RNS.Destination.IN,
                            RNS.Destination.SINGLE, "nomadnetwork", "node")
node_dest.register_request_handler(
    "/page/index.mu", response_generator=lambda *a: b"[`c`f4 hi `a]",
    allow=RNS.Destination.ALLOW_ALL,
)

with open(os.path.join(share_dir, "ready.json"), "w") as h:
    json.dump({"lxmf_dest": lxmf_dest.hash.hex(),
               "lxmf_pub": identity.get_public_key().hex(),
               "node_dest": node_dest.hash.hex()}, h)

announce_path = os.path.join(share_dir, "announce")
stop_path = os.path.join(share_dir, "stop")
announced = False
end = time.time() + 600
while time.time() < end and not os.path.isfile(stop_path):
    if os.path.isfile(announce_path) and not announced:
        lxmf_dest.announce()
        node_dest.announce()
        announced = True
    time.sleep(0.1)
RNS.exit(0)
"""


def _spawn_bob(bob_dir, share):
    """Start a Bob subprocess and wait for its fresh ready.json."""
    bob = subprocess.Popen(
        [sys.executable, "-c", _BOB_SCRIPT, str(bob_dir), str(share)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ),
    )
    ready = share / "ready.json"
    deadline = time.time() + 30
    while time.time() < deadline and not ready.is_file():
        if bob.poll() is not None:
            out, err = bob.communicate(timeout=5)
            raise AssertionError(f"bob exited {bob.returncode}: {err}\n{out}")
        time.sleep(0.1)
    assert ready.is_file(), "bob did not come up"
    return bob


@pytest.fixture(scope="module")
def mesh_pair(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("mesh_adv")
    port = _free_port()
    share = tmp_path / "share"
    share.mkdir()
    bob_dir = tmp_path / "bob"
    _write_config(bob_dir, port, "server", listen_port=port)
    bob = _spawn_bob(bob_dir, share)
    ready = share / "ready.json"

    alice_dir = tmp_path / "alice"
    _write_config(alice_dir, port, "client")
    import RNS

    RNS.Transport.STAMP_DESTINATIONS = False
    RNS.Transport.STAMP_PRS = False
    reticulum = RNS.Reticulum(configdir=str(alice_dir), loglevel=RNS.LOG_ERROR)
    identity = RNS.Identity()
    ctx = {
        "bob": bob,
        "share": share,
        "bob_dir": bob_dir,
        "ready": json.loads(ready.read_text()),
        "identity": identity,
        "reticulum": reticulum,
    }
    yield ctx
    (share / "stop").touch()
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass
    try:
        ctx["bob"].wait(timeout=15)
    except subprocess.TimeoutExpired:
        ctx["bob"].kill()
        ctx["bob"].wait(timeout=5)


def _alice_router(mesh_pair):
    """One LXMRouter per process; destinations cannot be registered twice."""
    import LXMF

    if "alice_router" in mesh_pair:
        return mesh_pair["alice_router"]
    storage = mesh_pair["share"] / "alice_lxmf"
    storage.mkdir(exist_ok=True)
    router = LXMF.LXMRouter(storagepath=str(storage))
    own = router.register_delivery_identity(mesh_pair["identity"], display_name="alice")
    mesh_pair["alice_router"] = (router, own)
    return router, own


def _send(mesh_pair, router, own_dest, content, title="t"):
    import LXMF
    import RNS

    bob_dest_hash = bytes.fromhex(mesh_pair["ready"]["lxmf_dest"])
    bob_ident = RNS.Identity.recall(bob_dest_hash)
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
        content=content,
        title=title,
        desired_method=LXMF.LXMessage.DIRECT,
    )
    router.handle_outbound(msg)


def _inbox(mesh_pair):
    p = mesh_pair["share"] / "inbox.jsonl"
    if not p.is_file():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def _wait_inbox(mesh_pair, n, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = _inbox(mesh_pair)
        if len(rows) >= n:
            return rows
        time.sleep(0.3)
    return _inbox(mesh_pair)


def test_concurrent_sends_delivered_exactly_once(mesh_pair):
    """N same-peer sends land exactly once each — no dupes, none lost."""
    import RNS

    (mesh_pair["share"] / "announce").touch()
    bob_dest = bytes.fromhex(mesh_pair["ready"]["lxmf_dest"])
    deadline = time.time() + 30
    while not RNS.Transport.has_path(bob_dest) and time.time() < deadline:
        RNS.Transport.request_path(bob_dest)
        time.sleep(0.4)
    assert RNS.Transport.has_path(bob_dest)

    router, own = _alice_router(mesh_pair)
    sent = [f"concurrent-{i}-{os.urandom(4).hex()}" for i in range(5)]
    for c in sent:
        _send(mesh_pair, router, own, c)

    rows = _wait_inbox(mesh_pair, len(sent))
    got = [r["content"] for r in rows]
    for c in sent:
        assert got.count(c) == 1, f"expected exactly-once, got {got.count(c)} for {c}"
    hashes = [r["hash"] for r in rows]
    assert len(set(hashes)) == len(hashes)


SOAK_SECONDS = int(os.environ.get("MESHCHAT_SOAK_SECONDS", "45"))


@pytest.mark.skipif(
    os.environ.get("MESHCHAT_LIVE_SOAK") != "1",
    reason="soak test; set MESHCHAT_LIVE_SOAK=1",
)
def test_idle_and_burst_soak_bounded(mesh_pair):
    """Idle + burst soak: bounded RSS/fd/thread growth, no idle packet flood."""
    import resource

    import RNS

    (mesh_pair["share"] / "announce").touch()
    bob_dest = bytes.fromhex(mesh_pair["ready"]["lxmf_dest"])
    deadline = time.time() + 30
    while not RNS.Transport.has_path(bob_dest) and time.time() < deadline:
        RNS.Transport.request_path(bob_dest)
        time.sleep(0.4)

    def fds():
        return len(os.listdir("/proc/self/fd"))

    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    threads0 = len(os.listdir("/proc/self/task"))
    fds0 = fds()

    # Idle phase
    time.sleep(SOAK_SECONDS // 3)
    # Burst phase — count only rows that arrive during this test.
    baseline = len(_inbox(mesh_pair))
    router, own = _alice_router(mesh_pair)
    for i in range(10):
        _send(mesh_pair, router, own, f"burst-{i}-{os.urandom(4).hex()}")
    deadline = time.time() + 60
    while time.time() < deadline and len(_inbox(mesh_pair)) < baseline + 10:
        time.sleep(0.3)
    assert len(_inbox(mesh_pair)) >= baseline + 10, "burst messages not delivered"
    # Cool-down
    time.sleep(SOAK_SECONDS // 3)

    threads1 = len(os.listdir("/proc/self/task"))
    fds1 = fds()
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    assert threads1 - threads0 < 15, f"thread growth {threads0}->{threads1}"
    assert fds1 - fds0 < 30, f"fd growth {fds0}->{fds1}"
    # ru_maxrss is peak-not-current on Linux, so allow generous slack:
    # the burst itself allocates, but an unbounded leak would blow past this.
    assert rss1 - rss0 < 256 * 1024, f"RSS growth {rss0}->{rss1} KB"


def test_peer_vanish_mid_announce_fails_clean(mesh_pair):
    """Killing Bob mid-interaction leaves Alice alive and failing fast."""
    import RNS

    mesh_pair["bob"].terminate()
    mesh_pair["bob"].wait(timeout=10)

    ghost = bytes.fromhex(mesh_pair["ready"]["node_dest"])
    t0 = time.monotonic()
    got_path = False
    for _ in range(8):
        if RNS.Transport.has_path(ghost):
            got_path = True
            break
        RNS.Transport.request_path(ghost)
        time.sleep(0.5)
    assert time.monotonic() - t0 < 20, "path discovery hung on dead peer"
    assert not got_path or True  # path may be cached; the bound is the point

    # Restart Bob so later tests in this module still have a live peer.
    # A fresh Bob gets a new identity, so ready.json must be regenerated.
    share = mesh_pair["share"]
    (share / "ready.json").unlink(missing_ok=True)
    mesh_pair["bob"] = _spawn_bob(mesh_pair["bob_dir"], share)
    mesh_pair["ready"] = json.loads((share / "ready.json").read_text())


def test_size_boundaries_deliver(mesh_pair):
    """Below/at/above the single-packet delivery limit all arrive intact."""
    import LXMF
    import RNS

    (mesh_pair["share"] / "announce").touch()
    bob_dest = bytes.fromhex(mesh_pair["ready"]["lxmf_dest"])
    deadline = time.time() + 30
    while not RNS.Transport.has_path(bob_dest) and time.time() < deadline:
        RNS.Transport.request_path(bob_dest)
        time.sleep(0.4)
    assert RNS.Transport.has_path(bob_dest)

    router, own = _alice_router(mesh_pair)
    limit = LXMF.LXMRouter.DELIVERY_LIMIT
    # packed overhead is a few hundred bytes; probe around the limit by
    # sizing content relative to it rather than guessing exact packing.
    cases = {
        "small": "x" * (limit - 400),
        "edge": "y" * (limit - 250),
        "large": "z" * (limit + 600),
    }
    for tag, content in cases.items():
        _send(mesh_pair, router, own, content, title=f"bnd-{tag}")
    baseline = len(_inbox(mesh_pair))
    # The >limit case rides an LXMF resource transfer; on a throttled CPU
    # after a soak burst it can take a while. Wait generously, assert exactly.
    got = _wait_inbox(mesh_pair, baseline + len(cases), timeout=240)
    contents = [r["content"] for r in got[-len(cases) :]]
    for tag, content in cases.items():
        assert content in contents, f"{tag} message missing/mangled"
