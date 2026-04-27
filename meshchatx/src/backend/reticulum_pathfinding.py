# SPDX-License-Identifier: 0BSD

import asyncio
import contextlib
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import RNS


@dataclass(frozen=True)
class OutboundPathOutcome:
    """Result of waiting for a Reticulum transport path before outbound LXMF."""

    path_available: bool
    prepare_measure: str
    used_nudge: bool


def format_outbound_path_finding_measure(outcome: OutboundPathOutcome) -> str:
    """Single string for storage/API: base measure, plus ``+nudge`` if a nudge was used."""
    base = outcome.prepare_measure
    if outcome.used_nudge:
        return f"{base}+nudge"
    return base


IDX_PT_TIMESTAMP = 0
IDX_PT_RVCD_IF = 5


def _path_table_entry_is_expired_by_reticulum_rules(entry) -> bool:
    ts = entry[IDX_PT_TIMESTAMP]
    attached = entry[IDX_PT_RVCD_IF]
    if attached is not None and hasattr(attached, "mode"):
        iface = RNS.Interfaces.Interface.Interface
        if attached.mode == iface.MODE_ACCESS_POINT:
            dest_exp = ts + RNS.Transport.AP_PATH_TIME
        elif attached.mode == iface.MODE_ROAMING:
            dest_exp = ts + RNS.Transport.ROAMING_PATH_TIME
        else:
            dest_exp = ts + RNS.Transport.DESTINATION_TIMEOUT
    else:
        dest_exp = ts + RNS.Transport.DESTINATION_TIMEOUT
    return time.time() > dest_exp


def transport_path_table_entry_is_expired(destination_hash: bytes) -> bool:
    with RNS.Transport.path_table_lock:
        if destination_hash not in RNS.Transport.path_table:
            return True
        entry = RNS.Transport.path_table[destination_hash]
    return _path_table_entry_is_expired_by_reticulum_rules(entry)


def should_rediscover_path(destination_hash: bytes) -> bool:
    if not RNS.Transport.has_path(destination_hash):
        return True
    if RNS.Transport.path_is_unresponsive(destination_hash):
        return True
    return transport_path_table_entry_is_expired(destination_hash)


def path_metadata_for_api(destination_hash: bytes) -> dict[str, bool]:
    has = RNS.Transport.has_path(destination_hash)
    if not has:
        return {
            "path_stale": True,
            "path_unresponsive": False,
        }
    return {
        "path_stale": transport_path_table_entry_is_expired(destination_hash),
        "path_unresponsive": RNS.Transport.path_is_unresponsive(destination_hash),
    }


def prepare_fresh_path_request(
    reticulum: Optional["ReticulumLike"], destination_hash: bytes
) -> str:
    """Ensure a path request is in flight if needed.

    Returns a stable label for what was done before waiting:
    ``reused_valid_path`` (no new request), ``path_refresh_requested`` (dropped
    or expired then requested), or ``new_path_requested`` (no prior path).
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
    RNS.Transport.request_path(destination_hash)
    return "path_refresh_requested" if had_path else "new_path_requested"


def nudge_path_request(destination_hash: bytes) -> None:
    RNS.Transport.request_path(destination_hash)


def lxmf_path_wait_cap_seconds() -> float:
    try:
        base = float(RNS.Transport.PATH_REQUEST_TIMEOUT)
    except Exception:
        base = 30.0
    return max(30.0, min(base, 120.0))


async def await_transport_path_for_outbound_lxmf(
    reticulum: Optional["ReticulumLike"],
    destination_hash_bytes: bytes,
) -> OutboundPathOutcome:
    long_w = lxmf_path_wait_cap_seconds()
    short_w = max(15.0, long_w * 0.5)

    measure = prepare_fresh_path_request(reticulum, destination_hash_bytes)
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
