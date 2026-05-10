# SPDX-License-Identifier: 0BSD

"""Multi-minute soak tests (announce DB + websocket fan-out).

These are **opt-in**: unset ``MESHCHAT_LONG_TEST_SECONDS`` skips them immediately.

Examples::

    MESHCHAT_LONG_TEST_SECONDS=300 uv run pytest tests/backend/test_long_running_stress.py -m long_running -v
    MESHCHAT_LONG_TEST_SECONDS=600 uv run pytest tests/backend/test_long_running_stress.py -m long_running -v

Quick smoke (seconds)::

    MESHCHAT_LONG_TEST_SECONDS=5 uv run pytest tests/backend/test_long_running_stress.py -m long_running -v
"""

from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.database.provider import DatabaseProvider


class _FakeIdentity:
    __slots__ = ("_h",)

    def __init__(self, identity_hex32: str):
        self._h = bytes.fromhex(identity_hex32)

    @property
    def hash(self):
        return self._h

    def get_public_key(self):
        return b"\xaa\xbb"


def _cleanup(db, path):
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
    DatabaseProvider._instance = None
    if path:
        try:
            os.unlink(path)
        except OSError:
            pass
        for suffix in ("-wal", "-shm"):
            try:
                os.unlink(path + suffix)
            except OSError:
                pass


def _new_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = Database(path)
    db.initialize()
    return db, path


def _store_enabled_config(**max_stored):
    config = MagicMock()
    for _k in (
        "announce_store_lxmf_delivery",
        "announce_store_lxst_telephony",
        "announce_store_nomadnetwork_node",
        "announce_store_lxmf_propagation",
        "announce_store_git_repositories",
    ):
        m = MagicMock()
        m.get.return_value = True
        setattr(config, _k, m)

    for key, default in (
        ("announce_max_stored_lxmf_delivery", None),
        ("announce_max_stored_nomadnetwork_node", None),
        ("announce_max_stored_lxmf_propagation", None),
    ):
        attr = MagicMock()
        attr.get.return_value = max_stored.get(key, default)
        setattr(config, key, attr)

    return config


def _long_test_seconds() -> float:
    raw = os.environ.get("MESHCHAT_LONG_TEST_SECONDS", "").strip()
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _require_long_duration():
    sec = _long_test_seconds()
    if sec <= 0:
        pytest.skip(
            "Set MESHCHAT_LONG_TEST_SECONDS to a positive value "
            "(e.g. 300 for 5 minutes, 600 for 10 minutes).",
        )
    return sec


def _bind_real_websocket_broadcast(app):
    return ReticulumMeshChat.websocket_broadcast.__get__(app, ReticulumMeshChat)


class _MagicWs:
    __slots__ = ("send_str",)

    def __init__(self):
        self.send_str = AsyncMock(return_value=None)


@pytest.mark.long_running
def test_soak_sqlite_announces_stay_bounded_and_quick_check():
    duration_s = _require_long_duration()
    cap = 96
    batch_size = 120
    qc_interval_batches = 15

    db, path = _new_db()
    try:
        cfg = _store_enabled_config(announce_max_stored_lxmf_delivery=cap)
        mgr = AnnounceManager(db, cfg)
        ret = MagicMock()
        deadline = time.monotonic() + duration_s
        seq = 0
        batches = 0
        while time.monotonic() < deadline:
            for _ in range(batch_size):
                mgr.upsert_announce(
                    ret,
                    _FakeIdentity(f"{seq % 2048:032x}"),
                    bytes.fromhex(f"{seq:032x}"),
                    "lxmf.delivery",
                    os.urandom(48),
                    None,
                )
                seq += 1
            batches += 1
            assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == cap
            if batches % qc_interval_batches == 0:
                qc = db.provider.quick_check()
                assert qc
                assert next(iter(qc[0].values())) == "ok"
        assert seq > 0
    finally:
        _cleanup(db, path)


@pytest.mark.long_running
def test_soak_interleaved_aspects_under_cap():
    duration_s = _require_long_duration()
    cfg = _store_enabled_config(
        announce_max_stored_lxmf_delivery=40,
        announce_max_stored_nomadnetwork_node=25,
        announce_max_stored_lxmf_propagation=30,
    )

    db, path = _new_db()
    try:
        mgr = AnnounceManager(db, cfg)
        ret = MagicMock()
        deadline = time.monotonic() + duration_s
        n = 0
        while time.monotonic() < deadline:
            for aspect, payload in (
                ("lxmf.delivery", b"a"),
                ("nomadnetwork.node", b"b"),
                ("lxmf.propagation", b"c"),
            ):
                mgr.upsert_announce(
                    ret,
                    _FakeIdentity(f"{n % 900:032x}"),
                    bytes.fromhex(f"{n:032x}"),
                    aspect,
                    payload,
                    None,
                )
                n += 1
            assert db.announces.get_announce_count_by_aspect("lxmf.delivery") <= 40
            assert db.announces.get_announce_count_by_aspect("nomadnetwork.node") <= 25
            assert db.announces.get_announce_count_by_aspect("lxmf.propagation") <= 30
        assert n > 0
        assert db.announces.get_announce_count_by_aspect("lxmf.delivery") == 40
        assert db.announces.get_announce_count_by_aspect("nomadnetwork.node") == 25
        assert db.announces.get_announce_count_by_aspect("lxmf.propagation") == 30
    finally:
        _cleanup(db, path)


@pytest.mark.long_running
@pytest.mark.asyncio
async def test_soak_websocket_broadcast_under_load(mock_app):
    duration_s = _require_long_duration()
    mock_app.websocket_clients.clear()
    n_clients = min(int(os.environ.get("MESHCHAT_LONG_TEST_WS_CLIENTS", "400")), 2000)
    clients = [_MagicWs() for _ in range(n_clients)]
    mock_app.websocket_clients.extend(clients)
    real = _bind_real_websocket_broadcast(mock_app)

    deadline = time.monotonic() + duration_s
    rounds = 0
    while time.monotonic() < deadline:
        payload = f'{{"type":"soak","round":{rounds}}}'
        await real(payload)
        for c in clients:
            assert c.send_str.await_args[0][0] == payload
        rounds += 1
    assert rounds > 0


@pytest.mark.long_running
@pytest.mark.asyncio
async def test_soak_websocket_broadcast_with_churn(mock_app):
    duration_s = _require_long_duration()
    real = _bind_real_websocket_broadcast(mock_app)
    deadline = time.monotonic() + duration_s
    wave = 0
    while time.monotonic() < deadline:
        mock_app.websocket_clients.clear()
        batch = [_MagicWs() for _ in range(80)]
        if wave % 3 == 0:
            for c in batch[:20]:
                c.send_str = AsyncMock(side_effect=ConnectionError("closed"))
        mock_app.websocket_clients.extend(batch)
        payload = f'{{"wave":{wave}}}'
        await real(payload)
        for c in mock_app.websocket_clients:
            assert c.send_str.await_args[0][0] == payload
        wave += 1
    assert wave > 0
