# SPDX-License-Identifier: 0BSD

"""Live RRC interoperability tests against a custom rrcd hub daemon.

Each test runs a real hub process and one or more real client processes
on separate Reticulum instances connected over loopback TCP. The hub and
client record every envelope, path request, and interface counter to
JSONL, so the assertions measure what actually crossed the wire rather
than what the in-process state claims.

Covered:
- connect, join, echo, and traffic accounting
- restart replay suppression and manual retry identity
- hub restart reconnect bounds
- advertised rate limit enforcement end to end
- unreachable hub retry traffic bounds
- announce storm reconnect bounds

Enable with MESHCHAT_LIVE_RETICULUM=1.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from meshchatx.src.backend.rrc.manager import RRCHub
from tests.backend.support.test_temp_dir import subprocess_test_env

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"

pytestmark = pytest.mark.skipif(
    not _RUN,
    reason="set MESHCHAT_LIVE_RETICULUM=1 to run live rrcd tests",
)

SUPPORT_DIR = Path(__file__).resolve().parent / "rrc_live_support"
RRCD_SCRIPT = SUPPORT_DIR / "rrcd.py"
CLIENT_SCRIPT = SUPPORT_DIR / "rrc_client.py"

READY_TIMEOUT_S = 40.0
CONNECT_TIMEOUT_S = 60.0


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _write_rns_config(directory: Path, port: int, role: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    instance = f"rrc_{role}_{port}_{os.getpid()}"
    if role == "hub":
        interfaces = (
            "[interfaces]\n"
            "  [[TCP Server]]\n"
            "    type = TCPServerInterface\n"
            "    enabled = Yes\n"
            "    listen_ip = 127.0.0.1\n"
            f"    listen_port = {port}\n"
        )
    else:
        interfaces = (
            "[interfaces]\n"
            "  [[TCP Client]]\n"
            "    type = TCPClientInterface\n"
            "    enabled = Yes\n"
            "    target_host = 127.0.0.1\n"
            f"    target_port = {port}\n"
        )
    (directory / "config").write_text(
        "[reticulum]\n"
        "enable_transport = Yes\n"
        "share_instance = No\n"
        f"shared_instance_port = {39000 + (port % 500)}\n"
        f"instance_name = {instance}\n"
        "panic_on_interface_error = No\n"
        "\n"
        "[logging]\n"
        "loglevel = 2\n"
        "\n" + interfaces,
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _wait_for(predicate, timeout=20.0, interval=0.2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


class LiveStack:
    """Hub plus client processes wired over loopback TCP."""

    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
        self.port = _free_port()
        self.hub_dir = tmp_path / "hub"
        self.hub_share = tmp_path / "hub_share"
        self.hub_share.mkdir(parents=True, exist_ok=True)
        self.client_dir = tmp_path / "client"
        self.client_share = tmp_path / "client_share"
        self.client_share.mkdir(parents=True, exist_ok=True)
        self.hubs_path = tmp_path / "hubs.json"
        self.hub_process = None
        self.client_process = None
        self.client_phase = 0
        _write_rns_config(self.hub_dir, self.port, "hub")
        _write_rns_config(self.client_dir, self.port, "client")

    # -- processes ---------------------------------------------------------

    def start_hub(
        self, mode="hub", announce_interval=60, rate_limit=120, drop_msgs=False
    ):
        self.hub_share.mkdir(parents=True, exist_ok=True)
        (self.hub_share / "hub_stop").unlink(missing_ok=True)
        self.hub_process = subprocess.Popen(
            [
                sys.executable,
                str(RRCD_SCRIPT),
                str(self.hub_dir),
                str(self.hub_share),
                str(self.port),
                str(announce_interval),
                str(rate_limit),
                mode,
                "1" if drop_msgs else "0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=subprocess_test_env(),
        )
        ready = self.hub_share / "hub_ready.json"
        assert _wait_for(ready.is_file, timeout=READY_TIMEOUT_S), self._hub_error()
        return json.loads(ready.read_text(encoding="utf-8"))

    def stop_hub(self):
        if self.hub_process is None:
            return
        (self.hub_share / "hub_stop").write_text("stop", encoding="utf-8")
        try:
            self.hub_process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.hub_process.kill()
            self.hub_process.wait(timeout=10)
        self.hub_process = None

    def announce_now(self):
        (self.hub_share / "hub_announce").write_text("go", encoding="utf-8")

    def start_client(self, hub_hashes, fresh_share=True):
        if fresh_share:
            self.client_phase += 1
            self.client_share = self.tmp_path / f"client_share_{self.client_phase}"
            self.client_share.mkdir(parents=True, exist_ok=True)
        self.hubs_path.write_text(json.dumps(hub_hashes), encoding="utf-8")
        (self.client_share / "commands.jsonl").touch()
        self.client_process = subprocess.Popen(
            [
                sys.executable,
                str(CLIENT_SCRIPT),
                str(self.client_dir),
                str(self.client_share),
                str(self.hubs_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=subprocess_test_env(),
        )
        assert _wait_for(self.client_ready, timeout=READY_TIMEOUT_S), (
            self._client_error()
        )
        return self.client_process

    def stop_client(self):
        if self.client_process is None:
            return
        self.client_process.terminate()
        try:
            self.client_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.client_process.kill()
            self.client_process.wait(timeout=10)
        self.client_process = None

    def close(self):
        self.stop_client()
        self.stop_hub()

    # -- errors ------------------------------------------------------------

    def _hub_error(self):
        if self.hub_process is None:
            return "hub not started"
        if self.hub_process.poll() is None:
            return "hub did not become ready"
        _out, err = self.hub_process.communicate(timeout=5)
        return "hub exited " + str(self.hub_process.returncode) + ": " + (err or "")

    def _client_error(self):
        if self.client_process is None:
            return "client not started"
        if self.client_process.poll() is None:
            return "client did not become ready"
        _out, err = self.client_process.communicate(timeout=5)
        return (
            "client exited " + str(self.client_process.returncode) + ": " + (err or "")
        )

    # -- traffic -----------------------------------------------------------

    def hub_events(self) -> list[dict]:
        return _read_jsonl(self.hub_share / "hub_traffic.jsonl")

    def client_events(self) -> list[dict]:
        return _read_jsonl(self.client_share / "client_traffic.jsonl")

    def client_ready(self) -> bool:
        return any(row.get("ev") == "ready" for row in self.client_events())

    def hub_inbound(self, msg_type=None, chat_only=False) -> list[dict]:
        rows = [r for r in self.hub_events() if r.get("ev") == "in"]
        if msg_type is not None:
            rows = [r for r in rows if r.get("t") == msg_type]
        if chat_only:
            rows = [r for r in rows if not r.get("is_command")]
        return rows

    def hub_interface_totals(self):
        rows = [r for r in self.hub_events() if r.get("ev") == "ifstats"]
        if not rows:
            return {}
        last = rows[-1].get("interfaces", [])
        totals = {"rxb": 0, "txb": 0, "rxs": 0, "txs": 0}
        for row in last:
            for key in totals:
                value = row.get(key)
                if isinstance(value, int):
                    totals[key] += value
        return totals

    # -- commands ----------------------------------------------------------

    def send_command(self, command, expect_op=None, timeout=30.0):
        before = len([r for r in self.client_events() if r.get("ev") == "op"])
        path = self.client_share / "commands.jsonl"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(command) + "\n")

        def result():
            ops = [r for r in self.client_events() if r.get("ev") == "op"]
            if len(ops) <= before:
                return None
            return ops[-1]

        row = _wait_for(result, timeout=timeout)
        assert row is not None, (
            "no op result for " + str(command) + ": " + self._client_error()
        )
        if expect_op is not None:
            assert row.get("op") == expect_op, row
        return row

    def snapshot(self, timeout=30.0):
        row = self.send_command({"op": "snapshot"}, timeout=timeout)
        assert row.get("ok"), row
        states = [r for r in self.client_events() if r.get("ev") == "state"]
        assert states, "no state snapshot"
        return states[-1]

    def event_count(self) -> int:
        return len(self.client_events())

    def wait_status(self, status, timeout=CONNECT_TIMEOUT_S, since=None):
        base = 0 if since is None else int(since)

        def check():
            rows = self.client_events()[base:]
            for row in reversed(rows):
                if row.get("ev") == "status" and row.get("status") == status:
                    return row
            return None

        return _wait_for(check, timeout=timeout)

    def connect(self, hub_hash):
        self.announce_now()
        self.send_command(
            {"op": "connect"}, expect_op="connect", timeout=CONNECT_TIMEOUT_S
        )
        status = self.wait_status(RRCHub.STATUS_CONNECTED, timeout=CONNECT_TIMEOUT_S)
        assert status is not None, (
            "hub never reached connected: " + self._client_error()
        )
        return status

    def join(self, room="lobby", timeout=30.0):
        row = self.send_command(
            {"op": "join", "room": room}, expect_op="join", timeout=timeout
        )
        assert row.get("ok"), row
        state = self.snapshot()
        rooms = state["hubs"][0]["rooms"]
        assert room in rooms, state
        return state


@pytest.fixture
def stack(tmp_path):
    live = LiveStack(tmp_path)
    try:
        yield live
    finally:
        live.close()


def _traffic_summary(stack: LiveStack) -> str:
    inbound = stack.hub_inbound()
    outbound = [r for r in stack.hub_events() if r.get("ev") == "out"]
    client_out = [r for r in stack.client_events() if r.get("ev") == "out"]
    path_requests = [r for r in stack.client_events() if r.get("ev") == "path_request"]
    totals = stack.hub_interface_totals()
    return (
        "hub_in={inb} hub_out={out} client_out={cout} path_requests={pr} "
        "hub_rxb={rxb} hub_txb={txb}"
    ).format(
        inb=len(inbound),
        out=len(outbound),
        cout=len(client_out),
        pr=len(path_requests),
        rxb=totals.get("rxb"),
        txb=totals.get("txb"),
    )


def test_live_rrcd_connect_echo_and_traffic(stack):
    """Connect, join, echo three messages, and account the traffic."""
    info = stack.start_hub()
    hub_hash = info["dest"]
    stack.start_client([hub_hash])
    stack.connect(hub_hash)
    stack.join()

    for text in ("live one", "live two", "live three"):
        row = stack.send_command({"op": "send", "room": "lobby", "text": text})
        assert row.get("ok"), row

    def delivered():
        state = stack.snapshot()
        rows = state["hubs"][0]["messages"].get("lobby", [])
        mine = [m for m in rows if m["text"] in ("live one", "live two", "live three")]
        return (
            mine
            if len(mine) == 3 and all(m["delivery"] == "sent" for m in mine)
            else None
        )

    mine = _wait_for(delivered, timeout=30.0)
    assert mine is not None, _traffic_summary(stack)
    assert all(m["dup_count"] == 1 for m in mine), mine

    chat = stack.hub_inbound(msg_type=20, chat_only=True)
    assert len(chat) == 3, _traffic_summary(stack)
    assert {row["body"] for row in chat} == {"live one", "live two", "live three"}
    assert all(row["mid"] for row in chat), chat

    relayed = stack.hub_events()
    stats_rows = [r for r in relayed if r.get("ev") == "hub_stats"]
    assert stats_rows, "hub never reported stats"

    def relayed_stats():
        rows = [r for r in stack.hub_events() if r.get("ev") == "hub_stats"]
        return rows[-1] if rows and rows[-1]["stats"]["messages_relayed"] >= 3 else None

    assert _wait_for(relayed_stats, timeout=10.0), "hub never counted relayed messages"
    print("traffic:", _traffic_summary(stack))


def test_live_rrcd_restart_does_not_replay_and_retry_keeps_identity(stack):
    """A held message survives restart without replay, retry keeps the mid."""
    info = stack.start_hub(drop_msgs=True)
    hub_hash = info["dest"]
    stack.start_client([hub_hash])
    stack.connect(hub_hash)
    stack.join()

    row = stack.send_command({"op": "send", "room": "lobby", "text": "held back"})
    assert row.get("ok"), row
    original_mid = row["mid"]
    assert original_mid

    # The hub accepts the envelope without relaying. The client must sweep
    # the unconfirmed send to failed after DELIVERY_TIMEOUT_S.
    time.sleep(17)

    def failed_row():
        state = stack.snapshot()
        rows = state["hubs"][0]["messages"].get("lobby", [])
        match = [m for m in rows if m["text"] == "held back"]
        return match[0] if match and match[0]["delivery"] == "failed" else None

    held = _wait_for(failed_row, timeout=20.0)
    assert held is not None, "held message never turned failed"
    assert held["mid"] == original_mid

    inbound_before = stack.hub_inbound(msg_type=20, chat_only=True)
    assert len(inbound_before) == 1, _traffic_summary(stack)
    assert inbound_before[0]["mid"] == original_mid

    # Restart the client from disk. History rows read as failed, and a
    # history row must never be replayed automatically on reconnect.
    stack.stop_client()
    stack.start_client([hub_hash], fresh_share=True)
    stack.announce_now()
    stack.send_command(
        {"op": "connect"}, expect_op="connect", timeout=CONNECT_TIMEOUT_S
    )
    stack.wait_status(RRCHub.STATUS_CONNECTED, timeout=CONNECT_TIMEOUT_S)
    stack.join()

    time.sleep(6)
    replayed = stack.hub_inbound(msg_type=20, chat_only=True)
    assert len(replayed) == 1, "history replayed on restart: " + _traffic_summary(stack)

    # seq numbers are session scoped, so re-resolve the row after restart.
    state = stack.snapshot()
    rows = state["hubs"][0]["messages"].get("lobby", [])
    reloaded = [m for m in rows if m["text"] == "held back"]
    assert len(reloaded) == 1, rows
    assert reloaded[0]["delivery"] == "failed", reloaded
    assert reloaded[0]["mid"] == original_mid, reloaded

    retry = stack.send_command(
        {"op": "retry", "room": "lobby", "seq": reloaded[0]["seq"]},
        expect_op="retry",
    )
    assert retry.get("ok"), retry
    assert retry["mid"] == original_mid

    def retried():
        rows = stack.hub_inbound(msg_type=20, chat_only=True)
        return rows if len(rows) == 2 else None

    rows = _wait_for(retried, timeout=20.0)
    assert rows is not None, _traffic_summary(stack)
    assert rows[1]["mid"] == original_mid
    print("traffic:", _traffic_summary(stack))


def test_live_rrcd_hub_restart_reconnect_is_bounded(stack):
    """Hub restart reconnects without a tight retry loop or replay."""
    info = stack.start_hub()
    hub_hash = info["dest"]
    stack.start_client([hub_hash])
    stack.connect(hub_hash)
    stack.join()
    row = stack.send_command({"op": "send", "room": "lobby", "text": "before outage"})
    assert row.get("ok"), row

    def delivered():
        state = stack.snapshot()
        rows = state["hubs"][0]["messages"].get("lobby", [])
        return [
            m for m in rows if m["text"] == "before outage" and m["delivery"] == "sent"
        ]

    assert _wait_for(delivered, timeout=20.0)

    inbound_before = len(stack.hub_inbound(msg_type=20, chat_only=True))

    marker = stack.event_count()
    stack.stop_hub()
    outage_started = time.monotonic()
    time.sleep(20)

    def connect_attempts():
        rows = [
            r
            for r in stack.client_events()[marker:]
            if r.get("ev") == "status" and r.get("status") == RRCHub.STATUS_CONNECTING
        ]
        return len(rows)

    attempts_during_outage = connect_attempts()
    assert attempts_during_outage <= 6, (
        "too many reconnect attempts during outage: " + str(attempts_during_outage)
    )

    stack.start_hub()
    stack.announce_now()
    reconnected = stack.wait_status(
        RRCHub.STATUS_CONNECTED,
        timeout=CONNECT_TIMEOUT_S,
        since=marker,
    )
    assert reconnected is not None, "client never reconnected: " + _traffic_summary(
        stack
    )
    recovery_s = time.monotonic() - outage_started - 20
    assert recovery_s < 45, "slow reconnect after hub restart: " + str(recovery_s)

    stack.join()
    time.sleep(5)
    replayed = stack.hub_inbound(msg_type=20, chat_only=True)
    assert len(replayed) == inbound_before, (
        "message replayed after hub restart: " + _traffic_summary(stack)
    )

    row = stack.send_command({"op": "send", "room": "lobby", "text": "after outage"})
    assert row.get("ok"), row
    print(
        "traffic:",
        _traffic_summary(stack),
        "outage_attempts=",
        attempts_during_outage,
    )


def test_live_rrcd_rate_limit_enforced_on_wire(stack):
    """The advertised limit bounds what the hub actually receives."""
    info = stack.start_hub(rate_limit=5)
    hub_hash = info["dest"]
    stack.start_client([hub_hash])
    stack.connect(hub_hash)
    stack.join()

    results = [
        stack.send_command(
            {"op": "send", "room": "lobby", "text": "burst " + str(i)},
            timeout=20.0,
        )
        for i in range(10)
    ]

    accepted = [r for r in results if r.get("ok")]
    rejected = [r for r in results if not r.get("ok")]
    assert accepted, results
    assert rejected, "client budget never rejected a burst send"
    assert any("RateLimited" in (r.get("error") or "") for r in rejected), rejected

    chat = stack.hub_inbound(msg_type=20, chat_only=True)
    assert len(chat) <= 5, (
        "hub received more chat than advertised: " + _traffic_summary(stack)
    )
    assert len(chat) == len(accepted), (
        len(chat),
        len(accepted),
        _traffic_summary(stack),
    )
    print("traffic:", _traffic_summary(stack), "accepted=", len(accepted))


def test_live_rrcd_unreachable_hubs_retry_traffic_bounded(stack):
    """Twenty unreachable hubs must not produce a retry or byte flood."""
    info = stack.start_hub()
    backbone = info["dest"]

    def fake_hash(seed):
        return (bytes([seed]) * 16).hex()

    fake_hubs = [fake_hash(1 + i) for i in range(20)]
    stack.start_client([backbone, *fake_hubs])
    stack.connect(backbone)

    start = time.monotonic()
    time.sleep(75)
    elapsed = time.monotonic() - start

    attempts = [
        r
        for r in stack.client_events()
        if r.get("ev") == "status" and r.get("status") == RRCHub.STATUS_CONNECTING
    ]
    path_requests = [r for r in stack.client_events() if r.get("ev") == "path_request"]
    totals = stack.hub_interface_totals()
    sent_bytes = totals.get("rxb") or 0

    per_hub_attempts = len(attempts) / float(len(fake_hubs))
    print(
        "traffic:",
        _traffic_summary(stack),
        "elapsed=",
        round(elapsed, 1),
        "attempts=",
        len(attempts),
        "per_hub=",
        round(per_hub_attempts, 2),
    )

    assert per_hub_attempts <= 6, "unreachable hubs retried too often: " + str(
        per_hub_attempts
    )
    # Each dead hub may spend a burst of two path requests plus one refill
    # in the 75s window. Before the token bucket this run measured 241
    # requests and 36 KB received by the peer interface.
    assert len(path_requests) <= 80, "path request storm: " + str(len(path_requests))
    assert sent_bytes < 4 * 1024 * 1024, "unreachable hubs sent too many bytes: " + str(
        sent_bytes
    )


def test_live_rrcd_idle_traffic_is_quiet(stack):
    """A connected, idle client must not burn measurable bandwidth.

    The reported failure mode was gigabytes per day with RCC idle. This
    measures the real interface counters on both ends across a quiet
    window with one connected hub.
    """
    info = stack.start_hub()
    hub_hash = info["dest"]
    stack.start_client([hub_hash])
    stack.connect(hub_hash)
    stack.join()

    time.sleep(3)
    start_totals = stack.hub_interface_totals()
    start_events = len(stack.hub_events())
    start_client_out = len([r for r in stack.client_events() if r.get("ev") == "out"])

    time.sleep(60)

    end_totals = stack.hub_interface_totals()
    end_client_out = len([r for r in stack.client_events() if r.get("ev") == "out"])

    rx_delta = (end_totals.get("rxb") or 0) - (start_totals.get("rxb") or 0)
    tx_delta = (end_totals.get("txb") or 0) - (start_totals.get("txb") or 0)
    hub_envelopes = [
        r for r in stack.hub_events()[start_events:] if r.get("ev") in ("in", "out")
    ]
    client_sends = end_client_out - start_client_out

    print(
        "idle 60s:",
        "rx_delta=",
        rx_delta,
        "tx_delta=",
        tx_delta,
        "hub_envelopes=",
        len(hub_envelopes),
        "client_sends=",
        client_sends,
    )

    assert client_sends <= 2, "idle client sent " + str(client_sends) + " envelopes"
    assert len(hub_envelopes) <= 8, (
        "idle hub saw " + str(len(hub_envelopes)) + " envelopes"
    )
    assert rx_delta < 32 * 1024, "idle received bytes: " + str(rx_delta)
    assert tx_delta < 32 * 1024, "idle sent bytes: " + str(tx_delta)


def test_live_rrcd_announce_storm_does_not_pin_reconnect(stack):
    """Announcing-but-unreachable hubs cannot hold the fast retry tier."""
    info = stack.start_hub()
    backbone = info["dest"]

    zombie_dir = stack.tmp_path / "zombie"
    zombie_share = stack.tmp_path / "zombie_share"
    _write_rns_config(zombie_dir, stack.port, "client")
    zombie_share.mkdir(parents=True, exist_ok=True)
    zombie = subprocess.Popen(
        [
            sys.executable,
            str(RRCD_SCRIPT),
            str(zombie_dir),
            str(zombie_share),
            str(stack.port),
            "5",
            "120",
            "zombie",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=subprocess_test_env(),
    )
    try:
        ready = zombie_share / "hub_ready.json"
        assert _wait_for(ready.is_file, timeout=READY_TIMEOUT_S)
        zombie_hash = json.loads(ready.read_text(encoding="utf-8"))["dest"]

        stack.start_client([backbone, zombie_hash])
        stack.connect(backbone)

        start = time.monotonic()
        time.sleep(75)
        elapsed = time.monotonic() - start

        zombie_attempts = [
            r
            for r in stack.client_events()
            if r.get("ev") == "status"
            and r.get("hub") == zombie_hash
            and r.get("status") == RRCHub.STATUS_CONNECTING
        ]
        announces = [
            r
            for r in stack.client_events()
            if r.get("ev") == "announce" and r.get("hub") == zombie_hash
        ]
        print(
            "traffic:",
            _traffic_summary(stack),
            "elapsed=",
            round(elapsed, 1),
            "zombie_attempts=",
            len(zombie_attempts),
            "announces_seen=",
            len(announces),
        )
        assert len(announces) >= 5, "zombie announces did not reach the client"
        assert len(zombie_attempts) <= 8, (
            "announce storm pinned reconnect attempts: " + str(len(zombie_attempts))
        )
    finally:
        (zombie_share / "hub_stop").write_text("stop", encoding="utf-8")
        try:
            zombie.wait(timeout=15)
        except subprocess.TimeoutExpired:
            zombie.kill()
            zombie.wait(timeout=10)
