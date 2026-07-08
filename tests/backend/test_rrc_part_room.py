# SPDX-License-Identifier: 0BSD

"""Regression test: leaving a connected RRC room must drop it from the
known-rooms list.

`RRCHub.ordered_known_rooms()` treats any room with an entry in
`self.messages` as "known", even if it was never joined. `part_room()`
(used for a connected hub) previously only discarded the room from
`self.rooms`, leaving its `messages` entry (and unread/member state)
behind, so the room kept reappearing in the sidebar after leaving it.
"""

from meshchatx.src.backend.rrc.manager import RRCHub


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeManager:
    def __init__(self):
        self.changes = 0
        self.identity = FakeIdentity(b"\x11" * 16)

    def _notify_change(self, hub=None):
        self.changes += 1

    def save(self):
        pass

    def _history_path(self, hub, room):
        return ""

    def _ensure_history_dir(self, hub):
        pass


HUB_HASH = bytes(range(16))


def make_hub():
    return RRCHub(FakeManager(), HUB_HASH, name="Hub")


def test_part_room_removes_room_from_known_rooms():
    hub = make_hub()
    hub.status = RRCHub.STATUS_CONNECTED
    hub.rooms.add("lobby")
    hub.messages["lobby"] = []
    hub.unread_rooms.add("lobby")
    hub.unread_counts["lobby"] = 3
    hub.members["lobby"] = {b"\x01" * 16}

    assert "lobby" in hub.ordered_known_rooms()

    hub.part_room("lobby")

    assert "lobby" not in hub.ordered_known_rooms()
    assert "lobby" not in hub.messages
    assert "lobby" not in hub.unread_rooms
    assert "lobby" not in hub.unread_counts
    assert "lobby" not in hub.members


def test_part_room_notifies_manager_of_change():
    hub = make_hub()
    hub.status = RRCHub.STATUS_CONNECTED
    hub.rooms.add("general")
    hub.messages["general"] = []

    hub.part_room("general")

    assert hub.manager.changes >= 1
