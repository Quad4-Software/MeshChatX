# SPDX-License-Identifier: 0BSD

"""History load must apply the per-room cap after filtering.

The room history file holds every record the hub wrote: chat rows,
system join/part lines, and delivery update rows. The cap is meant to
bound the messages a room keeps, not the raw record count, so a busy
room full of system rows must not starve real chat history on reload.
"""

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager
from tests.backend.test_rrc_protocol import FakeIdentity


def _write_history(tmp_path, real_count, system_count):
    manager = RRCManager(
        identity=FakeIdentity(b"\x22" * 16),
        storage_dir=str(tmp_path),
        history_per_room_cap=0,
    )
    hub = manager.add_hub(b"\xaa" * 16, name="test")
    hub.add_room("general")
    for i in range(max(real_count, system_count)):
        if i < real_count:
            msg = proto.RRCMessage(
                "msg", "general", b"\x33" * 16, "peer", f"real-{i}", 1000 + i
            )
            hub._record_message(msg)
        if i < system_count:
            hub._record_system("general", f"sys-{i}", event="join")
    return hub


def _reload(tmp_path, cap=None):
    kwargs = {}
    if cap is not None:
        kwargs["history_per_room_cap"] = cap
    manager = RRCManager(
        identity=FakeIdentity(b"\x22" * 16),
        storage_dir=str(tmp_path),
        **kwargs,
    )
    manager.load()
    assert len(manager.hubs) == 1
    return manager.hubs[0]


def test_cap_applies_after_system_rows_are_filtered(tmp_path):
    _write_history(tmp_path, real_count=300, system_count=300)

    hub = _reload(tmp_path, cap=100)
    msgs = hub.get_messages("general")

    assert len(msgs) == 100
    assert all(m.kind == "msg" for m in msgs)
    assert [m.text for m in msgs] == [f"real-{i}" for i in range(200, 300)]
    seqs = [m.seq for m in msgs]
    assert seqs == sorted(seqs)


def test_default_cap_keeps_full_real_history(tmp_path):
    _write_history(tmp_path, real_count=600, system_count=700)

    hub = _reload(tmp_path)
    msgs = hub.get_messages("general")

    assert len(msgs) == 600
    assert all(m.kind == "msg" for m in msgs)
    assert [m.text for m in msgs] == [f"real-{i}" for i in range(600)]


def test_byte_cap_trims_oversized_room_buffer(tmp_path):
    """Count caps alone cannot bound memory when bodies are large.

    A hub may advertise max_msg_body_bytes up to the protocol ceiling, so
    history_per_room_cap * body-size can reach tens of GB. The in-memory
    buffer must also honor the same byte bound as the history file.
    """
    manager = RRCManager(
        identity=FakeIdentity(b"\x22" * 16),
        storage_dir=str(tmp_path),
        history_per_room_cap=0,
    )
    hub = manager.add_hub(b"\xaa" * 16, name="test")
    hub.add_room("general")
    big = "x" * (1024 * 1024)
    for i in range(10):
        hub._record_message(
            proto.RRCMessage(
                "msg", "general", b"\x33" * 16, "peer", big + str(i), 1000 + i
            )
        )

    buf = hub.messages["general"]
    assert len(buf) <= 8
    assert buf[-1].text.endswith("9")
    assert hub._room_bytes["general"] <= hub.HISTORY_FILE_MAX_BYTES
    assert hub._room_bytes["general"] == sum(hub._msg_buf_size(m) for m in buf)


def test_byte_cap_counts_utf8_bytes(tmp_path):
    manager = RRCManager(
        identity=FakeIdentity(b"\x22" * 16),
        storage_dir=str(tmp_path),
        history_per_room_cap=0,
    )
    hub = manager.add_hub(b"\xaa" * 16, name="test")
    hub.add_room("general")
    # Each character is two UTF-8 bytes; char count alone would undercount.
    text = "é" * (4 * 1024 * 1024)
    for i in range(3):
        hub._record_message(
            proto.RRCMessage(
                "msg", "general", b"\x33" * 16, "peer", f"{text}-{i}", 1000 + i
            )
        )

    buf = hub.messages["general"]
    # Each record alone exceeds the byte cap, so only the newest survives.
    assert len(buf) == 1
    assert buf[0].text.endswith("-2")
    assert hub._room_bytes["general"] == sum(hub._msg_buf_size(m) for m in buf)


def test_notice_buffer_byte_cap(tmp_path):
    manager = RRCManager(
        identity=FakeIdentity(b"\x22" * 16),
        storage_dir=str(tmp_path),
        history_per_room_cap=0,
    )
    hub = manager.add_hub(b"\xaa" * 16, name="test")
    hub.add_room("general")
    big = "y" * (4 * 1024 * 1024)
    for i in range(4):
        hub._record_notice(
            proto.RRCMessage(
                "notice", "general", b"\x33" * 16, "peer", big + str(i), 1000 + i
            )
        )

    assert hub._notice_bytes <= hub.HISTORY_FILE_MAX_BYTES
    assert hub._notice_bytes == sum(hub._msg_buf_size(m) for m in hub.notices)
    assert len(hub.notices) <= 200
