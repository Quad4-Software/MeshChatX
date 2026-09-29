# SPDX-License-Identifier: 0BSD

"""Own-message delivery state: pending, echo-confirmed, failed, retry."""

import time

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import DELIVERY_TIMEOUT_S, RRCHub
from tests.backend.test_rrc_server import FakeManager, _loopback_client_hub


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
    assert not hub._pending_delivery


def test_retry_failed_message_resends(tmp_path):
    """Retry re-sends the body under a new mid and re-pends the echo."""
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "retry me")
    own = [m for m in hub.messages["general"] if m.text == "retry me"][-1]
    # Simulate hub never echoing: force-fail the entry.
    own.delivery = "failed"
    new_mid = hub.retry_message("general", own.seq)
    assert isinstance(new_mid, bytes)
    assert new_mid != mid
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
    msg.delivery = "failed"
    msg.seq = 9001
    hub.messages["general"].append(msg)

    hub._pending_joins.add("general")  # self-join marker set by join_room
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room="general", body=[b"\x22" * 16]
    )
    hub._handle_joined(env)
    assert msg.delivery == "sent"  # loopback echo confirmed the retry

    # A second JOINED must not resend; the one-shot flag is set.
    own_mid = msg.mid
    hub._pending_joins.add("general")
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room="general", body=[b"\x22" * 16]
    )
    hub._handle_joined(env)
    assert msg.mid == own_mid


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
