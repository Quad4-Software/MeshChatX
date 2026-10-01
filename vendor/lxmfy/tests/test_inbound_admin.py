"""Tests for inbound introspection, peer announce reads, and /inbox."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
import RNS

from lxmfy import TestBot


@pytest.fixture
def bot():
    b = TestBot()
    yield b
    b.close()


class _FakeResource:
    def __init__(self, hash_bytes, progress=0.5, size=4096, status=2):
        self.hash = hash_bytes
        self.status = status
        self.size = size
        self._progress = progress

    def get_progress(self):
        return self._progress

    def get_transfer_size(self):
        return int(self.size * 1.1)


class _FakeRouter:
    def __init__(self, resources=()):
        self._resources = list(resources)
        self.cancelled = []
        self.seen = set()

    def inbound_resources(self):
        return self._resources

    def inbound_count(self):
        return len(self._resources)

    def cancel_inbound(self, raw):
        self.cancelled.append(raw)

    def cancel_all_inbound(self):
        self._resources.clear()

    def has_message(self, raw):
        return raw in self.seen


class TestInboundWrappers:
    def test_no_router_safe_defaults(self, bot):
        assert bot.inbound_count() == 0
        assert bot.inbound_transfers() == []
        assert bot.has_message(b"\x00" * 32) is False
        assert bot.cancel_inbound(b"\x00" * 32) is False
        assert bot.cancel_all_inbound() == 0

    def test_inbound_count(self, bot):
        bot.router = _FakeRouter([_FakeResource(b"\x01" * 32)])
        assert bot.inbound_count() == 1

    def test_inbound_transfers(self, bot):
        resource = _FakeResource(b"\x02" * 32, progress=0.25)
        bot.router = _FakeRouter([resource])
        entries = bot.inbound_transfers()
        assert len(entries) == 1
        assert entries[0]["hash"] == (b"\x02" * 32).hex()
        assert entries[0]["progress"] == 0.25
        assert entries[0]["size"] == 4096
        assert entries[0]["transfer_size"] == int(4096 * 1.1)

    def test_has_message(self, bot):
        router = _FakeRouter()
        raw = b"\x03" * 32
        router.seen.add(raw)
        bot.router = router
        assert bot.has_message(raw) is True
        assert bot.has_message(raw.hex()) is True
        assert bot.has_message(b"\x04" * 32) is False

    def test_has_message_bad_input(self, bot):
        bot.router = _FakeRouter()
        assert bot.has_message("zz") is False
        assert bot.has_message(b"short") is False
        assert bot.has_message(None) is False

    def test_cancel_inbound(self, bot):
        raw = b"\x05" * 32
        bot.router = _FakeRouter([_FakeResource(raw)])
        assert bot.cancel_inbound(raw.hex()) is True
        assert router_cancelled(bot.router) == [raw]

    def test_cancel_inbound_unknown(self, bot):
        bot.router = _FakeRouter()
        assert bot.cancel_inbound(b"\x06" * 32) is False

    def test_cancel_all_inbound(self, bot):
        bot.router = _FakeRouter(
            [_FakeResource(b"\x07" * 32), _FakeResource(b"\x08" * 32)],
        )
        assert bot.cancel_all_inbound() == 2
        assert bot.inbound_count() == 0


def router_cancelled(router):
    return router.cancelled


class TestInboxCommand:
    def test_inbox_empty(self, bot):
        bot.router = _FakeRouter()
        bot.admins.add(bot.sender_hex("root"))
        sent = bot.receive("/inbox", sender="root")
        assert sent[0].content == "active inbound transfers: 0"

    def test_inbox_lists_transfers(self, bot):
        bot.router = _FakeRouter([_FakeResource(b"\x09" * 32, progress=0.5)])
        bot.admins.add(bot.sender_hex("root"))
        sent = bot.receive("/inbox", sender="root")
        assert "active inbound transfers: 1" in sent[0].content
        assert "50%" in sent[0].content

    def test_inbox_cancel_all(self, bot):
        bot.router = _FakeRouter([_FakeResource(b"\x0a" * 32)])
        bot.admins.add(bot.sender_hex("root"))
        sent = bot.receive("/inbox cancel all", sender="root")
        assert "Cancelled 1 inbound transfer(s)" in sent[0].content

    def test_inbox_cancel_by_hash(self, bot):
        raw = b"\x0b" * 32
        bot.router = _FakeRouter([_FakeResource(raw)])
        bot.admins.add(bot.sender_hex("root"))
        sent = bot.receive(f"/inbox cancel {raw.hex()}", sender="root")
        assert sent[0].content == "Cancelled."

    def test_inbox_cancel_unknown(self, bot):
        bot.router = _FakeRouter()
        bot.admins.add(bot.sender_hex("root"))
        sent = bot.receive("/inbox cancel " + "cc" * 32, sender="root")
        assert "Not cancelled" in sent[0].content

    def test_inbox_denied_for_non_admin(self):
        with TestBot(permissions_enabled=True) as bot:
            bot.router = _FakeRouter()
            bot.admins.add(bot.sender_hex("root"))
            sent = bot.receive("/inbox", sender="mallory")
            assert "permission" in sent[0].content.lower()


class TestPeerAnnounce:
    def test_app_data_unknown(self, bot):
        assert bot.get_peer_app_data("ab" * 16) is None
        assert bot.get_peer_announce("ab" * 16) is None

    def test_app_data_bad_hash(self, bot):
        assert bot.get_peer_app_data("nothex") is None
        assert bot.get_peer_announce("") is None

    def test_seeded_announce(self, bot):
        dest = bytes.fromhex("dd" * 16)
        RNS.Identity.known_destinations[dest] = [
            time.time(),
            b"\x01" * 32,
            b"pubkey",
            b"TestPeer",
            0,
        ]
        packet = SimpleNamespace(packet_hash=b"\x02" * 32)
        iface = SimpleNamespace(name="TestIF")
        with RNS.Transport.announce_table_lock:
            RNS.Transport.announce_table[dest] = [
                time.time(),
                0.0,
                0,
                b"\x03" * 16,
                2,
                packet,
                0,
                False,
                iface,
            ]
        try:
            assert bot.get_peer_app_data(dest.hex()) == b"TestPeer"
            info = bot.get_peer_announce(dest.hex())
            assert info["hops"] == 2
            assert info["app_data"] == b"TestPeer"
            assert info["destination"] == dest.hex()
            assert info["interface"] == "TestIF"
            announces = bot.list_peer_announces()
            assert any(a["destination"] == dest.hex() for a in announces)
        finally:
            RNS.Identity.known_destinations.pop(dest, None)
            with RNS.Transport.announce_table_lock:
                RNS.Transport.announce_table.pop(dest, None)

    def test_list_peer_announces_limit(self, bot):
        for i in range(5):
            dest = bytes([0xE0 + i]) * 16
            with RNS.Transport.announce_table_lock:
                RNS.Transport.announce_table[dest] = [
                    time.time() - i,
                    0.0,
                    0,
                    None,
                    i,
                    SimpleNamespace(packet_hash=None),
                    0,
                    False,
                    None,
                ]
        try:
            entries = bot.list_peer_announces(limit=3)
            assert len(entries) == 3
            timestamps = [e["received_at"] for e in entries]
            assert timestamps == sorted(timestamps, reverse=True)
        finally:
            for i in range(5):
                dest = bytes([0xE0 + i]) * 16
                with RNS.Transport.announce_table_lock:
                    RNS.Transport.announce_table.pop(dest, None)
