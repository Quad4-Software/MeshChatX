# SPDX-License-Identifier: 0BSD

"""Own-message delivery state: pending, echo-confirmed, failed, retry."""

import time

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import (
    DELIVERY_TIMEOUT_S,
    RateLimitedError,
    RRCHub,
)
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint
from tests.backend.test_rrc_server import (
    FakeManager,
    FakeServerManager,
    _loopback_client_hub,
)


class _Mgr(FakeManager):
    def get_nickname(self):
        return "me"


def test_loopback_echo_confirms_delivery(tmp_path):
    """A relayed self-echo flips the local message from sending to sent."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "hello loopback")
    assert isinstance(mid, bytes)
    msgs = hub.messages["general"]
    own = [m for m in msgs if m.delivery is not None]
    assert own[-1].text == "hello loopback"
    assert own[-1].delivery == "sent"
    assert not hub._pending_delivery


def test_send_failure_drops_pending_state(tmp_path):
    """A raise in _send_env leaves no pending entry and no delivery flag."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    with pytest.raises(RuntimeError):
        hub.send_message("general", "no link")
    assert not hub._pending_delivery


def test_delivery_sweep_marks_expired_failed(tmp_path):
    """An echo that never arrives within the window marks the msg failed."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "text", 0)
    msg.delivery = "sending"
    msg.mid = b"\x99" * 8
    hub._pending_delivery[msg.mid] = (msg, time.monotonic() - DELIVERY_TIMEOUT_S - 1)
    hub._sweep_pending_delivery()
    assert msg.delivery == "failed"
    assert msg._auto_retryable is True
    assert not hub._pending_delivery


def test_delivery_sweep_leaves_fresh_pending(tmp_path):
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "text", 0)
    msg.delivery = "sending"
    msg.mid = b"\x99" * 8
    hub._pending_delivery[msg.mid] = (msg, time.monotonic())
    hub._sweep_pending_delivery()
    assert msg.delivery == "sending"
    assert msg.mid in hub._pending_delivery


def test_link_close_flushes_pending_failed(tmp_path):
    """Link teardown flags every unconfirmed send as failed."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "lost", 0)
    msg.delivery = "sending"
    msg.mid = b"\x77" * 8
    hub._pending_delivery[msg.mid] = (msg, time.monotonic())
    link = hub.link
    hub._on_closed(link)
    assert msg.delivery == "failed"
    assert msg._auto_retryable is True
    assert not hub._pending_delivery


def test_retry_failed_message_resends(tmp_path):
    """Retry re-sends the body under the same mid and re-pends the echo."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "retry me")
    own = [m for m in hub.messages["general"] if m.text == "retry me"][-1]
    # Simulate hub never echoing: force-fail the entry.
    own.delivery = "failed"
    new_mid = hub.retry_message("general", own.seq)
    assert isinstance(new_mid, bytes)
    assert new_mid == mid
    assert own.delivery == "sent"
    assert not hub._pending_delivery


def test_retry_rejects_confirmed_message(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    hub.send_message("general", "already there")
    own = [m for m in hub.messages["general"] if m.text == "already there"][-1]
    assert own.delivery == "sent"
    with pytest.raises(ValueError):
        hub.retry_message("general", own.seq)


def test_retry_unknown_seq_raises(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    with pytest.raises(ValueError):
        hub.retry_message("general", 999_999)


def test_history_sending_loads_as_failed(tmp_path):
    """Persisted 'sending' state can never confirm after reload."""
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    entry = hub._entry_for(
        proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "gone", 0)
    )
    loaded = hub._msg_from_entry("general", entry)
    assert loaded.delivery is None
    entry["d"] = "sending"
    loaded = hub._msg_from_entry("general", entry)
    assert loaded.delivery == "failed"
    entry["d"] = "sent"
    loaded = hub._msg_from_entry("general", entry)
    assert loaded.delivery == "sent"


def test_failed_message_auto_retries_once_on_rejoin(tmp_path):
    """After link loss, a re-JOIN resends failed messages exactly once."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "lost?", 0)
    msg.delivery = "sending"
    msg.mid = b"\x99" * 8
    msg.seq = 9001
    hub._pending_delivery[msg.mid] = (
        msg,
        time.monotonic() - DELIVERY_TIMEOUT_S - 1,
    )
    hub.messages["general"].append(msg)
    hub._sweep_pending_delivery()
    assert msg.delivery == "failed"

    hub._pending_joins.add("general")  # self-join marker set by join_room
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room="general", body=[b"\x22" * 16]
    )
    hub._handle_joined(env)
    # The retry pass is deferred so a T_SEEN resync can land first. Run it
    # directly instead of waiting out the timer.
    hub._rejoin_retry_pass()
    assert msg.delivery == "sent"  # loopback echo confirmed the retry
    assert msg.mid == b"\x99" * 8  # retry reuses the original envelope id

    # A second JOINED must not resend. the one-shot flag is set.
    hub._pending_joins.add("general")
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room="general", body=[b"\x22" * 16]
    )
    hub._handle_joined(env)
    hub._rejoin_retry_pass()
    assert msg.mid == b"\x99" * 8


