# SPDX-License-Identifier: 0BSD

"""Wire-level invariants for the RRC client.

A client bug once reposted delivered history to every hub on restart,
which spammed RCC rooms for every other client on the network. These
tests record every chat envelope the client puts on the wire and assert
the rules that keep it well behaved:

- restarts are silent, history rows are never replayed
- retries are idempotent and reuse the original envelope id
- every chat envelope spends a send budget token
- no session exceeds the hub's advertised send budget

RNS link payloads are encrypted, so packet captures cannot assert any of
this. The loopback wire recorder here is the layer where content and
counts are actually observable.
"""

import random
import time

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import (
    DELIVERY_TIMEOUT_S,
    RateLimitedError,
    RRCManager,
)
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint
from tests.backend.test_rrc_protocol import FakeIdentity
from tests.backend.test_rrc_server import (
    FakeServerManager,
    _loopback_client_hub,
)


class WireLog:
    """Records chat envelopes a client hub puts on the wire.

    Also counts budget spends so tests can assert that no code path
    bypasses the send budget.
    """

    CHAT_KINDS = (proto.T_MSG, proto.T_ACTION, proto.T_NOTICE)

    def __init__(self, hub):
        self.entries = []
        self.budget_takes = 0
        self._hub = hub
        self._orig_send = hub._send_env
        self._orig_take = hub._take_send_budget

        def recording_send(env):
            if env.get(proto.K_T) in self.CHAT_KINDS:
                self.entries.append(
                    {
                        "t": env.get(proto.K_T),
                        "mid": bytes(env.get(proto.K_ID) or b""),
                        "room": env.get(proto.K_ROOM),
                        "body": env.get(proto.K_BODY),
                    },
                )
            return self._orig_send(env)

        def recording_take():
            self.budget_takes += 1
            return self._orig_take()

        hub._send_env = recording_send
        hub._take_send_budget = recording_take

    def mids(self):
        return [e["mid"] for e in self.entries]

    def clear(self):
        self.entries.clear()
        self.budget_takes = 0


def _self_join(hub, room="general"):
    hub._pending_joins.add(room)
    env = proto.make_envelope(
        proto.T_JOINED, src=b"\x44" * 16, room=room, body=[b"\x22" * 16]
    )
    hub._handle_joined(env)


def _restart_client(tmp_path, server):
    """Rebuild a client manager from disk and relink it to the server.

    The wire recorder is attached before the first envelope of the new
    session so every byte of the reconnect is observable.
    """
    manager = RRCManager(identity=FakeIdentity(b"\x22" * 16), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))
    manager.load()
    loaded = manager.hubs[0]
    log = WireLog(loaded)
    link = _LoopbackEndpoint(loaded, server)
    server._attach_loopback(link, manager.identity)
    loaded._hub_identity_hash = server.identity.hash
    loaded.link = link
    loaded._send_hello(link)
    assert loaded.welcomed is True
    manager.set_active(loaded, "general")
    loaded.join_room("general", silent=True)
    return loaded, log


def test_restart_replays_nothing_on_the_wire(tmp_path):
    server, hub = _loopback_client_hub(tmp_path)
    hub.send_message("general", "hello once")
    assert len(server._message_log) == 1

    _loaded, log = _restart_client(tmp_path, server)

    # The room still holds the row as a replay candidate, yet the whole
    # reconnect emitted no message content. The only body on the wire is
    # the deliberate room-list request, sent exactly once.
    assert any(m.text == "hello once" for m in _loaded.get_messages("general"))
    bodies = [e["body"] for e in log.entries]
    assert [b for b in bodies if not str(b).startswith("/")] == []
    assert bodies.count("/list") == 1
    assert len(server._message_log) == 1


