# SPDX-License-Identifier: 0BSD

"""Fake-link tests for the bundled AwareInterface RNS module.

The Java AwareSession is replaced by a fake android_locallink bridge, so the
tests pin the interface contract: session lifecycle, per-peer spawning,
HDLC framing parity with TCPClientInterface, and teardown.
"""

from __future__ import annotations

import importlib.util
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import RNS
from RNS.Interfaces.TCPInterface import HDLC

from meshchatx.src.backend import android_locallink

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "meshchatx",
    "src",
    "backend",
    "data",
    "interfaces",
    "AwareInterface.py",
)


def _load_module():
    spec = importlib.util.spec_from_file_location("AwareInterface", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def reticulum(tmp_path_factory):
    """Interface.__init__ needs a live Reticulum for ingress defaults.

    The config has no interfaces on purpose: the default AutoInterface would
    bind the UDP discovery ports that other tests spawn subprocesses onto.
    """
    config_dir = tmp_path_factory.mktemp("rns-aware")
    (config_dir / "config").write_text(
        "[reticulum]\nenable_transport = no\nshare_instance = no\n\n[interfaces]\n",
        encoding="utf-8",
    )
    yield RNS.Reticulum(configdir=str(config_dir), loglevel=RNS.LOG_ERROR)
    # Reset the RNS singleton so later tests can init their own Reticulum.
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass
    if hasattr(RNS.Reticulum, "_Reticulum__instance"):
        RNS.Reticulum._Reticulum__instance = None
    for flag in (
        "_Reticulum__exit_handler_ran",
        "_Reticulum__interface_detach_ran",
    ):
        if hasattr(RNS.Reticulum, flag):
            setattr(RNS.Reticulum, flag, False)
    try:
        from meshchatx.meshchat import ReticulumMeshChat

        ReticulumMeshChat._reset_transport_globals_for_reload()
    except Exception:
        RNS.Transport._should_run = True
        RNS.Transport.interfaces = []
        RNS.Transport.destinations = []


@pytest.fixture()
def aware_module(reticulum):
    module = _load_module()
    yield module
    # Clean any spawned interfaces registered during the test.
    for iface in list(RNS.Transport.interfaces):
        if iface.__class__.__name__ == "AwarePeerInterface":
            RNS.Transport.remove_interface(iface)


@pytest.fixture(autouse=True)
def reset_bridge():
    android_locallink._aware = None
    android_locallink._aware_listeners.clear()
    with android_locallink._bridge_lock:
        android_locallink._bridge = None
    yield
    android_locallink._aware = None
    android_locallink._aware_listeners.clear()


class _FakeAwareBridge:
    def __init__(self):
        self.calls = []
        self.sent = []

    def startPublish(self):
        self.calls.append("publish")

    def startSubscribe(self):
        self.calls.append("subscribe")

    def stop(self):
        self.calls.append("stop")

    def sendToPeer(self, peer_id, data):
        self.sent.append((peer_id, bytes(data)))
        return True

    def closePeer(self, peer_id):
        self.calls.append(("close", peer_id))


def _install_fake_aware():
    fake = _FakeAwareBridge()
    android_locallink._aware = fake
    # is_available() gates on _bridge; a truthy stand-in is enough here.
    with android_locallink._bridge_lock:
        android_locallink._bridge = SimpleNamespace()
    return fake


def _make_owner():
    owner = SimpleNamespace()
    owner.inbound = MagicMock()
    return owner


def _real_config(name="aware", mode="subscribe", peers=4):
    """ConfigObj-like dict the interface can index and 'in' test."""
    return {"name": name, "mode": mode, "peers": peers}


def _spawn(module, owner, mode="subscribe", peers=4):
    fake = _install_fake_aware()
    iface = module.AwareInterface(owner, _real_config(mode=mode, peers=peers))
    return iface, fake


class TestAwareInterfaceLifecycle:
    def test_starts_session_with_mode(self, aware_module):
        iface, fake = _spawn(aware_module, _make_owner(), mode="publish")
        assert fake.calls == ["publish"]
        assert iface.online is True
        assert iface.max_peers == 4
        iface.detach()

    def test_subscribe_mode(self, aware_module):
        iface, fake = _spawn(aware_module, _make_owner(), mode="subscribe")
        assert fake.calls == ["subscribe"]
        iface.detach()

    def test_peer_cap_clamped(self, aware_module):
        iface, _ = _spawn(aware_module, _make_owner(), peers=99)
        assert iface.max_peers == aware_module.AwareInterface.MAX_PEERS_LIMIT
        iface.detach()

    def test_requires_bridge(self, aware_module):
        android_locallink._aware = None
        with pytest.raises(SystemError):
            aware_module.AwareInterface(_make_owner(), _real_config())

    def test_detach_stops_session(self, aware_module):
        iface, fake = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 1, None)
        iface.detach()
        assert "stop" in fake.calls
        assert iface.online is False
        assert iface.spawned_interfaces == []