def _self_join(hub, room="general"):
    """Deliver a JOINED confirm for our own pending join."""
    hub._pending_joins.add(room)
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room=room, body=[b"\x22" * 16]
    )
    hub._handle_joined(env)


def test_history_loaded_failed_message_never_auto_retries(tmp_path):
    """Persisted-unconfirmed rows must not replay on rejoin.

    History entries are appended while delivery is still "sending" and
    load back as "failed". Replaying them on every restart reposts
    already delivered messages to the hub, which is the room spam RCC
    operators reported.
    """
    _server, hub = _loopback_client_hub(tmp_path)
    entry = hub._entry_for(
        proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "old news", 1)
    )
    entry["d"] = "sending"  # persisted mid-flight, echo never recorded
    loaded = hub._msg_from_entry("general", entry)
    assert loaded.delivery == "failed"
    loaded.seq = 9002
    hub.messages["general"].append(loaded)

    calls = []
    orig = hub.retry_message
    hub.retry_message = lambda room, seq: calls.append(seq) or orig(room, seq)
    _self_join(hub)
    assert calls == []
    assert loaded.delivery == "failed"  # untouched, manual retry still open


def test_session_failed_message_auto_retries_with_same_mid_and_ts(tmp_path):
    """In-session failures retry once on rejoin, reusing mid and ts."""
    _server, hub = _loopback_client_hub(tmp_path)
    old_ts = proto.now_ms() - 60_000
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "lost?", old_ts)
    msg.delivery = "sending"
    msg.mid = b"\x99" * 8
    msg.seq = 9003
    hub._pending_delivery[msg.mid] = (
        msg,
        time.monotonic() - DELIVERY_TIMEOUT_S - 1,
    )
    hub.messages["general"].append(msg)
    hub._sweep_pending_delivery()

    sent_envs = []
    orig_send = hub._send_env

    def spy(env):
        sent_envs.append(env)
        return orig_send(env)

    hub._send_env = spy
    _self_join(hub)
    hub._rejoin_retry_pass()
    resent = [e for e in sent_envs if e.get(proto.K_T) == proto.T_MSG]
    assert len(resent) == 1
    assert resent[0][proto.K_ID] == b"\x99" * 8
    assert resent[0][proto.K_TS] == old_ts
    assert msg.delivery == "sent"


