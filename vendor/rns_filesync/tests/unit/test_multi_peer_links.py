"""Multi-peer link registration must not collapse unidentified inbound peers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from rns_filesync.service import FileSyncService

pytestmark = [pytest.mark.unit, pytest.mark.acceptance]


class _FakeLink:
    def __init__(self, identity_hash: bytes | None = None):
        self._identity = None
        if identity_hash is not None:
            self._identity = SimpleNamespace(hash=identity_hash)
        # Shared local destination hash mimics inbound SINGLE links.
        self.destination = SimpleNamespace(hash=b"\x11" * 16)
        self.status = 2  # RNS.Link.ACTIVE
        self._identified_cb = None
        self.torn_down = False

    def get_remote_identity(self):
        return self._identity

    def set_remote_identified_callback(self, cb):
        self._identified_cb = cb

    def set_link_closed_callback(self, _cb):
        return None

    def set_packet_callback(self, _cb):
        return None

    def set_resource_strategy(self, _strategy):
        return None

    def set_resource_callback(self, _cb):
        return None

    def set_resource_started_callback(self, _cb):
        return None

    def set_resource_concluded_callback(self, _cb):
        return None

    def teardown(self):
        self.torn_down = True

    def identify(self, identity_hash: bytes):
        self._identity = SimpleNamespace(hash=identity_hash)
        if self._identified_cb is not None:
            self._identified_cb(self, self._identity)


def _open_service(tmp_path):
    sync = tmp_path / "sync"
    sync.mkdir()
    svc = FileSyncService(
        identity=SimpleNamespace(hash=b"\xaa" * 16),
        sync_directory=str(sync),
    )
    svc._send = lambda link, payload: None
    return svc


def test_two_unidentified_inbound_links_keep_distinct_slots(tmp_path):
    svc = _open_service(tmp_path)
    leaf_a = _FakeLink(None)
    leaf_b = _FakeLink(None)
    # Same destination.hash on both: old bug keyed both as one peer.
    assert leaf_a.destination.hash == leaf_b.destination.hash

    svc._on_link_established(leaf_a)
    svc._on_link_established(leaf_b)

    assert len(svc._links) == 2
    assert all(key.startswith("pending:") for key in svc._links)
    assert set(svc._links.values()) == {leaf_a, leaf_b}

    leaf_a.identify(b"\x01" * 16)
    leaf_b.identify(b"\x02" * 16)

    assert len(svc._links) == 2
    assert (b"\x01" * 16).hex() in svc._links
    assert (b"\x02" * 16).hex() in svc._links
    assert set(svc._links.values()) == {leaf_a, leaf_b}


def test_broadcast_reaches_both_provisional_peers(tmp_path):
    svc = _open_service(tmp_path)
    (tmp_path / "sync" / "note.txt").write_text("hi")
    svc.inventory.scan()
    svc.inventory.save()

    leaf_a = _FakeLink(None)
    leaf_b = _FakeLink(None)
    leaf_a.packets = []
    leaf_b.packets = []
    svc._send = lambda link, payload: link.packets.append(payload)

    svc._on_link_established(leaf_a)
    svc._on_link_established(leaf_b)
    svc._broadcast_update("note.txt")

    assert len(leaf_a.packets) == 1
    assert len(leaf_b.packets) == 1
