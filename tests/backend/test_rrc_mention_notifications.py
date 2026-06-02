# SPDX-License-Identifier: 0BSD

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager
from tests.backend.test_rrc_protocol import FakeIdentity, make_manager


class FakeMisc:
    def __init__(self):
        self.dismissed = []
        self.added = []

    def dismiss_unviewed_notifications(self, notification_type=None, remote_hash=None):
        self.dismissed.append((notification_type, remote_hash))

    def add_notification(self, notification_type, remote_hash, title, content):
        self.added.append((notification_type, remote_hash, title, content))


class FakeDatabase:
    def __init__(self):
        self.misc = FakeMisc()


class FakeContext:
    def __init__(self):
        self.database = FakeDatabase()


def test_maybe_add_rrc_mention_notification():
    manager = RRCManager(
        identity=FakeIdentity(),
        storage_dir="/tmp/rrc-mention-test",
        get_nickname=lambda: "alice",
    )
    hub = manager.add_hub(bytes(range(16)))
    hub.name = "Test Hub"
    ctx = FakeContext()
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app.current_context = ctx

    msg = proto.RRCMessage(
        "msg", "lobby", b"\x20" * 16, "carol", "hey @alice", proto.now_ms()
    )
    msg.mention = True

    app._maybe_add_rrc_mention_notification(hub, msg, context=ctx)

    assert len(ctx.database.misc.dismissed) == 1
    assert ctx.database.misc.dismissed[0][0] == "rrc_mention"
    assert ctx.database.misc.dismissed[0][1] == f"{hub.hub_hash.hex()}:lobby"
    assert len(ctx.database.misc.added) == 1
    assert ctx.database.misc.added[0][0] == "rrc_mention"
    assert "lobby" in ctx.database.misc.added[0][2]
    assert "carol" in ctx.database.misc.added[0][3]


def test_hub_mention_tracks_room(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    env = proto.make_envelope(
        proto.T_MSG,
        src=b"\x20" * 16,
        room="lobby",
        body="ping @alice",
        nick="carol",
    )
    hub._on_packet(proto.encode(env))
    messages = hub.get_messages("lobby")
    assert messages[0].mention is True
    assert "lobby" in hub.mention_rooms