def test_auto_retry_skips_command_like_text(tmp_path):
    """A stored body starting with / must not replay as a hub command."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "/nick evil", 0)
    msg.delivery = "sending"
    msg.mid = b"\x55" * 8
    msg.seq = 9004
    hub._pending_delivery[msg.mid] = (
        msg,
        time.monotonic() - DELIVERY_TIMEOUT_S - 1,
    )
    hub.messages["general"].append(msg)
    hub._sweep_pending_delivery()

    calls = []
    orig = hub.retry_message
    hub.retry_message = lambda room, seq: calls.append(seq) or orig(room, seq)
    _self_join(hub)
    assert calls == []


def test_manual_retry_allowed_on_history_loaded_failed(tmp_path):
    """Loaded-failed rows stay manually retryable from the UI."""
    _server, hub = _loopback_client_hub(tmp_path)
    entry = hub._entry_for(
        proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "still here", 1)
    )
    entry["d"] = "sending"
    loaded = hub._msg_from_entry("general", entry)
    loaded.seq = 9005
    hub.messages["general"].append(loaded)

    mid = hub.retry_message("general", loaded.seq)
    assert isinstance(mid, bytes)
    assert loaded.delivery == "sent"


import RNS

from meshchatx.src.backend.rrc.manager import RRCManager
from tests.backend.test_rrc_protocol import FakeIdentity


def _manager_with_hub(tmp_path):
    manager = RRCManager(
        identity=FakeIdentity(),
        storage_dir=str(tmp_path),
        get_nickname=lambda: "me",
    )
    hub = manager.add_hub(b"\x44" * 16, name="hub")
    return manager, hub


def test_connect_auto_reconnect_waits_for_first_interface(tmp_path, monkeypatch):
    """Startup auto-connect holds off until an interface reports online."""
    manager, hub = _manager_with_hub(tmp_path)
    hub.auto_reconnect = True

    calls = {"connects": 0}

    class FakeReticulum:
        def get_interface_stats(self):
            calls["connects"] += 1
            # Come online on the second poll so the wait loop is exercised.
            online = calls["connects"] > 1
            return {"interfaces": [{"status": online}]}

    monkeypatch.setattr(
        RNS.Reticulum, "get_instance", staticmethod(lambda: FakeReticulum())
    )
    started = []
    monkeypatch.setattr(hub, "connect", lambda: started.append(hub))

    start = time.monotonic()
    manager.connect_auto_reconnect_hubs()
    assert time.monotonic() - start >= 0.2
    assert started == [hub]

    # Second call skips the wait entirely.
    started.clear()
    calls["connects"] = 0
    manager.connect_auto_reconnect_hubs()
    assert calls["connects"] == 0
    assert started == [hub]


def test_connect_auto_reconnect_no_reticulum_returns_fast(tmp_path, monkeypatch):
    manager, hub = _manager_with_hub(tmp_path)
    hub.auto_reconnect = True

    def no_instance():
        raise RuntimeError("no reticulum")

    monkeypatch.setattr(RNS.Reticulum, "get_instance", staticmethod(no_instance))
    started = []
    monkeypatch.setattr(hub, "connect", lambda: started.append(hub))

    start = time.monotonic()
    manager.connect_auto_reconnect_hubs()
    assert time.monotonic() - start < 1.0
    assert started == [hub]


def test_path_request_bucket_spends_burst_then_refills(tmp_path):
    """Two requests go out, then the bucket holds until the refill window."""
    from meshchatx.src.backend.rrc import manager as rrc_manager

    hub = RRCHub(_Mgr(), b"\x55" * 16, name="dead hub")
    assert hub._take_path_request_token() is True
    assert hub._take_path_request_token() is True
    assert hub._take_path_request_token() is False

    hub._path_token_last -= rrc_manager.PATH_REQUEST_REFILL_S
    assert hub._take_path_request_token() is True
    assert hub._take_path_request_token() is False


def test_connect_worker_path_requests_bounded_by_burst(tmp_path, monkeypatch):
    """A dead hub gets the burst and no more inside the wait window.

    Without the bucket this worker sends one request per retry cadence
    for the whole window, which for a large configured hub set turns
    into a sustained mesh wide path request spray.
    """
    from meshchatx.src.backend.rrc import manager as rrc_manager

    _manager, hub = _manager_with_hub(tmp_path)
    hub.auto_reconnect = False
    requests = []

    monkeypatch.setattr(rrc_manager, "slowest_online_bitrate", lambda *a, **k: None)
    monkeypatch.setattr(rrc_manager, "path_response_window", lambda *a, **k: 1.0)
    monkeypatch.setattr(rrc_manager, "CONNECT_PATH_RETRY_S", 0.1)
    monkeypatch.setattr(
        rrc_manager.RNS.Transport,
        "has_path",
        staticmethod(lambda h: False),
    )
    monkeypatch.setattr(
        rrc_manager.RNS.Transport,
        "request_path",
        staticmethod(lambda h: requests.append(h)),
    )
    monkeypatch.setattr(
        rrc_manager.RNS.Identity,
        "recall",
        staticmethod(lambda h: None),
    )

    hub._connect_worker()

    assert hub.status == RRCHub.STATUS_FAILED
    # The shared mesh-wide path policy has a five-second per-destination
    # floor, which is stricter than this legacy hub-local burst inside the
    # shortened one-second test window. The important invariant here is that
    # the retry loop does not emit once per 100ms cadence.
    assert requests == [hub.hub_hash]


def test_restart_does_not_replay_sent_history(tmp_path):
    """Full restart cycle: delivered history must not repost to the hub.

    Reproduces the reported RCC spam: a client sends a message, exits,
    and its history row must load back with the confirmed state, not
    as "failed", because the echo confirmation is now persisted as an
    update record. Before the fix the rejoin auto-retry reposted it to
    the hub on every restart.
    """
    server, hub = _loopback_client_hub(tmp_path)
    hub.send_message("general", "first session message")
    own = [m for m in hub.messages["general"] if m.text == "first session message"][-1]
    assert own.delivery == "sent"
    relayed_before = len(server._message_log)
    assert relayed_before == 1

    # Simulate app restart: a fresh manager rebuilds hubs and room
    # history from the persisted store files.
    manager2 = RRCManager(
        identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path)
    )
    manager2.set_server_manager(FakeServerManager([server]))
    manager2.load()
    hub2 = manager2.hubs[0]
    assert "general" in hub2.rooms

    # The delivered message loads back as sent: the echo confirmation
    # was persisted as a history update record.
    loaded = [
        m for m in hub2.messages.get("general", []) if m.text == "first session message"
    ]
    assert loaded and loaded[-1].delivery == "sent"

    # Reconnect to the same hub. HELLO -> WELCOME rejoins the saved room,
    # JOINED runs the auto-retry gate, and nothing may reach the wire.
    link = _LoopbackEndpoint(hub2, server)
    server._attach_loopback(link, manager2.identity)
    hub2._hub_identity_hash = server.identity.hash
    hub2.link = link
    hub2._send_hello(link)
    assert hub2.welcomed is True
    assert "general" in hub2.rooms

    assert len(server._message_log) == relayed_before


def test_restart_preserves_failed_badge_without_silently_resending(tmp_path):
    """Unconfirmed rows keep their failed badge across restarts."""
    server, hub = _loopback_client_hub(tmp_path)
    # Persist a send whose echo never arrived: it stays unconfirmed.
    pending = proto.RRCMessage(
        "msg",
        "general",
        b"\x22" * 16,
        "me",
        "may or may not have landed",
        proto.now_ms(),
    )
    pending.delivery = "sending"
    pending.mid = b"\x77" * 8
    hub._append_history("general", pending)

    manager2 = RRCManager(
        identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path)
    )
    manager2.set_server_manager(FakeServerManager([server]))
    manager2.load()
    hub2 = manager2.hubs[0]
    loaded = [
        m
        for m in hub2.messages.get("general", [])
        if m.text == "may or may not have landed"
    ]
    # The badge still marks the row as unconfirmed so the user can see it
    # and retry by hand. Only automatic replay is suppressed.
    assert loaded and loaded[-1].delivery == "failed"


def test_send_budget_warning_is_rate_limited(tmp_path):
    """A blocked send logs one warning, not one per rejected call."""
    hub = RRCHub(_Mgr(), b"\x77" * 16, name="hub")
    hub.rate_limit_msgs_per_minute = 2
    with hub._lock:
        hub._send_budget_tokens = 2.0
        hub._send_budget_last = time.monotonic()

    logs = []
    hub._log = lambda msg, level=None: logs.append((level, msg))

    hub._take_send_budget()
    hub._take_send_budget()
    for _ in range(5):
        with pytest.raises(RateLimitedError):
            hub._take_send_budget()

    warnings = [msg for level, msg in logs if level == RNS.LOG_WARNING]
    assert len(warnings) == 1
    assert "send budget exhausted" in warnings[0]


def test_duplicate_redelivery_warning_at_threshold(tmp_path):
    """A row that keeps growing logs a redelivery warning once per tier."""
    from meshchatx.src.backend.rrc.manager import DUP_WARN_COUNTS

    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "dup target")
    row = [m for m in hub.messages["general"] if m.text == "dup target"][-1]
    assert row.dup_count == 1

    logs = []
    hub._log = lambda msg, level=None: logs.append((level, msg))

    threshold = DUP_WARN_COUNTS[0]
    for _ in range(threshold - 1):
        assert hub._bump_duplicate_by_mid(mid) is True
    assert row.dup_count == threshold

    warnings = [msg for level, msg in logs if level == RNS.LOG_WARNING]
    assert len(warnings) == 1
    assert "redelivered " + str(threshold) + " times" in warnings[0]


def test_rejoin_retry_logs_resent_count(tmp_path):
    """The bounded rejoin replay logs how many held messages it resent."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "lost?", 0)
    msg.delivery = "sending"
    msg.mid = b"\x99" * 8
    msg.seq = 9001
    hub._pending_delivery[msg.mid] = (msg, time.monotonic() - DELIVERY_TIMEOUT_S - 1)
    hub.messages["general"].append(msg)
    hub._sweep_pending_delivery()
    assert msg.delivery == "failed"

    logs = []
    hub._log = lambda msg, level=None: logs.append((level, msg))
    _self_join(hub)
    hub._rejoin_retry_pass()

    assert any("rejoin retry resent 1 held message" in msg for _level, msg in logs)


