# SPDX-License-Identifier: 0BSD
"""Bound RNS Identity ratchet persistence to one worker thread.

Upstream RNS.Identity._remember_ratchet starts a new daemon Thread for every
new ratchet when not on a shared instance. Under announce flood that reaches
Thread-4000+ while each job waits on ratchet_persist_lock, then fails with
Errno 24 when opening ratchet files. MeshChatX replaces that path with a
bounded queue and a single persist worker.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Any

logger = logging.getLogger("meshchatx.rns_ratchet_persist")

_PATCHED = False
_ORIGINAL_REMEMBER = None
_QUEUE: queue.Queue[tuple[bytes, bytes] | None] | None = None
_WORKER: threading.Thread | None = None
_LATEST: dict[bytes, bytes] = {}
_LATEST_LOCK = threading.Lock()
_QUEUE_MAX = 512


def _persist_one(destination_hash: bytes, ratchet: bytes) -> None:
    import RNS
    import umsgpack

    with RNS.Identity.ratchet_persist_lock:
        hexhash = RNS.hexrep(destination_hash, delimit=False)
        ratchet_data = {"ratchet": ratchet, "received": time.time()}
        ratchetdir = RNS.Reticulum.storagepath + "/ratchets"
        if not os.path.isdir(ratchetdir):
            os.makedirs(ratchetdir)
        outpath = f"{ratchetdir}/{hexhash}.out"
        finalpath = f"{ratchetdir}/{hexhash}"
        with open(outpath, "wb") as ratchet_file:
            ratchet_file.write(umsgpack.packb(ratchet_data))
        os.replace(outpath, finalpath)


def _worker_loop() -> None:
    assert _QUEUE is not None
    while True:
        item = _QUEUE.get()
        if item is None:
            return
        destination_hash, _ignored = item
        with _LATEST_LOCK:
            ratchet = _LATEST.pop(destination_hash, None)
        if ratchet is None:
            continue
        try:
            _persist_one(destination_hash, ratchet)
        except Exception as exc:
            logger.error("Bounded ratchet persist failed: %s", exc)


def _ensure_worker() -> queue.Queue[tuple[bytes, bytes] | None]:
    global _QUEUE, _WORKER
    if _QUEUE is not None and _WORKER is not None and _WORKER.is_alive():
        return _QUEUE
    with _LATEST_LOCK:
        if _QUEUE is None:
            _QUEUE = queue.Queue(maxsize=_QUEUE_MAX)
        if _WORKER is None or not _WORKER.is_alive():
            _WORKER = threading.Thread(
                target=_worker_loop,
                name="meshchatx-ratchet-persist",
                daemon=True,
            )
            _WORKER.start()
        return _QUEUE


def _enqueue_persist(destination_hash: bytes, ratchet: bytes) -> None:
    with _LATEST_LOCK:
        _LATEST[destination_hash] = ratchet
    q = _ensure_worker()
    try:
        q.put_nowait((destination_hash, ratchet))
    except queue.Full:
        # Latest map already holds the newest bytes for this hash.
        # Drop the queue signal rather than spawning another thread.
        logger.warning("Ratchet persist queue full, coalescing writes")


def _patched_remember_ratchet(destination_hash: Any, ratchet: Any) -> None:
    import RNS

    try:
        if (
            destination_hash in RNS.Identity.known_ratchets
            and RNS.Identity.known_ratchets[destination_hash] == ratchet
        ):
            return

        RNS.log(
            f"Remembering ratchet {RNS.prettyhexrep(RNS.Identity._get_ratchet_id(ratchet))} "
            f"for {RNS.prettyhexrep(destination_hash)}",
            RNS.LOG_EXTREME,
        ) if RNS.sl(RNS.LOG_EXTREME) else None
        RNS.Identity.known_ratchets[destination_hash] = ratchet
        if not RNS.Transport.owner.is_connected_to_shared_instance:
            _enqueue_persist(destination_hash, ratchet)
    except Exception as e:
        RNS.log(
            f"Could not persist ratchet for {RNS.prettyhexrep(destination_hash)} to storage.",
            RNS.LOG_ERROR,
        )
        RNS.log(f"The contained exception was: {e}")
        RNS.trace_exception(e)


def install_bounded_ratchet_persist() -> bool:
    """Replace RNS Identity ratchet Thread-per-write with a single worker."""
    global _PATCHED, _ORIGINAL_REMEMBER
    if _PATCHED:
        return False
    try:
        import RNS
    except Exception:
        return False
    original = getattr(RNS.Identity, "_remember_ratchet", None)
    if original is None or original is _patched_remember_ratchet:
        return False
    _ORIGINAL_REMEMBER = original
    RNS.Identity._remember_ratchet = staticmethod(_patched_remember_ratchet)
    _ensure_worker()
    _PATCHED = True
    logger.info("Installed bounded RNS ratchet persist worker")
    return True


def raise_nofile_soft_limit(target: int = 65536) -> tuple[int, int] | None:
    """Raise the process soft open-file limit up to min(target, hard)."""
    try:
        import resource
    except Exception:
        return None
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    except Exception:
        return None
    desired = int(target)
    if hard > 0:
        desired = min(desired, int(hard))
    if soft >= desired:
        return soft, hard
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (desired, hard))
        return desired, hard
    except Exception as exc:
        logger.warning("Could not raise RLIMIT_NOFILE to %s: %s", desired, exc)
        return soft, hard
