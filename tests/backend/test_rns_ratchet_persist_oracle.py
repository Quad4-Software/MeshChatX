# SPDX-License-Identifier: 0BSD
"""Oracle: RNS ratchet persist uses one worker instead of Thread-per-write."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import meshchatx.src.backend.rns_ratchet_persist as ratchet_mod


def _reset_module_state():
    ratchet_mod._PATCHED = False
    ratchet_mod._ORIGINAL_REMEMBER = None
    ratchet_mod._QUEUE = None
    ratchet_mod._WORKER = None
    with ratchet_mod._LATEST_LOCK:
        ratchet_mod._LATEST.clear()


def test_enqueue_persist_starts_single_worker_and_coalesces():
    _reset_module_state()
    persisted: list[tuple[bytes, bytes]] = []
    done = threading.Event()

    def fake_persist(destination_hash, ratchet):
        persisted.append((destination_hash, ratchet))
        if len(persisted) >= 1:
            done.set()

    dest = b"\x11" * 32
    with patch.object(ratchet_mod, "_persist_one", side_effect=fake_persist):
        ratchet_mod._enqueue_persist(dest, b"\x22" * 32)
        ratchet_mod._enqueue_persist(dest, b"\x33" * 32)
        assert done.wait(timeout=2)

    assert ratchet_mod._WORKER is not None
    assert ratchet_mod._WORKER.name == "meshchatx-ratchet-persist"
    assert ratchet_mod._WORKER.is_alive()
    # Coalesced to the latest ratchet bytes for the destination.
    assert persisted[-1] == (dest, b"\x33" * 32)


def test_persist_one_imports_rns_vendored_umsgpack():
    """Oracle: never bare-import top-level umsgpack (fails in frozen desktop)."""
    from pathlib import Path

    src = Path(ratchet_mod.__file__).read_text(encoding="utf-8")
    assert "import RNS.vendor.umsgpack as umsgpack" in src
    assert "\n    import umsgpack\n" not in src
    assert "\nimport umsgpack\n" not in src


def test_persist_one_writes_ratchet_via_vendored_umsgpack(tmp_path, monkeypatch):
    _reset_module_state()
    import RNS

    dest = b"\x11" * 32
    ratchet = b"\x22" * 32
    monkeypatch.setattr(RNS.Reticulum, "storagepath", str(tmp_path), raising=False)
    if (
        not hasattr(RNS.Identity, "ratchet_persist_lock")
        or RNS.Identity.ratchet_persist_lock is None
    ):
        monkeypatch.setattr(
            RNS.Identity, "ratchet_persist_lock", threading.Lock(), raising=False
        )

    ratchet_mod._persist_one(dest, ratchet)

    final = tmp_path / "ratchets" / RNS.hexrep(dest, delimit=False)
    assert final.is_file()
    from RNS.vendor import umsgpack

    loaded = umsgpack.unpackb(final.read_bytes())
    assert loaded["ratchet"] == ratchet
    assert "received" in loaded


def test_patched_remember_skips_persist_on_shared_instance():
    _reset_module_state()
    identity = MagicMock()
    identity.known_ratchets = {}
    identity._get_ratchet_id = MagicMock(return_value=b"\x01" * 32)

    fake_rns = MagicMock()
    fake_rns.Identity = identity
    fake_rns.Transport.owner.is_connected_to_shared_instance = True
    fake_rns.prettyhexrep = lambda value: value.hex()
    fake_rns.sl = MagicMock(return_value=False)
    fake_rns.LOG_EXTREME = 7

    with (
        patch.dict("sys.modules", {"RNS": fake_rns}),
        patch.object(ratchet_mod, "_enqueue_persist") as enqueue,
    ):
        dest = b"\x11" * 32
        ratchet = b"\x22" * 32
        ratchet_mod._patched_remember_ratchet(dest, ratchet)
        enqueue.assert_not_called()
        assert identity.known_ratchets[dest] == ratchet