def test_confirm_delivery_appends_sent_update(tmp_path):
    """The hub echo appends a sent update record to the history file.

    Own rows are first persisted while still sending, which loads back
    as failed. Without the update record every confirmed send renders
    as "not delivered to hub" after a restart.
    """
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "persist me")
    path = hub.manager._history_path(hub, "general")
    with open(path, "rb") as f:
        data = f.read()
    states = []
    pos = 0
    while pos < len(data):
        entry, pos = proto.decode_item(data, pos)
        if entry.get("id") == mid:
            states.append(entry.get("d"))
    assert states == ["sending", "sent"]


def test_history_reload_preserves_confirmed_delivery(tmp_path):
    """A delivered send must still read as sent after a restart."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "already confirmed")
    hub.messages["general"] = []
    hub._load_history()
    rows = [m for m in hub.messages["general"] if getattr(m, "mid", None) == mid]
    assert len(rows) == 1
    assert rows[0].delivery == "sent"


def test_history_reload_keeps_unconfirmed_failed(tmp_path):
    """A send with no update record still loads back as failed."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "echo lost", 0)
    msg.delivery = "sending"
    msg.mid = b"\xaa" * 8
    hub._append_history("general", msg)
    hub.messages["general"] = []
    hub._load_history()
    rows = [
        m for m in hub.messages["general"] if getattr(m, "mid", None) == b"\xaa" * 8
    ]
    assert len(rows) == 1
    assert rows[0].delivery == "failed"


