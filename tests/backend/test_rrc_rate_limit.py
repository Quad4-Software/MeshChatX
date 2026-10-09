# SPDX-License-Identifier: 0BSD

"""Rate limit behavior for RRC hubs and clients.

Hubs advertise rate_limit_msgs_per_minute in WELCOME and enforce it on
inbound chat envelopes. Clients keep a matching local budget so sends and
auto-retries never trip hub-side enforcement, and operators can set the
per-hub limit from the hosted hub settings.
"""

import time

import pytest

import meshchatx.src.backend.rrc.manager as rrc_manager
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RateLimitedError, RRCHub, RRCManager
from meshchatx.src.backend.rrc.server import (
    MAX_RATE_LIMIT_MSGS_PER_MINUTE,
    RRCHubServer,
    RRCServerManager,
    _LoopbackEndpoint,
    normalize_rate_limit_msgs_per_minute,
)
from tests.backend.test_rrc_protocol import FakeIdentity
from tests.backend.test_rrc_server import (
    HUB_HASH,
    FakeLink,
    FakeManager,
    FakeServerManager,
    _load_with_fake_identity,
    _loopback_client_hub,
    add_session,
    make_running_server,
    route,
)


class _Mgr(FakeManager):
    def get_nickname(self):
        return "me"


class _Clock:
    def __init__(self, start=1000.0):
        self.now = float(start)

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


def _hub(limit=None):
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    if limit is not None:
        hub.rate_limit_msgs_per_minute = limit
        hub._send_budget_tokens = float(max(1, limit))
        hub._send_budget_last = time.monotonic()
    return hub


def _loopback_with_limit(tmp_path, limit):
    """Loopback client connected to a hub advertising the given limit."""
    server = make_running_server()
    server.register_room("general")
    server.rate_limit_msgs_per_minute = limit
    manager = RRCManager(identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))
    hub = manager.add_hub(server.dest_hash)
    hub.auto_list = False
    hub.auto_who = False
    link = _LoopbackEndpoint(hub, server)
    server._attach_loopback(link, manager.identity)
    hub._hub_identity_hash = server.identity.hash
    hub.link = link
    hub._send_hello(link)
    assert hub.welcomed is True
    manager.set_active(hub, "general")
    hub.join_room("general", silent=True)
    return server, hub


def _self_join(hub, room="general"):
    hub._pending_joins.add(room)
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room=room, body=[b"\x22" * 16]
    )
    hub._handle_joined(env)


def test_send_budget_capacity_defaults_and_clamps():
    hub = RRCHub(_Mgr(), b"\x33" * 16, name="hub")
    assert hub._send_budget_capacity() == float(proto.DEFAULT_RATE_PER_MINUTE)
    hub.rate_limit_msgs_per_minute = 0
    assert hub._send_budget_capacity() == 1.0
    hub.rate_limit_msgs_per_minute = -12
    assert hub._send_budget_capacity() == 1.0
    hub.rate_limit_msgs_per_minute = "junk"
    assert hub._send_budget_capacity() == float(proto.DEFAULT_RATE_PER_MINUTE)


