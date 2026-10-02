# SPDX-License-Identifier: 0BSD

"""End-to-end RRC tests over the in-process loopback bridge.

These wire a real RRCHubServer to a real client RRCHub through
_LoopbackEndpoint so packets travel the actual encode/decode/route path
without needing Reticulum transport or sockets.
"""

import types

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub
from meshchatx.src.backend.rrc.server import RRCServerManager
from tests.backend.test_rrc_protocol import make_manager


def _wait_for(predicate, timeout=5.0):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def _make_server(tmp_path, name="Live Hub", greeting=None):
    sm = RRCServerManager(str(tmp_path / "srv"))
    server = sm.create_hub(
        name=name,
        greeting=greeting,
        announce=False,
        enabled=False,
    )
    # RNS.Destination requires a running Reticulum, but the loopback bridge
    # only needs the destination hash for find_local_server matching.
    server.destination = types.SimpleNamespace(hash=b"\x99" * 16)
    server.running = True
    return sm, server


def _make_client(tmp_path, server):
    manager = make_manager(tmp_path / "cli", nickname="alice")
    manager.set_server_manager(server.manager)
    return manager, manager.add_hub(server.dest_hash)


@pytest.fixture
def live_pair(tmp_path):
    _sm, server = _make_server(
        tmp_path, name="Live Hub", greeting="welcome to the live hub"
    )
    server.rooms.register_room("lobby", topic="the lobby")
    _manager, hub = _make_client(tmp_path, server)
    yield server, hub
    hub.disconnect()
    server.stop()


def test_loopback_welcome_room_list_and_motd(live_pair):
    """HELLO to WELCOME to auto /list to MOTD over the real wire path."""
    _server, hub = live_pair
    hub.connect()

    assert _wait_for(lambda: hub.welcomed)
    assert _wait_for(lambda: hub.status == RRCHub.STATUS_CONNECTED)
    assert hub.hub_name == "Live Hub"
    assert _wait_for(lambda: hub.available_rooms == {"lobby": "the lobby"})
    assert _wait_for(lambda: hub.motd == "welcome to the live hub")


def test_loopback_join_send_relay(live_pair):
    """Join a room and relay a message back over the real link."""
    server, hub = live_pair
    hub.connect()
    assert _wait_for(lambda: hub.welcomed)

    hub.join_room("lobby")
    assert _wait_for(lambda: "lobby" in hub.rooms)

    hub.send_message("lobby", "hello mesh")
    assert _wait_for(
        lambda: any(
            m.text == "hello mesh" and m.kind == "msg"
            for m in hub.get_messages("lobby")
        )
    )
    assert _wait_for(lambda: server._stats["messages_relayed"] >= 1)


def test_loopback_foreign_dest_hash_src_accepted(live_pair, monkeypatch):
    """Notices stamped with the destination hash still drive client state.

    A foreign hub implementation may stamp src with its destination hash
    instead of the identity hash. Regression coverage for the is_hub_src
    gate added in c8b465de.
    """
    server, hub = live_pair

    # Rewrite the src stamp on every server->client packet so it carries the
    # destination hash like a foreign implementation would. Decoded, edited,
    # and re-encoded so the client parses real wire bytes.
    real_send = server._send_payload

    def foreign_src_send(link, payload):
        try:
            env = proto.decode(payload)
            if env.get(proto.K_SRC) == bytes(server.identity.hash):
                env[proto.K_SRC] = bytes(server.dest_hash)
                payload = proto.encode(env)
        except Exception:
            pass
        real_send(link, payload)

    monkeypatch.setattr(server, "_send_payload", foreign_src_send)

    hub.connect()
    assert _wait_for(lambda: hub.welcomed)
    assert _wait_for(lambda: hub.available_rooms == {"lobby": "the lobby"})
    assert _wait_for(lambda: hub.motd == "welcome to the live hub")


def test_loopback_disconnect_reconnect(live_pair):
    """Link teardown and reconnect both stay healthy over loopback."""
    _server, hub = live_pair
    hub.connect()
    assert _wait_for(lambda: hub.welcomed)

    hub.disconnect()
    assert _wait_for(lambda: hub.status == RRCHub.STATUS_DISCONNECTED)

    hub.connect()
    assert _wait_for(lambda: hub.status == RRCHub.STATUS_CONNECTED)