def test_in_session_retry_is_bounded_and_idempotent(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    log = WireLog(hub)

    mid = hub.send_message("general", "retry me")
    own = [m for m in hub.messages["general"] if m.text == "retry me"][-1]
    # Link loss before the echo confirmed: force-fail the pending send.
    hub._pending_delivery.clear()
    own.delivery = "failed"
    own._auto_retryable = True

    _self_join(hub)
    _self_join(hub)

    # Original plus exactly one retry, and the retry reuses the mid.
    assert log.mids() == [mid, mid]
    assert own.delivery == "sent"


def test_flap_retry_emits_one_copy_with_original_mid(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message("general", "flap")
    own = [m for m in hub.messages["general"] if m.text == "flap"][-1]

    # Re-arm the pending send and drop the link like _on_closed does.
    own.delivery = "sending"
    hub._pending_delivery[mid] = (own, time.monotonic())
    hub._flush_pending_delivery_locked()
    assert own.delivery == "failed"

    log = WireLog(hub)
    _self_join(hub)
    assert log.mids() == [mid]
    assert own.delivery == "sent"


def test_every_wire_envelope_spends_a_budget_token(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    log = WireLog(hub)

    hub.send_message("general", "one")
    hub.send_action("general", "waves")
    hub.send_command("/list", room="general")
    own = [m for m in hub.messages["general"] if m.text == "one"][-1]
    own.delivery = "failed"
    own._auto_retryable = True
    hub._pending_delivery.clear()
    _self_join(hub)

    assert len(log.entries) == 4
    assert log.budget_takes == len(log.entries)


def test_session_never_exceeds_advertised_budget(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    hub.rate_limit_msgs_per_minute = 3
    hub._send_budget_tokens = 3.0
    hub._send_budget_last = time.monotonic()
    log = WireLog(hub)

    sent = 0
    for i in range(10):
        try:
            hub.send_message("general", "m" + str(i))
            sent += 1
        except RateLimitedError:
            pass

    assert sent == 3
    assert len(log.entries) == 3


def test_seeded_restart_and_flap_soak(tmp_path):
    """Seeded chaos: restarts, flaps, and rejoins must never amplify."""
    rng = random.Random(20261009)
    server, hub = _loopback_client_hub(tmp_path)
    hub.rate_limit_msgs_per_minute = 8
    hub._send_budget_tokens = 8.0
    hub._send_budget_last = time.monotonic()
    log = WireLog(hub)
    per_mid = {}

    for step in range(12):
        action = rng.choice(["send", "fail", "rejoin", "restart"])
        if action == "send":
            try:
                hub.send_message("general", f"step{step}")
            except RateLimitedError:
                pass
        elif action == "fail":
            # Drop the link like a real close: pending sends become failed.
            hub._flush_pending_delivery_locked()
        elif action == "rejoin":
            log.clear()
            _self_join(hub)
            # Auto-retry is one-shot per message per session.
            mids = log.mids()
            assert len(mids) == len(set(mids))
            # Every retry spent a budget token.
            assert log.budget_takes == len(log.entries)
        elif action == "restart":
            hub, restart_log = _restart_client(tmp_path, server)
            # Restart replay is silent: nothing but the room-list request.
            assert [
                e for e in restart_log.entries if not str(e["body"]).startswith("/")
            ] == []
            hub.rate_limit_msgs_per_minute = 8
            hub._send_budget_tokens = 8.0
            hub._send_budget_last = time.monotonic()
            log = WireLog(hub)
            _self_join(hub)
            assert log.entries == []
        for entry in log.entries:
            per_mid[entry["mid"]] = per_mid.get(entry["mid"], 0) + 1
        log.clear()

    # No message is ever put on the wire more than twice (original + one
    # in-session retry), across any number of restarts and flaps.
    assert per_mid, "soak must have sent at least one message"
    assert max(per_mid.values()) <= 2


def test_delivery_timeout_sweep_then_retry_is_bounded(tmp_path):
    _server, hub = _loopback_client_hub(tmp_path)
    log = WireLog(hub)

    mid = hub.send_message("general", "slow")
    own = [m for m in hub.messages["general"] if m.text == "slow"][-1]
    hub._pending_delivery[mid] = (own, time.monotonic() - DELIVERY_TIMEOUT_S - 1)
    hub._sweep_pending_delivery()
    assert own.delivery == "failed"

    _self_join(hub)
    _self_join(hub)
    assert log.mids() == [mid, mid]