class TestPeerSpawning:
    def test_link_up_spawns_peer(self, aware_module):
        iface, _ = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 42, None)
        assert 42 in iface.peers
        peer = iface.peers[42]
        assert peer.online is True
        assert peer in iface.spawned_interfaces
        assert peer in RNS.Transport.interfaces
        iface.detach()

    def test_duplicate_link_up_ignored(self, aware_module):
        iface, _ = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 1, None)
        iface._on_aware_event("link_up", 1, None)
        assert len(iface.spawned_interfaces) == 1
        iface.detach()

    def test_peer_cap_drops_link(self, aware_module):
        iface, fake = _spawn(aware_module, _make_owner(), peers=1)
        iface._on_aware_event("link_up", 1, None)
        iface._on_aware_event("link_up", 2, None)
        assert len(iface.spawned_interfaces) == 1
        assert ("close", 2) in fake.calls
        iface.detach()

    def test_link_down_tears_down(self, aware_module):
        iface, _ = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 7, None)
        peer = iface.peers[7]
        iface._on_aware_event("link_down", 7, None)
        assert 7 not in iface.peers
        assert peer.online is False
        assert peer not in RNS.Transport.interfaces
        iface.detach()


class TestHdlcFraming:
    def test_outgoing_frames(self, aware_module):
        iface, fake = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 5, None)
        peer = iface.peers[5]
        payload = bytes([HDLC.FLAG, 0x41, HDLC.ESC, 0x42])
        peer.process_outgoing(payload)
        peer_id, sent = fake.sent[-1]
        assert peer_id == 5
        expected = bytes([HDLC.FLAG]) + HDLC.escape(payload) + bytes([HDLC.FLAG])
        assert sent == expected
        iface.detach()

    def test_incoming_deframes(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 9, None)
        peer = iface.peers[9]
        payload = bytes(range(20, 80))  # >= HEADER_MINSIZE
        wire = bytes([HDLC.FLAG]) + HDLC.escape(payload) + bytes([HDLC.FLAG])
        peer.feed_bytes(wire)
        owner.inbound.assert_called_once_with(payload, peer)
        iface.detach()

    def test_split_frames(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 9, None)
        peer = iface.peers[9]
        payload = bytes(range(30, 90))
        wire = bytes([HDLC.FLAG]) + HDLC.escape(payload) + bytes([HDLC.FLAG])
        mid = len(wire) // 2
        peer.feed_bytes(wire[:mid])
        assert owner.inbound.call_count == 0
        peer.feed_bytes(wire[mid:])
        owner.inbound.assert_called_once_with(payload, peer)
        iface.detach()

    def test_two_frames_one_read(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 9, None)
        peer = iface.peers[9]
        p1 = bytes(range(20, 50))
        p2 = bytes(range(60, 95))
        wire = (
            bytes([HDLC.FLAG])
            + HDLC.escape(p1)
            + bytes([HDLC.FLAG])
            + HDLC.escape(p2)
            + bytes([HDLC.FLAG])
        )
        peer.feed_bytes(wire)
        assert owner.inbound.call_count == 2
        owner.inbound.assert_any_call(p1, peer)
        owner.inbound.assert_any_call(p2, peer)
        iface.detach()

    def test_short_frame_dropped(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 9, None)
        peer = iface.peers[9]
        tiny = b"\x01\x02\x03"
        wire = bytes([HDLC.FLAG]) + HDLC.escape(tiny) + bytes([HDLC.FLAG])
        peer.feed_bytes(wire)
        assert owner.inbound.call_count == 0
        iface.detach()

    def test_data_dispatch_routes_to_peer(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 3, None)
        payload = bytes(range(20, 60))
        wire = bytes([HDLC.FLAG]) + HDLC.escape(payload) + bytes([HDLC.FLAG])
        iface._on_aware_event("data", 3, wire)
        owner.inbound.assert_called_once_with(payload, iface.peers[3])
        iface.detach()

    def test_wire_compat_with_tcp_escape(self, aware_module):
        """Escaped bytes must be identical to TCPClientInterface's HDLC."""
        iface, fake = _spawn(aware_module, _make_owner())
        iface._on_aware_event("link_up", 1, None)
        peer = iface.peers[1]
        hostile = bytes([HDLC.FLAG, HDLC.ESC, HDLC.FLAG, 0x00, HDLC.ESC])
        peer.process_outgoing(hostile)
        _, sent = fake.sent[-1]
        inner = sent[1:-1]
        assert HDLC.FLAG not in inner
        assert HDLC.ESC in inner
        assert inner == HDLC.escape(hostile)
        iface.detach()


class TestCounters:
    def test_rxb_txb_accounting(self, aware_module):
        owner = _make_owner()
        iface, _ = _spawn(aware_module, owner)
        iface._on_aware_event("link_up", 2, None)
        peer = iface.peers[2]
        payload = bytes(range(20, 70))
        peer.process_outgoing(payload)
        assert peer.txb > 0
        assert iface.txb == peer.txb
        wire = bytes([HDLC.FLAG]) + HDLC.escape(payload) + bytes([HDLC.FLAG])
        peer.feed_bytes(wire)
        assert peer.rxb == len(payload)
        assert iface.rxb == len(payload)
        iface.detach()
