# SPDX-License-Identifier: 0BSD

"""Auto-select a usable LXMF propagation peer from local announces and paths.

Zen of Reticulum notes for this manager:

- There is no privileged propagation center. Candidates are destination hashes
  heard via lxmf.propagation announces, plus local memory of peers that already
  proved reachable for this identity.
- Trust is experience: a usable RNS path and a successful LXMF sync probe, not a
  hostname, directory, or fixed server role.
- Airtime is scarce: prefer sticky verified peers, cool down failures, probe at
  most a few peers per cycle, and request at most one message during a probe.
- Delay is normal: missing paths request rediscovery and keep recoverable state
  instead of clearing the preferred hash on the first blip.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any

import RNS
from LXMF.LXMRouter import LXMRouter

from meshchatx.src.backend import reticulum_pathfinding
from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.meshchat_utils import (
    parse_lxmf_propagation_node_app_data,
    propagation_sync_idle_like,
)

_PROP_FAILURE_STATES = frozenset(
    {
        LXMRouter.PR_NO_PATH,
        LXMRouter.PR_LINK_FAILED,
        LXMRouter.PR_TRANSFER_FAILED,
        LXMRouter.PR_NO_IDENTITY_RCVD,
        LXMRouter.PR_NO_ACCESS,
        LXMRouter.PR_FAILED,
        LXMRouter.PR_PATH_TIMEOUT,
    },
)
_PROP_SUCCESS_STATES = frozenset(
    {
        LXMRouter.PR_IDLE,
        LXMRouter.PR_COMPLETE,
    },
)

PATH_WAIT_SECONDS = 40.0
SYNC_PROBE_TIMEOUT_SECONDS = 120.0
POLL_INTERVAL_SECONDS = 0.2
CHECK_INTERVAL_SECONDS = 300
# Keep a working preferred peer without full sync probes this often.
REVERIFY_SECONDS = 1800
# Avoid hammering peers that just failed a sync probe.
FAILURE_COOLDOWN_SECONDS = 600
# Do not switch away from a working preferred peer for a tiny hop gain.
HOP_SWITCH_HYSTERESIS = 2
# Clear the active outbound peer only after repeated verify failures.
MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR = 3
MAX_MEMORY_NODES = 12
# Scarcity: do not walk the whole announce table in one cycle.
MAX_PROBES_PER_CYCLE = 2
# Scarcity: prove sync/access without pulling a bulk mailbox.
PROBE_MAX_MESSAGES = 1
UNKNOWN_HOPS = 10**9
MEMORY_CONFIG_KEY = "lxmf_preferred_propagation_node_memory"


def _pretty_dest(node_hex: str) -> str:
    try:
        return RNS.prettyhexrep(bytes.fromhex(node_hex))
    except Exception:
        return "<invalid>"


class AutoPropagationManager:
    def __init__(self, app, context):
        self.app = app
        self.context = context
        self.config = context.config
        self.database = context.database
        self.running = False
        self._check_interval = CHECK_INTERVAL_SECONDS
        # In-process cache mirrors identity-scoped config memory.
        self._memory: dict[str, dict[str, Any]] = {}
        self._load_memory()

    def stop(self):
        self.running = False

    async def _run(self):
        # Wait after startup so announces and paths can settle.
        await asyncio.sleep(10)
        self.running = True

        while self.running and self.context.running:
            try:
                if self.config.lxmf_preferred_propagation_node_auto_select.get():
                    await self.check_and_update_propagation_node()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(
                    f"Error in AutoPropagationManager: {type(e).__name__}: {e}",
                )

            await asyncio.sleep(self._check_interval)

    def _load_memory(self) -> None:
        raw = None
        with contextlib.suppress(Exception):
            raw = self.config.get(MEMORY_CONFIG_KEY, default_value=None)
        self._memory = self._parse_memory(raw)

    def _save_memory(self) -> None:
        trimmed = self._trim_memory(self._memory)
        self._memory = trimmed
        payload = json.dumps(trimmed, separators=(",", ":"), sort_keys=True)
        with contextlib.suppress(Exception):
            self.config.set(MEMORY_CONFIG_KEY, payload)

    @staticmethod
    def _parse_memory(raw: Any) -> dict[str, dict[str, Any]]:
        if not raw:
            return {}
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, json.JSONDecodeError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            try:
                bytes.fromhex(key)
            except ValueError:
                continue
            if len(key) != (RNS.Identity.TRUNCATED_HASHLENGTH // 8) * 2:
                continue
            out[key.lower()] = {
                "successes": int(value.get("successes") or 0),
                "failures": int(value.get("failures") or 0),
                "consecutive_failures": int(value.get("consecutive_failures") or 0),
                "last_success_at": int(value.get("last_success_at") or 0),
                "last_failure_at": int(value.get("last_failure_at") or 0),
                "last_hops": int(value.get("last_hops") or UNKNOWN_HOPS),
            }
        return out

    @staticmethod
    def _trim_memory(memory: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        if len(memory) <= MAX_MEMORY_NODES:
            return memory

        def rank(item: tuple[str, dict[str, Any]]) -> tuple[int, int, int]:
            entry = item[1]
            return (
                int(entry.get("last_success_at") or 0),
                int(entry.get("successes") or 0),
                -int(entry.get("consecutive_failures") or 0),
            )

        keep = sorted(memory.items(), key=rank, reverse=True)[:MAX_MEMORY_NODES]
        return {key: value for key, value in keep}

    def _memory_entry(self, node_hex: str) -> dict[str, Any]:
        return self._memory.setdefault(
            node_hex.lower(),
            {
                "successes": 0,
                "failures": 0,
                "consecutive_failures": 0,
                "last_success_at": 0,
                "last_failure_at": 0,
                "last_hops": UNKNOWN_HOPS,
            },
        )

    def _record_success(self, node_hex: str, hops: int) -> None:
        entry = self._memory_entry(node_hex)
        entry["successes"] = int(entry.get("successes") or 0) + 1
        entry["consecutive_failures"] = 0
        entry["last_success_at"] = int(time.time())
        entry["last_hops"] = (
            hops if hops < UNKNOWN_HOPS else entry.get("last_hops", UNKNOWN_HOPS)
        )
        self._save_memory()

    def _record_failure(self, node_hex: str) -> None:
        entry = self._memory_entry(node_hex)
        entry["failures"] = int(entry.get("failures") or 0) + 1
        entry["consecutive_failures"] = int(entry.get("consecutive_failures") or 0) + 1
        entry["last_failure_at"] = int(time.time())
        self._save_memory()

    def _in_failure_cooldown(self, node_hex: str, now: float | None = None) -> bool:
        entry = self._memory.get(node_hex.lower())
        if not entry:
            return False
        if int(entry.get("consecutive_failures") or 0) <= 0:
            return False
        last_failure = int(entry.get("last_failure_at") or 0)
        if last_failure <= 0:
            return False
        clock = time.time() if now is None else now
        return (clock - last_failure) < FAILURE_COOLDOWN_SECONDS

    def _recently_verified(self, node_hex: str, now: float | None = None) -> bool:
        entry = self._memory.get(node_hex.lower())
        if not entry:
            return False
        if int(entry.get("consecutive_failures") or 0) > 0:
            return False
        last_success = int(entry.get("last_success_at") or 0)
        if last_success <= 0:
            return False
        clock = time.time() if now is None else now
        return (clock - last_success) < REVERIFY_SECONDS

    @staticmethod
    def _path_quality_ok(dest_hash: bytes) -> bool:
        try:
            if not RNS.Transport.has_path(dest_hash):
                return False
            if RNS.Transport.path_is_unresponsive(dest_hash):
                return False
            if reticulum_pathfinding.transport_path_table_entry_is_expired(dest_hash):
                return False
            return True
        except Exception:
            return False

    def _hops_to(self, dest_hash: bytes) -> int:
        try:
            if RNS.Transport.has_path(dest_hash):
                hops = RNS.Transport.hops_to(dest_hash)
                if isinstance(hops, int) and hops >= 0:
                    return hops
        except Exception:
            pass
        return UNKNOWN_HOPS

    def _candidate_score(
        self,
        node_hex: str,
        hops: int,
        path_ok: bool,
        from_announce: bool,
        now: float,
    ) -> float:
        """Lower is better. Announced presence beats memory-only ghosts."""
        score = float(hops if hops < UNKNOWN_HOPS else 64)
        if not path_ok:
            score += 80.0
        if not from_announce:
            # Announces are presence. Memory is only a recovery hint.
            score += 12.0

        entry = self._memory.get(node_hex.lower())
        if entry:
            successes = int(entry.get("successes") or 0)
            consecutive = int(entry.get("consecutive_failures") or 0)
            last_success = int(entry.get("last_success_at") or 0)
            score -= min(successes, 8) * 0.75
            score += consecutive * 6.0
            if last_success > 0:
                age = max(0.0, now - last_success)
                score -= max(0.0, 4.0 - (age / 900.0))
            if self._in_failure_cooldown(node_hex, now=now):
                score += 1000.0
        return score

    async def _wait_for_usable_path(self, dest_hash: bytes, timeout: float) -> bool:
        r = self.app.reticulum if self.app and hasattr(self.app, "reticulum") else None
        reticulum_pathfinding.prepare_fresh_path_request(r, dest_hash)
        deadline = time.monotonic() + timeout
        nudged = False
        while time.monotonic() < deadline:
            if self._path_quality_ok(dest_hash):
                return True
            try:
                has_path = RNS.Transport.has_path(dest_hash)
            except Exception:
                has_path = False
            if has_path and not nudged:
                # Stale or unresponsive path: drop and request again once.
                if r is not None:
                    with contextlib.suppress(Exception):
                        r.drop_path(dest_hash)
                else:
                    with contextlib.suppress(Exception):
                        RNS.Transport.expire_path(dest_hash)
                reticulum_pathfinding.nudge_path_request(dest_hash)
                nudged = True
            elif (
                not has_path
                and not nudged
                and (deadline - time.monotonic()) < (timeout * 0.45)
            ):
                reticulum_pathfinding.nudge_path_request(dest_hash)
                nudged = True
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        return self._path_quality_ok(dest_hash)

    async def _settle_router_idle(self, router, seconds: float = 5.0) -> None:
        settle_deadline = time.monotonic() + seconds
        while time.monotonic() < settle_deadline:
            if propagation_sync_idle_like(router.propagation_transfer_state):
                with contextlib.suppress(Exception):
                    if router.propagation_transfer_state == LXMRouter.PR_COMPLETE:
                        router.propagation_transfer_state = LXMRouter.PR_IDLE
                return
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        with contextlib.suppress(Exception):
            router.propagation_transfer_state = LXMRouter.PR_IDLE

    async def _probe_propagation_sync(self, node_hex: str) -> bool:
        ctx = self.context
        router = ctx.message_router
        if not router:
            return False
        try:
            dest = bytes.fromhex(node_hex)
            if len(dest) != RNS.Identity.TRUNCATED_HASHLENGTH // 8:
                return False
        except Exception:
            return False

        # Cancel any previous sync and wait for idle so stale non-idle state
        # cannot look like a successful probe.
        self.app.stop_propagation_node_sync(context=ctx)
        await self._settle_router_idle(router)

        try:
            router.set_outbound_propagation_node(dest)
        except Exception:
            return False

        # LXMF needs a recalled identity to open the propagation link.
        with contextlib.suppress(Exception):
            if RNS.Identity.recall(dest) is None:
                RNS.Transport.request_path(dest)

        # Prove access with a tiny transfer budget. Full mailbox sync belongs
        # to the operator-triggered or interval sync paths, not auto-select.
        router.request_messages_from_propagation_node(
            ctx.identity,
            max_messages=PROBE_MAX_MESSAGES,
        )

        deadline = time.monotonic() + SYNC_PROBE_TIMEOUT_SECONDS
        left_idle = False

        while time.monotonic() < deadline:
            state = router.propagation_transfer_state
            if state in _PROP_FAILURE_STATES:
                self.app.stop_propagation_node_sync(context=ctx)
                return False
            if state not in _PROP_SUCCESS_STATES:
                left_idle = True
                break
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        else:
            self.app.stop_propagation_node_sync(context=ctx)
            return False

        while time.monotonic() < deadline:
            state = router.propagation_transfer_state
            if state in _PROP_FAILURE_STATES:
                self.app.stop_propagation_node_sync(context=ctx)
                return False
            # LXMF ends a successful sync at PR_COMPLETE (not always PR_IDLE).
            if left_idle and state in _PROP_SUCCESS_STATES:
                self.app.stop_propagation_node_sync(context=ctx)
                return True
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

        self.app.stop_propagation_node_sync(context=ctx)
        return False

    def _collect_candidates(self) -> tuple[dict[str, int], set[str]]:
        """Return destination_hex -> hops, plus the set heard via announces."""
        announces = self.database.announces.get_announces(aspect="lxmf.propagation")
        best_by_hex: dict[str, int] = {}
        announced: set[str] = set()

        for announce in announces or []:
            dest_hex = announce.get("destination_hash")
            if not isinstance(dest_hex, str):
                continue
            dest_hex = dest_hex.lower()
            node_data = parse_lxmf_propagation_node_app_data(announce.get("app_data"))
            if not node_data or not node_data.get("enabled", False):
                continue
            try:
                dest_hash = bytes.fromhex(dest_hex)
            except ValueError:
                continue
            hops = self._hops_to(dest_hash)
            prev = best_by_hex.get(dest_hex)
            if prev is None or hops < prev:
                best_by_hex[dest_hex] = hops
            announced.add(dest_hex)

        # Remembered peers stay candidates when announces aged out, but they are
        # recovery hints only, never a global registry.
        now = time.time()
        for node_hex, entry in self._memory.items():
            if node_hex in best_by_hex:
                continue
            if int(entry.get("successes") or 0) <= 0:
                continue
            if int(entry.get("consecutive_failures") or 0) >= (
                MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR
            ):
                continue
            last_success = int(entry.get("last_success_at") or 0)
            if last_success <= 0 or (now - last_success) > (REVERIFY_SECONDS * 8):
                continue
            try:
                dest_hash = bytes.fromhex(node_hex)
            except ValueError:
                continue
            best_by_hex[node_hex] = self._hops_to(dest_hash)

        return best_by_hex, announced

    def _ordered_candidates(
        self,
        best_by_hex: dict[str, int],
        announced: set[str],
        previous_hex: str | None,
    ) -> list[tuple[float, int, str]]:
        now = time.time()
        scored: list[tuple[float, int, str]] = []
        for node_hex, hops in best_by_hex.items():
            try:
                dest_hash = bytes.fromhex(node_hex)
            except ValueError:
                continue
            path_ok = self._path_quality_ok(dest_hash)
            score = self._candidate_score(
                node_hex,
                hops,
                path_ok,
                node_hex in announced,
                now,
            )
            scored.append((score, hops, node_hex))

        scored.sort(key=lambda item: (item[0], item[1], item[2]))

        ordered: list[tuple[float, int, str]] = []
        seen: set[str] = set()
        if previous_hex and previous_hex in best_by_hex:
            for item in scored:
                if item[2] == previous_hex:
                    ordered.append(item)
                    seen.add(previous_hex)
                    break
        for item in scored:
            if item[2] not in seen:
                ordered.append(item)
                seen.add(item[2])
        return ordered

    def _should_keep_previous_without_probe(
        self,
        previous_hex: str | None,
        best_by_hex: dict[str, int],
        ordered: list[tuple[float, int, str]],
    ) -> bool:
        if not previous_hex or previous_hex not in best_by_hex:
            return False
        try:
            dest_hash = bytes.fromhex(previous_hex)
        except ValueError:
            return False
        if not self._path_quality_ok(dest_hash):
            return False
        if not self._recently_verified(previous_hex):
            return False

        previous_hops = best_by_hex[previous_hex]
        # Stay sticky unless another candidate is clearly closer and path-usable.
        for _score, hops, node_hex in ordered:
            if node_hex == previous_hex:
                continue
            if hops >= UNKNOWN_HOPS:
                continue
            try:
                other_hash = bytes.fromhex(node_hex)
            except ValueError:
                continue
            if not self._path_quality_ok(other_hash):
                continue
            if hops + HOP_SWITCH_HYSTERESIS < previous_hops:
                return False
            break
        return True

    async def check_and_update_propagation_node(self):
        ctx = self.context
        router = ctx.message_router
        if not router:
            return

        previous_hex = (
            self.config.lxmf_preferred_propagation_node_destination_hash.get()
        )
        if isinstance(previous_hex, str):
            previous_hex = previous_hex.lower()
        else:
            previous_hex = None

        # If a sync is in progress, only interrupt when the current peer path
        # looks unreachable or stale. PR_COMPLETE is idle-like (finished).
        if not propagation_sync_idle_like(router.propagation_transfer_state):
            current_path_ok = False
            if previous_hex:
                try:
                    current_dest = bytes.fromhex(previous_hex)
                    current_path_ok = self._path_quality_ok(current_dest)
                except Exception:
                    current_path_ok = False
            if current_path_ok:
                return
            self.app.stop_propagation_node_sync(context=ctx)
            await self._settle_router_idle(router)

        best_by_hex, announced = self._collect_candidates()
        if not best_by_hex:
            return

        ordered = self._ordered_candidates(best_by_hex, announced, previous_hex)

        if self._should_keep_previous_without_probe(previous_hex, best_by_hex, ordered):
            # Keep the verified preferred peer without a disruptive sync probe.
            outbound = None
            with contextlib.suppress(Exception):
                outbound = router.get_outbound_propagation_node()
            if outbound is None or (
                isinstance(outbound, (bytes, bytearray))
                and outbound.hex() != previous_hex
            ):
                self.app.set_active_propagation_node(previous_hex, context=self.context)
            else:
                with contextlib.suppress(Exception):
                    RNS.Transport.request_path(bytes.fromhex(previous_hex))
            return

        probed_any = False
        probes = 0
        for _score, hops, node_hex in ordered:
            if probes >= MAX_PROBES_PER_CYCLE:
                break
            if self._in_failure_cooldown(node_hex) and node_hex != previous_hex:
                continue
            try:
                dest_hash = bytes.fromhex(node_hex)
            except ValueError:
                continue

            if not await self._wait_for_usable_path(dest_hash, PATH_WAIT_SECONDS):
                self._record_failure(node_hex)
                continue

            probes += 1
            probed_any = True
            if not await self._probe_propagation_sync(node_hex):
                self._record_failure(node_hex)
                continue

            hops = self._hops_to(dest_hash)
            self._record_success(node_hex, hops)
            if node_hex != previous_hex:
                print(
                    "Auto-propagation: switching to verified peer "
                    f"{_pretty_dest(node_hex)}",
                )
            self.app.set_active_propagation_node(node_hex, context=self.context)
            self.config.lxmf_preferred_propagation_node_destination_hash.set(node_hex)
            AsyncUtils.run_async(
                self.app.send_config_to_websocket_clients(context=ctx),
            )
            return

        # Nothing verified this cycle. Keep a recently-good preferred hash when
        # possible so the next check can retry without wiping operator state.
        if previous_hex:
            entry = self._memory.get(previous_hex, {})
            consecutive = int(entry.get("consecutive_failures") or 0)
            if consecutive < MAX_CONSECUTIVE_FAILURES_BEFORE_CLEAR:
                with contextlib.suppress(Exception):
                    RNS.Transport.request_path(bytes.fromhex(previous_hex))
                self.app.set_active_propagation_node(previous_hex, context=self.context)
                return

        if probed_any or previous_hex:
            self.app.remove_active_propagation_node(context=self.context)
            if previous_hex:
                self.config.lxmf_preferred_propagation_node_destination_hash.set(None)
                AsyncUtils.run_async(
                    self.app.send_config_to_websocket_clients(context=ctx),
                )