def test_late_own_echo_restores_failed_delivery(tmp_path):
    """An echo landing after failure is proof of delivery, not a repeat."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "slow echo")
    row = [m for m in hub.messages["general"] if getattr(m, "mid", None) == mid][-1]
    row.delivery = "failed"
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x22" * 16,
        room="general",
        body="slow echo",
        mid=mid,
    )
    hub._handle_msg(env)
    assert row.delivery == "sent"
    assert getattr(row, "dup_count", 1) == 1


def test_extra_own_echo_still_counts_as_repeat(tmp_path):
    """A second echo on an already sent row is a genuine extra copy."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "echo twice")
    row = [m for m in hub.messages["general"] if getattr(m, "mid", None) == mid][-1]
    assert row.delivery == "sent"
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x22" * 16,
        room="general",
        body="echo twice",
        mid=mid,
    )
    hub._handle_msg(env)
    assert row.delivery == "sent"
    assert row.dup_count == 2


def test_seen_restores_failed_row(tmp_path):
    """A T_SEEN receipt flips a failed row back to sent."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "made it", 0)
    msg.delivery = "failed"
    msg.mid = b"\xab" * 8
    msg.seq = 9100
    hub.messages["general"].append(msg)
    env = proto.make_envelope(
        proto.T_SEEN,
        src=b"\x44" * 16,
        room="general",
        body=[b"\xab" * 8],
    )
    hub._handle_seen(env)
    assert msg.delivery == "sent"


def test_seen_ignores_unknown_mids(tmp_path):
    """Receipts for mids we never sent change nothing."""
    _server, hub = _loopback_client_hub(tmp_path)
    before = list(hub.messages["general"])
    env = proto.make_envelope(
        proto.T_SEEN,
        src=b"\x44" * 16,
        room="general",
        body=[b"\x00" * 8, "junk", b"\x01" * 8],
    )
    hub._handle_seen(env)
    assert hub.messages["general"] == before


def test_self_join_sends_sync_for_failed_mids(tmp_path):
    """A self-JOIN asks the hub which failed mids it already relayed."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "uncertain", 0)
    msg.delivery = "failed"
    msg.mid = b"\xcd" * 8
    msg.seq = 9102
    hub.messages["general"].append(msg)

    sent = []
    orig = hub._send_env

    def spy(env):
        sent.append(env)
        return orig(env)

    hub._send_env = spy
    _self_join(hub)
    sync = [e for e in sent if e.get(proto.K_T) == proto.T_SYNC]
    assert len(sync) == 1
    assert sync[0][proto.K_ROOM] == "general"
    assert sync[0][proto.K_BODY] == [b"\xcd" * 8]


