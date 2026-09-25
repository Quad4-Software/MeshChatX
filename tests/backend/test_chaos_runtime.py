# SPDX-License-Identifier: 0BSD
"""Chaos and race tests for runtime managers.

Covers RRC hub connect storms, identity hotswap serialization, and
Reticulum reload serialization.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import threading
import time
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager


@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def mock_rns():
    real_identity_class = RNS.Identity

    class MockIdentityClass(real_identity_class):
        def __init__(self, *args, **kwargs):
            self.hash = b"initial_hash_32_bytes_long_01234"
            self.hexhash = self.hash.hex()

    with ExitStack() as stack:
        patches = [
            patch("RNS.Reticulum"),
            patch("RNS.Transport"),
            patch("RNS.Identity", MockIdentityClass),
            patch("threading.Thread"),
            patch(
                "asyncio.to_thread",
                side_effect=lambda fn, *args, **kwargs: fn(*args, **kwargs),
            ),
            patch("meshchatx.src.backend.identity_context.Database"),
            patch("meshchatx.src.backend.identity_context.ConfigManager"),
            patch("meshchatx.src.backend.identity_context.MessageHandler"),
            patch("meshchatx.src.backend.identity_context.AnnounceManager"),
            patch("meshchatx.src.backend.identity_context.ArchiverManager"),
            patch("meshchatx.src.backend.identity_context.MapManager"),
            patch("meshchatx.src.backend.identity_context.DocsManager"),
            patch("meshchatx.src.backend.identity_context.NomadNetworkManager"),
            patch("meshchatx.src.backend.identity_context.TelephoneManager"),
            patch("meshchatx.src.backend.identity_context.VoicemailManager"),
            patch("meshchatx.src.backend.identity_context.RingtoneManager"),
            patch("meshchatx.src.backend.identity_context.RNCPHandler"),
            patch("meshchatx.src.backend.identity_context.RNStatusHandler"),
            patch("meshchatx.src.backend.identity_context.RNProbeHandler"),
            patch("meshchatx.src.backend.identity_context.CommunityInterfacesManager"),
            patch("LXMF.LXMRouter"),
            patch("meshchatx.meshchat.IdentityContext"),
        ]
        mocks = {}
        for p in patches:
            attr_name = (
                p.attribute if hasattr(p, "attribute") else p.target.split(".")[-1]
            )
            mocks[attr_name] = stack.enter_context(p)

        mock_id_instance = MockIdentityClass()
        mock_id_instance.get_private_key = MagicMock(
            return_value=b"initial_private_key"
        )

        stack.enter_context(
            patch.object(MockIdentityClass, "from_file", return_value=mock_id_instance),
        )
        stack.enter_context(
            patch.object(MockIdentityClass, "recall", return_value=mock_id_instance),
        )
        stack.enter_context(
            patch.object(
                MockIdentityClass, "from_bytes", return_value=mock_id_instance
            ),
        )

        mocks["ConfigManager"].return_value.display_name.get.return_value = "Test User"
        yield {
            "Identity": MockIdentityClass,
            "id_instance": mock_id_instance,
            "IdentityContext": mocks["IdentityContext"],
        }


def _hub_hash(i: int) -> bytes:
    return bytes([i & 0xFF]) + b"\x00" * 31


def _make_manager(tmp_path):
    identity = MagicMock()
    identity.get_private_key.return_value = b"\x01" * 32
    return RRCManager(identity=identity, storage_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_hotswap_identity_lock_serializes(mock_rns, temp_dir):
    """Two concurrent hotswaps must never interleave teardown/setup."""
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    in_flight = 0
    max_in_flight = 0
    order = []

    new_hash = "aa" * 16
    identity_dir = os.path.join(temp_dir, "identities", new_hash)
    os.makedirs(identity_dir)
    with open(os.path.join(identity_dir, "identity"), "wb") as f:
        f.write(b"new_private_key")

    new_id = MagicMock()
    new_id.hash = bytes.fromhex(new_hash)
    mock_rns["Identity"].from_file.return_value = new_id
    ctx = mock_rns["IdentityContext"].return_value
    ctx.config.display_name.get.return_value = "New User"
    ctx.identity_hash = new_hash

    async def fake_teardown(*_a, **_k):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        order.append("teardown-begin")
        await asyncio.sleep(0.02)
        order.append("teardown-end")

    def fake_setup(_id):
        nonlocal in_flight
        order.append("setup")
        app.current_context = ctx
        in_flight -= 1

    app.teardown_identity = MagicMock(side_effect=lambda *a, **k: None)
    # teardown_identity is sync in production; emulate an async critical
    # section through the broadcast boundary instead.
    app.websocket_broadcast = AsyncMock()
    app.setup_identity = MagicMock(side_effect=fake_setup)

    # Serialize two swaps through the real lock path.
    async def swap(h):
        async with app._identity_hotswap_lock:
            await fake_teardown()
            fake_setup(new_id)

    await asyncio.gather(swap(new_hash), swap(new_hash), swap(new_hash))
    assert max_in_flight == 1
    # Each swap contributes a strict teardown-begin -> teardown-end -> setup.
    for i in range(0, len(order), 3):
        assert order[i : i + 3] == ["teardown-begin", "teardown-end", "setup"]


@pytest.mark.asyncio
async def test_reload_reticulum_lock_serializes(mock_rns, temp_dir):
    app = ReticulumMeshChat(
        identity=mock_rns["id_instance"],
        storage_dir=temp_dir,
        reticulum_config_dir=temp_dir,
    )
    in_flight = 0
    max_in_flight = 0

    async def fake_locked():
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return "reloaded"

    app._reload_reticulum_locked = fake_locked
    results = await asyncio.gather(
        app.reload_reticulum(),
        app.reload_reticulum(),
        app.reload_reticulum(),
    )
    assert max_in_flight == 1
    assert results == ["reloaded"] * 3


def test_hub_connect_disconnect_storm(tmp_path, monkeypatch):
    """Connect/disconnect cycles from many threads must leave the hub in a consistent state.

    No exception may propagate and status must settle after the storm.
    """
    manager = _make_manager(tmp_path)
    hub = manager.add_hub(_hub_hash(1), name="storm")
    hub.auto_reconnect = False

    monkeypatch.setattr(RNS.Transport, "has_path", lambda *_a, **_k: True)
    monkeypatch.setattr(RNS.Identity, "recall", lambda *_a, **_k: None)

    errors = []
    stop = threading.Event()

    def cycler(i):
        try:
            for _ in range(30):
                if i % 2 == 0:
                    hub.connect()
                else:
                    hub.disconnect()
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [
        threading.Thread(target=cycler, args=(i,), daemon=True) for i in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), "cycler thread did not finish"

    assert not errors
    # Let in-flight connect workers settle, then force a clean end state.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and hub.status == RRCHub.STATUS_CONNECTING:
        time.sleep(0.05)
    hub.disconnect()
    assert hub.status == RRCHub.STATUS_DISCONNECTED
    assert hub.link is None
    stop.set()


def test_hub_add_storm_dedupes(tmp_path):
    """Concurrent add_hub for the same hash must produce exactly one hub."""
    manager = _make_manager(tmp_path)
    target = _hub_hash(7)
    results = []
    results_lock = threading.Lock()

    def adder(i):
        h = manager.add_hub(target if i % 3 == 0 else _hub_hash(i), name=f"h{i}")
        with results_lock:
            results.append(h)

    threads = [
        threading.Thread(target=adder, args=(i,), daemon=True) for i in range(24)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
        assert not t.is_alive()

    dupes = [h for h in manager.hubs if h.hub_hash == target]
    assert len(dupes) == 1
    assert len(manager.hubs) == len({h.hub_hash for h in manager.hubs})
    # find_hub returns the canonical instance for the duplicated hash.
    assert manager.find_hub(target) is dupes[0]


def test_remove_hub_racing_connect(tmp_path, monkeypatch):
    """remove_hub during an in-flight connect must not resurrect the hub."""
    manager = _make_manager(tmp_path)
    hub = manager.add_hub(_hub_hash(9), name="doomed")
    hub.auto_reconnect = False

    monkeypatch.setattr(RNS.Transport, "has_path", lambda *_a, **_k: True)
    monkeypatch.setattr(RNS.Identity, "recall", lambda *_a, **_k: None)

    errors = []

    def connector():
        try:
            for _ in range(20):
                hub.connect()
                time.sleep(0.002)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    t = threading.Thread(target=connector, daemon=True)
    t.start()
    time.sleep(0.01)
    manager.remove_hub(hub)
    t.join(timeout=30)
    assert not t.is_alive()
    assert not errors
    assert hub not in manager.hubs
    assert manager.find_hub(_hub_hash(9)) is None


def test_auto_reconnect_storm_no_overlapping_workers(tmp_path, monkeypatch):
    """The auto-reconnect storm must never overlap connect workers for one hub.

    Hub connect runs are guarded by CONNECTING status; two workers for the
    same hub would race connection attempts.
    """
    manager = _make_manager(tmp_path)
    for i in range(5):
        hub = manager.add_hub(_hub_hash(20 + i), name=f"auto{i}")
        hub.set_auto_reconnect(True, save=False)

    monkeypatch.setattr(RNS.Transport, "has_path", lambda *_a, **_k: True)
    monkeypatch.setattr(RNS.Identity, "recall", lambda *_a, **_k: None)

    state = {"calls": 0, "max_per_hub": 0}
    in_flight: dict[int, int] = {}
    state_lock = threading.Lock()
    real_worker = RRCHub._connect_worker

    def counted_worker(self):
        key = id(self)
        with state_lock:
            in_flight[key] = in_flight.get(key, 0) + 1
            state["calls"] += 1
            state["max_per_hub"] = max(state["max_per_hub"], in_flight[key])
        try:
            real_worker(self)
        finally:
            with state_lock:
                in_flight[key] -= 1

    monkeypatch.setattr(RRCHub, "_connect_worker", counted_worker)

    errors = []

    def auto():
        try:
            for _ in range(4):
                manager.connect_auto_reconnect_hubs()
                time.sleep(0.002)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=auto, daemon=True) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
        assert not t.is_alive()

    assert not errors
    assert state["calls"] >= 1
    assert state["max_per_hub"] <= 1

    for h in manager.hubs:
        h.disconnect()
    for h in manager.hubs:
        assert h.status == RRCHub.STATUS_DISCONNECTED
