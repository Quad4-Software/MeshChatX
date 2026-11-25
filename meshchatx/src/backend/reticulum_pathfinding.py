# SPDX-License-Identifier: 0BSD

import asyncio
import contextlib
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import RNS

from meshchatx.src.backend.path_utils import path_response_window


@dataclass(frozen=True)
class OutboundPathOutcome:
    """Result of waiting for a Reticulum transport path before outbound LXMF."""

    path_available: bool
    prepare_measure: str
    used_nudge: bool


def format_outbound_path_finding_measure(outcome: OutboundPathOutcome) -> str:
    """Single string for storage/API: base measure, plus +nudge if a nudge was used."""
    base = outcome.prepare_measure
    if outcome.used_nudge:
        return f"{base}+nudge"
    return base


IDX_PT_TIMESTAMP = 0
IDX_PT_EXPIRES = 3

# Soft cap for in-memory RNS path table entries (~270 MB at RNS estimate).
DEFAULT_PATH_TABLE_SOFT_CAP = 15_000
DEFAULT_PATH_PRUNE_BATCH = 500
DEFAULT_PATH_PRUNE_TRIGGER = 10_000


def _path_table_entry_is_expired_by_reticulum_rules(entry) -> bool:
    # RNS stores the computed expiry at IDX_PT_EXPIRES (index 3) in both
    # 1.5.x and 1.6.x and culls on it directly. Reading it avoids depending
    # on timeout constants that were renamed between releases.
    if not entry or len(entry) <= IDX_PT_EXPIRES:
        return True
    expires = entry[IDX_PT_EXPIRES]
    if not isinstance(expires, (int, float)):
        return True
    return time.time() > expires


def transport_path_table_entry_is_expired(destination_hash: bytes) -> bool:
    with RNS.Transport.path_table_lock:
        if destination_hash not in RNS.Transport.path_table:
            return True
        entry = RNS.Transport.path_table[destination_hash]
    return _path_table_entry_is_expired_by_reticulum_rules(entry)


def path_table_size() -> int:
    try:
        with RNS.Transport.path_table_lock:
            return len(RNS.Transport.path_table)
    except Exception:
        return 0


def prune_expired_path_table_entries(
    reticulum: Optional["ReticulumLike"] = None,
    *,
    max_to_drop: int = DEFAULT_PATH_PRUNE_BATCH,
    trigger_size: int = DEFAULT_PATH_PRUNE_TRIGGER,
) -> int:
    """Drop expired path-table entries when the table is large.

    Returns the number of paths dropped.
    """
    if max_to_drop <= 0:
        return 0
    size = path_table_size()
    if size < trigger_size:
        return 0

    expired: list[tuple[float, bytes]] = []
    try:
        with RNS.Transport.path_table_lock:
            for dest_hash, entry in RNS.Transport.path_table.items():
                if _path_table_entry_is_expired_by_reticulum_rules(entry):
                    ts = entry[IDX_PT_TIMESTAMP] if entry else 0.0
                    if not isinstance(ts, (int, float)):
                        # Corrupt entry timestamps must not crash the sort
                        # below. Treat them as oldest so they prune first.
                        ts = 0.0
                    expired.append((ts, dest_hash))
    except Exception:
        return 0

    if not expired:
        return 0

    expired.sort(key=lambda item: item[0])
    dropped = 0
    for _ts, dest_hash in expired[:max_to_drop]:
        try:
            if reticulum is not None:
                if reticulum.drop_path(dest_hash):
                    dropped += 1
            else:
                RNS.Transport.expire_path(dest_hash)
                dropped += 1
        except Exception:
            continue
    return dropped


def prune_path_table_to_soft_cap(
    reticulum: Optional["ReticulumLike"] = None,
    *,
    soft_cap: int = DEFAULT_PATH_TABLE_SOFT_CAP,
    max_to_drop: int = DEFAULT_PATH_PRUNE_BATCH,
) -> int:
    """If still over soft_cap after expiry prune, drop oldest unresponsive paths."""
    if soft_cap <= 0 or max_to_drop <= 0:
        return 0
    size = path_table_size()
    if size <= soft_cap:
        return 0

    candidates: list[tuple[float, bytes]] = []
    try:
        with RNS.Transport.path_table_lock:
            for dest_hash, entry in RNS.Transport.path_table.items():
                ts = entry[IDX_PT_TIMESTAMP] if entry else 0.0
                unresponsive = False
                try:
                    unresponsive = RNS.Transport.path_is_unresponsive(dest_hash)
                except Exception:
                    unresponsive = False
                # Prefer unresponsive, then oldest.
                rank = (0.0 if unresponsive else 1.0e12) + float(ts or 0.0)
                candidates.append((rank, dest_hash))
    except Exception:
        return 0

    if not candidates:
        return 0

    over = size - soft_cap
    budget = min(max_to_drop, over)
    candidates.sort(key=lambda item: item[0])
    dropped = 0
    for _rank, dest_hash in candidates[:budget]:
        try:
            if reticulum is not None:
                if reticulum.drop_path(dest_hash):
                    dropped += 1
            else:
                RNS.Transport.expire_path(dest_hash)
                dropped += 1
        except Exception:
            continue
    return dropped


