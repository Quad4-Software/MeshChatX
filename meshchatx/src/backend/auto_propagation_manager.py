# SPDX-License-Identifier: 0BSD

import asyncio
import contextlib
import time

import RNS
from LXMF.LXMRouter import LXMRouter

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.meshchat_utils import parse_lxmf_propagation_node_app_data
from meshchatx.src.backend import reticulum_pathfinding

_PROP_FAILURE_STATES = frozenset(
    {
        LXMRouter.PR_NO_PATH,
        LXMRouter.PR_LINK_FAILED,
        LXMRouter.PR_TRANSFER_FAILED,
        LXMRouter.PR_NO_IDENTITY_RCVD,
        LXMRouter.PR_NO_ACCESS,
        LXMRouter.PR_FAILED,
    },
)

PATH_WAIT_SECONDS = 40.0
SYNC_PROBE_TIMEOUT_SECONDS = 120.0
POLL_INTERVAL_SECONDS = 0.2


class AutoPropagationManager:
    def __init__(self, app, context):
        self.app = app
        self.context = context
        self.config = context.config
        self.database = context.database
        self.running = False
        self._last_check = 0
        self._check_interval = 300  # 5 minutes

    def stop(self):
        self.running = False

    async def _run(self):
        # Wait a bit after startup to allow discovers to come in
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
                    f"Error in AutoPropagationManager for {self.context.identity_hash}: {e}",
                )

            await asyncio.sleep(self._check_interval)

    async def _wait_for_path(self, dest_hash: bytes, timeout: float) -> bool:
        r = self.app.reticulum if self.app and hasattr(self.app, "reticulum") else None
        return await reticulum_pathfinding.wait_for_path(
            r,
            dest_hash,
            timeout,
            poll_interval=POLL_INTERVAL_SECONDS,
        )

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

        # Ensure any previous sync is fully cancelled and state is idle
        self.app.stop_propagation_node_sync(context=ctx)
        settle_deadline = time.monotonic() + 5.0
        while time.monotonic() < settle_deadline:
            if router.propagation_transfer_state == LXMRouter.PR_IDLE:
                break
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        else:
            with contextlib.suppress(Exception):
                router.propagation_transfer_state = LXMRouter.PR_IDLE

        try:
            router.set_outbound_propagation_node(dest)
        except Exception:
            return False

        router.request_messages_from_propagation_node(ctx.identity)

        deadline = time.monotonic() + SYNC_PROBE_TIMEOUT_SECONDS

        # Wait for the sync to actually start (leave idle)
        while time.monotonic() < deadline:
            state = router.propagation_transfer_state
            if state in _PROP_FAILURE_STATES:
                self.app.stop_propagation_node_sync(context=ctx)
                return False
            if state != LXMRouter.PR_IDLE:
                break
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        else:
            # Never left idle -> failed to start
            self.app.stop_propagation_node_sync(context=ctx)
            return False

        # Wait for the sync to finish (return to idle)
        while time.monotonic() < deadline:
            state = router.propagation_transfer_state
            if state in _PROP_FAILURE_STATES:
                self.app.stop_propagation_node_sync(context=ctx)
                return False
            if state == LXMRouter.PR_IDLE:
                # Success: we left idle and now we're back
                self.app.stop_propagation_node_sync(context=ctx)
                return True
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

        self.app.stop_propagation_node_sync(context=ctx)
        return False

    async def check_and_update_propagation_node(self):
        ctx = self.context
        router = ctx.message_router
        if not router:
            return

        previous_hex = (
            self.config.lxmf_preferred_propagation_node_destination_hash.get()
        )

        # If a sync is in progress, only interrupt it when the current node
        # appears unreachable or the path is stale/unresponsive.  This prevents
        # getting stuck on a node we cannot actually reach.
        if router.propagation_transfer_state != LXMRouter.PR_IDLE:
            current_path_ok = False
            if previous_hex:
                try:
                    current_dest = bytes.fromhex(previous_hex)
                    current_has_path = RNS.Transport.has_path(current_dest)
                    current_path_ok = (
                        current_has_path
                        and not RNS.Transport.path_is_unresponsive(current_dest)
                        and not reticulum_pathfinding.transport_path_table_entry_is_expired(
                            current_dest,
                        )
                    )
                except Exception:
                    pass
            if current_path_ok:
                # Sync is likely making progress – let it finish.
                return
            # Current node is unreachable – stop the stuck sync so we can
            # look for a working alternative.
            self.app.stop_propagation_node_sync(context=ctx)
            # Wait briefly for the router to settle back to idle before we
            # start probing other nodes.
            settle_deadline = time.monotonic() + 5.0
            while time.monotonic() < settle_deadline:
                if router.propagation_transfer_state == LXMRouter.PR_IDLE:
                    break
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            else:
                with contextlib.suppress(Exception):
                    router.propagation_transfer_state = LXMRouter.PR_IDLE

        announces = self.database.announces.get_announces(aspect="lxmf.propagation")

        best_by_hex: dict[str, tuple[int, str]] = {}
        for announce in announces:
            dest_hex = announce["destination_hash"]
            node_data = parse_lxmf_propagation_node_app_data(announce["app_data"])
            if not node_data or not node_data.get("enabled", False):
                continue
            try:
                dest_hash = bytes.fromhex(dest_hex)
            except ValueError:
                continue
            if RNS.Transport.has_path(dest_hash):
                hops = RNS.Transport.hops_to(dest_hash)
            else:
                hops = 10**9
            prev = best_by_hex.get(dest_hex)
            if prev is None or hops < prev[0]:
                best_by_hex[dest_hex] = (hops, dest_hex)

        sorted_candidates = sorted(best_by_hex.values(), key=lambda x: x[0])
        if not sorted_candidates:
            return

        ordered: list[tuple[int, str]] = []
        seen_hex: set[str] = set()
        if previous_hex and previous_hex in best_by_hex:
            ordered.append(best_by_hex[previous_hex])
            seen_hex.add(previous_hex)
        for item in sorted_candidates:
            if item[1] not in seen_hex:
                ordered.append(item)
                seen_hex.add(item[1])

        for _hops, node_hex in ordered:
            try:
                dest_hash = bytes.fromhex(node_hex)
            except ValueError:
                continue

            if not await self._wait_for_path(dest_hash, PATH_WAIT_SECONDS):
                continue

            if not await self._probe_propagation_sync(node_hex):
                continue

            if node_hex != previous_hex:
                print(
                    f"Auto-propagation: Switching to verified node {node_hex} "
                    f"for {self.context.identity_hash}",
                )
                self.app.set_active_propagation_node(node_hex, context=self.context)
                self.config.lxmf_preferred_propagation_node_destination_hash.set(
                    node_hex,
                )
                AsyncUtils.run_async(
                    self.app.send_config_to_websocket_clients(context=ctx),
                )
            return

        # None of the candidates worked.  If the previously-selected node is
        # still unreachable, clear it rather than restoring a broken node.
        if previous_hex:
            try:
                previous_dest = bytes.fromhex(previous_hex)
                if RNS.Transport.has_path(previous_dest):
                    self.app.set_active_propagation_node(
                        previous_hex, context=self.context
                    )
                    return
            except Exception:
                pass
            self.app.remove_active_propagation_node(context=self.context)
        else:
            self.app.remove_active_propagation_node(context=self.context)
