# SPDX-License-Identifier: 0BSD

"""Resource-delivered notices must populate room lists like normal notices."""

import io

import RNS

from meshchatx.src.backend.rrc import protocol as proto
from tests.backend.test_rrc_protocol import make_manager


class FakeResource:
    def __init__(self, data):
        self.status = RNS.Resource.COMPLETE
        self.data = io.BytesIO(data)


def _expect_notice(hub, payload):
    with hub._lock:
        hub._resource_expectations[b"\x01" * 8] = {
            "kind": proto.RES_KIND_NOTICE,
            "size": len(payload),
            "sha256": None,
            "encoding": "utf-8",
            "room": None,
            "expires": 1e18,
        }


def test_resource_notice_populates_room_list(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))

    body = b"Registered public rooms:\n  lobby - the lobby\n  dev"
    _expect_notice(hub, body)
    hub._resource_concluded(FakeResource(body))

    assert hub.available_rooms == {"lobby": "the lobby", "dev": None}


def test_resource_notice_consumes_silent_list_pending(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    hub._silent_list_pending = 1

    body = b"Registered public rooms:\n  lobby"
    _expect_notice(hub, body)
    hub._resource_concluded(FakeResource(body))

    assert hub.available_rooms == {"lobby": None}
    assert hub._silent_list_pending == 0


def test_resource_notice_motd_still_records(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))

    body = b"welcome to the hub"
    with hub._lock:
        hub._resource_expectations[b"\x02" * 8] = {
            "kind": proto.RES_KIND_MOTD,
            "size": len(body),
            "sha256": None,
            "encoding": "utf-8",
            "room": None,
            "expires": 1e18,
        }
    hub._resource_concluded(FakeResource(body))

    assert hub.motd == "welcome to the hub"


def test_resource_notice_sha256_mismatch_drops(tmp_path):
    import hashlib

    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))

    body = b"Registered public rooms:\n  lobby"
    with hub._lock:
        hub._resource_expectations[b"\x03" * 8] = {
            "kind": proto.RES_KIND_NOTICE,
            "size": len(body),
            "sha256": hashlib.sha256(b"tampered").digest(),
            "encoding": "utf-8",
            "room": None,
            "expires": 1e18,
        }
    hub._resource_concluded(FakeResource(body))

    assert hub.available_rooms == {}


def _notice_env(text, src=None):
    return {
        proto.K_T: proto.T_NOTICE,
        proto.K_BODY: text,
        proto.K_ROOM: None,
        proto.K_SRC: src,
    }


def test_hub_notice_accepts_destination_hash_src(tmp_path):
    """Foreign hubs may stamp notices with the destination hash."""
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    hub._hub_identity_hash = b"\xaa" * 16

    hub._handle_notice(
        _notice_env("Registered public rooms:\n  lobby", src=bytes(range(16)))
    )
    assert hub.available_rooms == {"lobby": None}


def test_hub_notice_accepts_identity_hash_src(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    hub._hub_identity_hash = b"\xaa" * 16

    hub._handle_notice(
        _notice_env("Registered public rooms:\n  lobby", src=b"\xaa" * 16)
    )
    assert hub.available_rooms == {"lobby": None}


def test_hub_notice_rejects_peer_src(tmp_path):
    """A peer-stamped src must not drive room list or MOTD state."""
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    hub._hub_identity_hash = b"\xaa" * 16

    hub._handle_notice(
        _notice_env("Registered public rooms:\n  lobby", src=b"\xbb" * 16)
    )
    assert hub.available_rooms == {}

    hub._handle_notice(_notice_env("spoofed motd", src=b"\xbb" * 16))
    assert hub.motd is None


def test_hub_notice_motd_accepts_destination_hash_src(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    hub._hub_identity_hash = b"\xaa" * 16

    hub._handle_notice(_notice_env("server rules be nice", src=bytes(range(16))))
    assert hub.motd == "server rules be nice"


def _notice_env(body, src):
    return {
        proto.K_T: proto.T_NOTICE,
        proto.K_BODY: body,
        proto.K_ROOM: None,
        proto.K_SRC: src,
    }


def test_chunked_list_notice_reassembles(tmp_path):
    """An oversized /list reply arrives from rrcd as per-line NOTICE envelopes."""
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    src = bytes(range(16))
    hub._silent_list_pending = 1

    for line in ["Registered public rooms:", "  lobby - the lobby", "  dev"]:
        hub._handle_notice(_notice_env(line, src))
    # A non-matching notice ends the burst and flushes the buffer.
    hub._handle_notice(_notice_env("unrelated hub notice", src))

    assert hub.available_rooms == {"lobby": "the lobby", "dev": None}
    assert hub._silent_list_pending == 0


def test_chunked_list_flushes_on_non_notice(tmp_path):
    manager = make_manager(tmp_path, nickname="alice")
    hub = manager.add_hub(bytes(range(16)))
    src = bytes(range(16))

    for line in ["Registered public rooms:", "  lobby"]:
        hub._handle_notice(_notice_env(line, src))
    hub._on_packet(proto.encode({proto.K_T: proto.T_PING}))

    assert hub.available_rooms == {"lobby": None}