def clean_rns_announce_cache() -> bool:
    """Ask RNS to trim on-disk announce cache files not referenced by paths."""
    try:
        owner = getattr(RNS.Transport, "owner", None)
        if owner is not None and getattr(
            owner,
            "is_connected_to_shared_instance",
            False,
        ):
            return False
        clean = getattr(RNS.Transport, "clean_cache", None)
        if callable(clean):
            clean()
            return True
        clean_ann = getattr(RNS.Transport, "clean_announce_cache", None)
        if callable(clean_ann):
            clean_ann()
            return True
    except Exception:
        return False
    return False


def should_rediscover_path(destination_hash: bytes) -> bool:
    if not RNS.Transport.has_path(destination_hash):
        return True
    if RNS.Transport.path_is_unresponsive(destination_hash):
        return True
    return transport_path_table_entry_is_expired(destination_hash)


def path_metadata_for_api(destination_hash: bytes) -> dict[str, bool]:
    has = RNS.Transport.has_path(destination_hash)
    if has is not True:
        return {
            "path_stale": True,
            "path_unresponsive": False,
        }
    stale = transport_path_table_entry_is_expired(destination_hash)
    unresponsive = RNS.Transport.path_is_unresponsive(destination_hash)
    return {
        "path_stale": stale if isinstance(stale, bool) else True,
        "path_unresponsive": unresponsive if isinstance(unresponsive, bool) else False,
    }


def lxmf_delivery_hash_bytes(identity, fallback_hash: bytes) -> bytes:
    """Return the lxmf.delivery destination hash for identity.

    Identity hashes and other-aspect destination hashes are not the
    LXMF mail address. Outbound path waits must use this dest, not the
    raw hash the UI pasted.
    """
    if identity is None:
        return fallback_hash
    try:
        computed = RNS.Destination.hash(identity, "lxmf", "delivery")
    except Exception:
        return fallback_hash
    if isinstance(computed, (bytes, bytearray)) and len(computed) == 16:
        return bytes(computed)
    return fallback_hash


_PATH_REQUEST_MIN_INTERVAL_SECONDS = 5.0
# Bound the per-destination rate-limit memory. Entries are evicted by their
# recorded request time, oldest first; clearing the whole table at the cap
# used to re-arm hundreds of destinations in one burst.
_PATH_REQUEST_RATE_LIMIT_MAX_ENTRIES = 512
# Path requests are flooded on every interface. In addition to the
# per-destination floor above, keep a process-wide token bucket so crawlers,
# propagation probes, and manual tools together cannot exceed a small mesh
# wide budget. Six requests per ten seconds is enough for interactive use and
# ordinary outbound sends, while dead-peer storms refill slowly instead of
# spraying continuously.
_PATH_REQUEST_GLOBAL_BURST = 6.0
_PATH_REQUEST_GLOBAL_WINDOW_SECONDS = 10.0
_last_path_request_at: dict[bytes, float] = {}
_path_request_lock = threading.Lock()
_path_request_global_tokens = _PATH_REQUEST_GLOBAL_BURST
_path_request_global_tokens_at: float | None = None


def reset_path_request_rate_limit_for_tests() -> None:
    global _path_request_global_tokens, _path_request_global_tokens_at
    with _path_request_lock:
        _last_path_request_at.clear()
        _path_request_global_tokens = _PATH_REQUEST_GLOBAL_BURST
        _path_request_global_tokens_at = None


def _refill_global_path_request_tokens_locked(now: float) -> None:
    global _path_request_global_tokens, _path_request_global_tokens_at

    burst = max(0.0, float(_PATH_REQUEST_GLOBAL_BURST))
    window = max(0.001, float(_PATH_REQUEST_GLOBAL_WINDOW_SECONDS))
    if _path_request_global_tokens_at is None:
        _path_request_global_tokens = burst
        _path_request_global_tokens_at = now
        return

    elapsed = max(0.0, now - _path_request_global_tokens_at)
    _path_request_global_tokens = min(
        burst,
        _path_request_global_tokens + elapsed * (burst / window),
    )
    _path_request_global_tokens_at = now


def _take_global_path_request_token_locked(now: float) -> bool:
    global _path_request_global_tokens

    _refill_global_path_request_tokens_locked(now)
    if _path_request_global_tokens < 1.0:
        return False
    _path_request_global_tokens -= 1.0
    return True


def _refund_global_path_request_token_locked() -> None:
    global _path_request_global_tokens

    burst = max(0.0, float(_PATH_REQUEST_GLOBAL_BURST))
    _path_request_global_tokens = min(burst, _path_request_global_tokens + 1.0)


def _evict_oldest_path_request_entry_locked() -> None:
    if not _last_path_request_at:
        return
    oldest = min(_last_path_request_at.items(), key=lambda item: item[1])[0]
    _last_path_request_at.pop(oldest, None)


