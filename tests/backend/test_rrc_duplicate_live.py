# SPDX-License-Identifier: 0BSD

"""Live loopback coverage for RRC repeat counting and replay suppression.

These tests drive the real hub server packet path end to end: a second
session sends a message, the server fans it out over the loopback link,
and redeliveries, reconnects, and restarts must fold into one row with a
repeat count instead of spamming the room. They pin the exact failure
mode RCC operators reported: a client that reposts held envelopes after
a restart.
"""

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint
from tests.backend.test_rrc_protocol import FakeIdentity
from tests.backend.test_rrc_server import (
    FakeLink,
    FakeServerManager,
    _loopback_client_hub,
    add_session,
)

DAVE = b"\x07" * 16
OWN = b"\x22" * 16
ROOM = "general"


def _dave_session(server, room=ROOM):
    link = FakeLink(FakeIdentity(DAVE))
    sess = add_session(server, link, DAVE, nick="dave")
    server._on_packet(
        link,
        proto.encode(
            proto.make_envelope(proto.T_JOIN, src=DAVE, room=room),
        ),
    )
    return link, sess


def _dave_say(server, link, text, room=ROOM):
    """Send a message from dave through the full server packet path."""
    env = proto.make_envelope(
        proto.T_MSG,
        src=DAVE,
        room=room,
        nick="dave",
        body=text,
    )
    payload = proto.encode(env)
    server._on_packet(link, payload)
    return payload


def _rows(hub, text):
    return [m for m in hub.get_messages(ROOM) if m.text == text]


def _reconnect_client(tmp_path, server, hub):
    """Rebuild a client manager from disk and relink it to the server."""
    manager = RRCManager(identity=FakeIdentity(OWN), storage_dir=str(tmp_path))
    manager.set_server_manager(FakeServerManager([server]))
    manager.load()
    loaded_hub = manager.hubs[0]
    link = _LoopbackEndpoint(loaded_hub, server)
    server._attach_loopback(link, manager.identity)
    loaded_hub._hub_identity_hash = server.identity.hash
    loaded_hub.link = link
    loaded_hub._send_hello(link)
    assert loaded_hub.welcomed is True
    manager.set_active(loaded_hub, ROOM)
    loaded_hub.join_room(ROOM, silent=True)
    return manager, loaded_hub


def test_live_redeliveries_fold_into_repeat_count(tmp_path):
    server, hub = _loopback_client_hub(tmp_path)
    dave_link, _ = _dave_session(server)

    payload = _dave_say(server, dave_link, "live hello")
    rows = _rows(hub, "live hello")
    assert len(rows) == 1
    assert rows[0].dup_count == 1

    # The hub holds envelopes and replays them. Each replay carries the
    # original mid, so the live path must fold it into the same row.
    server._on_packet(dave_link, payload)
    server._on_packet(dave_link, payload)
    rows = _rows(hub, "live hello")
    assert len(rows) == 1
    assert rows[0].dup_count == 3
    assert rows[0].to_dict()["dup_count"] == 3


def test_live_replay_after_restart_counts_without_new_rows(tmp_path):
    server, hub = _loopback_client_hub(tmp_path)
    dave_link, _ = _dave_session(server)

    payload = _dave_say(server, dave_link, "restart replay")
    assert len(_rows(hub, "restart replay")) == 1

    _, loaded_hub = _reconnect_client(tmp_path, server, hub)
    assert len(_rows(loaded_hub, "restart replay")) == 1

    # The hub replays the held envelope to the restarted client. This is
    # the reported spam path: it must count, not repost.
    server._on_packet(dave_link, payload)
    rows = _rows(loaded_hub, "restart replay")
    assert len(rows) == 1
    assert rows[0].dup_count == 2


def test_live_own_echo_redelivery_counts_on_sender_row(tmp_path):
    server, hub = _loopback_client_hub(tmp_path)
    mid = hub.send_message(ROOM, "mine")
    own = _rows(hub, "mine")[-1]
    assert own.delivery == "sent"

    # The hub relays our own message back again after delivery already
    # confirmed. The extra copy must show on our row, not as a new line.
    server._on_packet(
        hub.link,
        proto.encode(
            proto.make_envelope(
                proto.T_MSG,
                src=OWN,
                room=ROOM,
                body="mine",
                mid=mid,
            ),
        ),
    )
    rows = _rows(hub, "mine")
    assert len(rows) == 1
    assert rows[0].dup_count == 2
    assert rows[0].delivery == "sent"