def test_take_refill_and_retry_after(monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(rrc_manager.time, "monotonic", clock.monotonic)
    hub = _hub(60)
    hub._send_budget_last = clock.monotonic()

    for _ in range(60):
        hub._take_send_budget()
    with pytest.raises(RateLimitedError) as excinfo:
        hub._take_send_budget()
    assert excinfo.value.retry_after == pytest.approx(1.0, abs=0.05)

    clock.advance(30)
    for _ in range(30):
        hub._take_send_budget()
    with pytest.raises(RateLimitedError):
        hub._take_send_budget()

    clock.advance(600)
    hub._refill_send_budget()
    assert hub._send_budget_tokens == 60.0
    hub._take_send_budget()
    assert hub._send_budget_tokens == pytest.approx(59.0)


def test_failed_send_refunds_budget():
    hub = _hub(1)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            hub.send_message("general", "no link")
    # Every failed attempt refunded its token; the budget is still spendable.
    hub._take_send_budget()


def test_rate_limited_send_leaves_no_pending_or_row(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    hub.rate_limit_msgs_per_minute = 1
    hub._send_budget_tokens = 1.0
    hub._send_budget_last = time.monotonic()

    mid = hub.send_message("general", "first")
    assert isinstance(mid, bytes)
    with pytest.raises(RateLimitedError):
        hub.send_message("general", "second")
    assert all(m.text != "second" for m in hub.get_messages("general"))
    assert not hub._pending_delivery


def test_welcome_limit_applies_to_budget(tmp_path):
    _server, hub = _loopback_with_limit(tmp_path, 3)
    assert hub.rate_limit_msgs_per_minute == 3
    assert hub._send_budget_tokens == pytest.approx(3.0)
    for i in range(3):
        hub.send_message("general", "m" + str(i))
    with pytest.raises(RateLimitedError):
        hub.send_message("general", "overflow")


def test_commands_count_against_budget(tmp_path):
    _server, hub = _loopback_with_limit(tmp_path, 2)
    hub.send_command("/list", room="general")
    hub.send_message("general", "hello")
    with pytest.raises(RateLimitedError):
        hub.send_message("general", "overflow")


def test_auto_retry_stops_at_budget_and_resumes(tmp_path, monkeypatch):
    clock = _Clock()
    monkeypatch.setattr(rrc_manager.time, "monotonic", clock.monotonic)
    _server, hub = _loopback_client_hub(tmp_path)
    hub.rate_limit_msgs_per_minute = 1
    hub._send_budget_tokens = 1.0
    hub._send_budget_last = clock.monotonic()

    msgs = []
    for i in range(3):
        msg = proto.RRCMessage(
            "msg", "general", b"\x22" * 16, "me", "lost" + str(i), proto.now_ms()
        )
        msg.delivery = "sending"
        msg.mid = bytes([0x40 + i]) * 8
        msg.seq = 9000 + i
        hub._pending_delivery[msg.mid] = (
            msg,
            clock.monotonic() - rrc_manager.DELIVERY_TIMEOUT_S - 1,
        )
        hub.messages["general"].append(msg)
        msgs.append(msg)
    hub._sweep_pending_delivery()
    assert all(m.delivery == "failed" for m in msgs)

    _self_join(hub)
    assert sum(1 for m in msgs if m.delivery == "sent") == 1
    assert sum(1 for m in msgs if m.delivery == "failed") == 2

    # The budget refills after a minute; the next rejoin sends one more.
    clock.advance(61)
    _self_join(hub)
    assert sum(1 for m in msgs if m.delivery == "sent") == 2
    assert sum(1 for m in msgs if m.delivery == "failed") == 1


def test_reconnect_resets_budget_for_new_limit():
    hub = _hub(60)
    hub._take_send_budget()
    assert hub._send_budget_tokens == pytest.approx(59.0)
    hub._apply_limits({proto.L_RATE_LIMIT_MSGS_PER_MINUTE: 5})
    assert hub.rate_limit_msgs_per_minute == 5
    assert hub._send_budget_tokens == pytest.approx(5.0)


def test_normalize_rate_limit_clamps():
    assert normalize_rate_limit_msgs_per_minute(None) == proto.DEFAULT_RATE_PER_MINUTE
    assert normalize_rate_limit_msgs_per_minute(0) == 1
    assert normalize_rate_limit_msgs_per_minute(-5) == 1
    assert normalize_rate_limit_msgs_per_minute(30) == 30
    assert (
        normalize_rate_limit_msgs_per_minute(999999) == MAX_RATE_LIMIT_MSGS_PER_MINUTE
    )
    assert normalize_rate_limit_msgs_per_minute("junk") == proto.DEFAULT_RATE_PER_MINUTE
    assert normalize_rate_limit_msgs_per_minute("42") == 42


def test_hub_config_roundtrips_rate_limit(tmp_path):
    manager = RRCServerManager(storage_dir=str(tmp_path))
    hub = RRCHubServer(
        manager,
        FakeIdentity(HUB_HASH),
        name="Limited Hub",
        rate_limit_msgs_per_minute=30,
    )
    hub.configure_storage(str(manager._hub_dir(HUB_HASH.hex())))
    manager.hubs.append(hub)
    manager.save()

    store = tmp_path / "rrc_server" / "hubs"
    obj = proto.decode(store.read_bytes())
    assert obj["hubs"][0]["rate_limit_msgs_per_minute"] == 30
    assert hub.to_dict()["rate_limit_msgs_per_minute"] == 30

    # _load_entry requires the identity file on disk; content is replaced
    # by the fake identity patch.
    (tmp_path / "rrc_server" / (HUB_HASH.hex() + ".identity")).write_bytes(b"\x00" * 64)
    reloaded = RRCServerManager(storage_dir=str(tmp_path))
    _load_with_fake_identity(reloaded)
    loaded_hub = reloaded.find_hub(HUB_HASH.hex())
    assert loaded_hub is not None
    assert loaded_hub.rate_limit_msgs_per_minute == 30


def test_update_hub_clamps_rate_limit(tmp_path):
    manager = RRCServerManager(storage_dir=str(tmp_path))
    hub = RRCHubServer(manager, FakeIdentity(HUB_HASH), name="Hub")
    hub.configure_storage(str(manager._hub_dir(HUB_HASH.hex())))
    manager.hubs.append(hub)

    assert manager.update_hub(HUB_HASH.hex(), rate_limit_msgs_per_minute=0) is True
    assert hub.rate_limit_msgs_per_minute == 1
    manager.update_hub(HUB_HASH.hex(), rate_limit_msgs_per_minute=999999)
    assert hub.rate_limit_msgs_per_minute == MAX_RATE_LIMIT_MSGS_PER_MINUTE
    manager.update_hub(HUB_HASH.hex(), rate_limit_msgs_per_minute=45)
    assert hub.rate_limit_msgs_per_minute == 45
    # Unknown hub: no change, no error.
    assert manager.update_hub("00" * 16, rate_limit_msgs_per_minute=30) is False


def test_welcome_advertises_configured_rate_limit():
    server = RRCHubServer(
        FakeManager(),
        FakeIdentity(HUB_HASH),
        name="Limited",
        rate_limit_msgs_per_minute=42,
    )
    link = FakeLink(FakeIdentity(b"peer-bbbbbbbbbbbb"))
    sess = add_session(server, link, link._identity.hash, welcomed=False)

    env = proto.make_envelope(proto.T_HELLO, src=link._identity.hash, nick="bob")
    out = route(server, link, sess, env)

    welcome = out[0][1]
    limits = welcome[proto.K_BODY][proto.B_WELCOME_LIMITS]
    assert limits[proto.L_RATE_LIMIT_MSGS_PER_MINUTE] == 42
