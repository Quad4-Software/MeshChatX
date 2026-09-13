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