def test_self_join_sends_no_sync_without_failed_rows(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    sent = []
    orig = hub._send_env

    def spy(env):
        sent.append(env)
        return orig(env)

    hub._send_env = spy
    _self_join(hub)
    assert [e for e in sent if e.get(proto.K_T) == proto.T_SYNC] == []


def test_seen_confirmed_row_is_not_retried_on_rejoin(tmp_path):
    """A resync-confirmed failed row must not be resent by the pass."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "made it", 0)
    msg.delivery = "failed"
    msg._auto_retryable = True
    msg.mid = b"\xef" * 8
    msg.seq = 9103
    hub.messages["general"].append(msg)

    sent = []
    orig = hub._send_env

    def spy(env):
        sent.append(env)
        return orig(env)

    hub._send_env = spy
    _self_join(hub)
    seen = proto.make_envelope(
        proto.T_SEEN,
        src=b"\x44" * 16,
        room="general",
        body=[b"\xef" * 8],
    )
    hub._handle_seen(seen)
    assert msg.delivery == "sent"
    hub._rejoin_retry_pass()
    assert [e for e in sent if e.get(proto.K_T) == proto.T_MSG] == []


def test_rejoin_retry_pass_skips_dead_link(tmp_path):
    """A pass firing after link loss must not burn the retry budget."""
    _server, hub = _loopback_client_hub(tmp_path)
    msg = proto.RRCMessage("msg", "general", b"\x22" * 16, "me", "lost?", 0)
    msg.delivery = "failed"
    msg._auto_retryable = True
    msg.mid = b"\x55" * 8
    msg.seq = 9104
    hub.messages["general"].append(msg)
    hub._rejoin_retry_rooms.add("general")
    link = hub.link
    hub.link = None
    calls = []
    orig = hub.retry_message
    hub.retry_message = lambda room, seq: calls.append(seq) or orig(room, seq)
    hub._rejoin_retry_pass()
    assert calls == []
    assert getattr(msg, "_auto_retried", False) is False
    hub.link = link
