import asyncio
import time

import RNS

from meshchatx.src.backend.meshchat_utils import parse_lxmf_propagation_node_app_data


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

    async def check_and_update_propagation_node(self):
        # Get all propagation node announces
        announces = self.database.announces.get_announces(aspect="lxmf.propagation")

        nodes_with_hops = []
        for announce in announces:
            dest_hash_hex = announce["destination_hash"]
            dest_hash = bytes.fromhex(dest_hash_hex)

            # Check if propagation is enabled for this node
            node_data = parse_lxmf_propagation_node_app_data(announce["app_data"])
            if not node_data or not node_data.get("enabled", False):
                continue

            if RNS.Transport.has_path(dest_hash):
                hops = RNS.Transport.hops_to(dest_hash)
                nodes_with_hops.append((hops, dest_hash_hex))

        # Sort by hops (lowest first)
        nodes_with_hops.sort()

        current_node = (
            self.config.lxmf_preferred_propagation_node_destination_hash.get()
        )

        if not nodes_with_hops:
            return

        # Try nodes in order of hops until we find a reachable one
        for hops, node_hex in nodes_with_hops:
            # If current node is already the best and we have it, check if we should keep it
            if node_hex == current_node:
                # We could probe it to be sure, but for now let's assume it's fine if it's the best
                return

            # Before switching to a new "best" node, try to probe it to ensure it's actually reachable
            try:
                dest_hash = bytes.fromhex(node_hex)
                # We use a short timeout for the probe
                if await self.probe_node(dest_hash):
                    print(
                        f"Auto-propagation: Switching to better node {node_hex} ({hops} hops) for {self.context.identity_hash}",
                    )
                    self.app.set_active_propagation_node(node_hex, context=self.context)
                    self.config.lxmf_preferred_propagation_node_destination_hash.set(
                        node_hex,
                    )
                    return
                print(
                    f"Auto-propagation: Node {node_hex} announced but probe failed, trying next...",
                )
            except Exception as e:
                print(f"Auto-propagation: Error probing node {node_hex}: {e}")

    async def probe_node(self, destination_hash):
        """Probes a destination to see if it's reachable."""
        try:
            # We use the app's probe handler if available
            if (
                hasattr(self.context, "rnprobe_handler")
                and self.context.rnprobe_handler
            ):

                # Re-using the logic from RNProbeHandler but simplified
                if not RNS.Transport.has_path(destination_hash):
                    RNS.Transport.request_path(destination_hash)

                # Wait a bit for path
                timeout = 5
                start = time.time()
                while (
                    not RNS.Transport.has_path(destination_hash)
                    and time.time() - start < timeout
                ):
                    await asyncio.sleep(0.5)

                if not RNS.Transport.has_path(destination_hash):
                    return False

                # If we have a path, it's a good sign.
                # For propagation nodes, having a path is often enough to try using it.
                return True

            return RNS.Transport.has_path(destination_hash)
        except Exception:
            return False