def _request_path_once_per_window(destination_hash: bytes) -> bool:
    """Issue Transport.request_path within per-peer and mesh-wide budgets.

    Repeated sends and concurrent waiters to the same unreachable peer must
    not fan out into one path request per caller. An in-flight request already
    covers them. The window check, global token spend, and the request are
    inside the lock so threads cannot race one another into duplicate wire
    requests. Returns False when an existing in-flight request or the global
    budget covers/suppresses this call.
    """
    now = time.monotonic()
    with _path_request_lock:
        last = _last_path_request_at.get(destination_hash)
        if last is not None and now - last < _PATH_REQUEST_MIN_INTERVAL_SECONDS:
            return False
        if not _take_global_path_request_token_locked(now):
            return False
        if (
            destination_hash not in _last_path_request_at
            and len(_last_path_request_at) >= _PATH_REQUEST_RATE_LIMIT_MAX_ENTRIES
        ):
            _evict_oldest_path_request_entry_locked()
        try:
            # Record after the call: a raised request consumes neither the
            # per-destination window nor the global token, or callers retrying
            # a failed request would be suppressed without a packet emitted.
            RNS.Transport.request_path(destination_hash)
        except Exception:
            _refund_global_path_request_token_locked()
            raise
        _last_path_request_at[destination_hash] = now
        return True


def request_path_rate_limited(destination_hash: bytes) -> bool:
    """Request a path through the shared mesh-wide policy.

    Returns True only when a new wire request was emitted. False means an
    equivalent request is already inside the per-destination window or the
    global budget is temporarily empty; callers should continue their normal
    wait/timeout path rather than bypassing the policy.
    """
    return _request_path_once_per_window(destination_hash)


def prepare_fresh_path_request(
    reticulum: Optional["ReticulumLike"],
    destination_hash: bytes,
) -> str:
    """Ensure a path request is in flight if needed.

    Returns a stable label for what was done before waiting:
    reused_valid_path (no new request), path_refresh_requested (dropped
    or expired then requested), or new_path_requested (no prior path).
    """
    if not should_rediscover_path(destination_hash):
        return "reused_valid_path"
    had_path = RNS.Transport.has_path(destination_hash)
    if had_path:
        if reticulum is not None:
            with contextlib.suppress(Exception):
                reticulum.drop_path(destination_hash)
        else:
            RNS.Transport.expire_path(destination_hash)
    if not _request_path_once_per_window(destination_hash):
        return "path_request_rate_limited"
    return "path_refresh_requested" if had_path else "new_path_requested"


def nudge_path_request(destination_hash: bytes) -> bool:
    return _request_path_once_per_window(destination_hash)


def lxmf_path_wait_cap_seconds(
    destination_hash: bytes | None = None,
    reticulum: Optional["ReticulumLike"] = None,
) -> float:
    if destination_hash is not None:
        return path_response_window(destination_hash, reticulum)
    try:
        base = float(RNS.Transport.PATH_REQUEST_TIMEOUT)
    except Exception:
        base = 30.0
    return max(30.0, min(base, 120.0))


async def await_transport_path_for_outbound_lxmf(
    reticulum: Optional["ReticulumLike"],
    destination_hash_bytes: bytes,
) -> OutboundPathOutcome:
    long_w = lxmf_path_wait_cap_seconds(destination_hash_bytes, reticulum)
    try:
        short_floor = float(RNS.Transport.PATH_REQUEST_TIMEOUT)
    except Exception:
        short_floor = 15.0
    short_w = max(long_w * 0.5, short_floor)

    measure = await asyncio.to_thread(
        prepare_fresh_path_request, reticulum, destination_hash_bytes
    )
    deadline = time.time() + long_w
    while not RNS.Transport.has_path(destination_hash_bytes) and time.time() < deadline:
        await asyncio.sleep(0.1)
    if RNS.Transport.has_path(destination_hash_bytes):
        return OutboundPathOutcome(True, measure, False)

    nudge_path_request(destination_hash_bytes)
    deadline = time.time() + short_w
    while not RNS.Transport.has_path(destination_hash_bytes) and time.time() < deadline:
        await asyncio.sleep(0.1)
    ok = RNS.Transport.has_path(destination_hash_bytes)
    return OutboundPathOutcome(ok, measure, True)


class ReticulumLike(Protocol):
    def drop_path(self, destination) -> Any: ...


async def wait_for_path(
    reticulum: Optional["ReticulumLike"],
    dest_hash: bytes,
    path_wait_timeout_seconds: float,
    poll_interval: float = 0.1,
) -> bool:
    prepare_fresh_path_request(reticulum, dest_hash)
    deadline = time.monotonic() + path_wait_timeout_seconds
    while time.monotonic() < deadline:
        if RNS.Transport.has_path(dest_hash):
            return True
        await asyncio.sleep(poll_interval)
    return RNS.Transport.has_path(dest_hash)
