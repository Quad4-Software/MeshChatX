"""Propagation node management for LXMFBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

import RNS
from LXMF import LXMRouter

from .validation import destination_bytes

if TYPE_CHECKING:
    from .config import BotConfig


class PropagationMixin:
    """Propagation node configuration, status, and storage limits."""

    config: BotConfig
    identity: RNS.Identity
    local: RNS.Destination | None
    router: LXMRouter | None

    def _configure_propagation(self) -> None:
        if self.router and self.config.enable_propagation_node:
            try:
                self.router.enable_propagation()

                if self.config.message_storage_limit_mb > 0:
                    self.router.set_message_storage_limit(
                        megabytes=self.config.message_storage_limit_mb,
                    )
                    RNS.log(
                        f"Set propagation node message storage limit to {self.config.message_storage_limit_mb} MB",
                        RNS.LOG_INFO,
                    )

                RNS.log(
                    f"Enabled propagation node mode on {RNS.prettyhexrep(self.local.hash) if self.local else 'unknown'}",
                    RNS.LOG_INFO,
                )
            except Exception as e:
                RNS.log(
                    f"Failed to enable propagation node: {e}",
                    RNS.LOG_ERROR,
                )

        if self.router and self.config.propagation_node:
            try:
                propagation_node_bytes = bytes.fromhex(self.config.propagation_node)
                self.router.set_outbound_propagation_node(propagation_node_bytes)
                RNS.log(
                    f"Configured outbound propagation node: {RNS.prettyhexrep(propagation_node_bytes)}",
                    RNS.LOG_INFO,
                )
            except ValueError:
                RNS.log(
                    f"Invalid propagation node hash format: {self.config.propagation_node}",
                    RNS.LOG_ERROR,
                )
        elif self.router and self.config.autopeer_propagation:
            RNS.log(
                f"Auto-peering enabled for propagation nodes within {self.config.autopeer_maxdepth} hops",
                RNS.LOG_INFO,
            )
        elif (
            self.router
            and self.config.propagation_fallback_enabled
            and not self.config.enable_propagation_node
        ):
            RNS.log(
                "Propagation fallback is enabled but no propagation_node configured and autopeer_propagation is disabled. "
                "Propagated delivery will fail. Set propagation_node, enable autopeer_propagation, or disable propagation_fallback_enabled.",
                RNS.LOG_WARNING,
            )

    def get_propagation_node_status(self):
        """Get information about configured and discovered propagation nodes.

        Returns:
            dict: Dictionary with propagation node configuration and status.

        """
        if self.config.test_mode:
            return {
                "test_mode": True,
                "error": "Not available in test mode",
            }

        if not self.router:
            return {"error": "Router not initialized"}

        status = {
            "manual_node": self.config.propagation_node,
            "autopeer_enabled": self.config.autopeer_propagation,
            "autopeer_maxdepth": self.config.autopeer_maxdepth,
            "is_propagation_node": self.config.enable_propagation_node,
            "current_outbound_node": None,
            "discovered_peers": [],
        }

        current_node = self.router.get_outbound_propagation_node()
        if current_node:
            status["current_outbound_node"] = RNS.hexrep(current_node, delimit=False)

        if hasattr(self.router, "peers") and self.router.peers:
            status["discovered_peers"] = [
                {
                    "hash": RNS.hexrep(peer_hash, delimit=False),
                    "hops": RNS.Transport.hops_to(peer_hash),
                }
                for peer_hash in self.router.peers
            ]

        return status

    def set_propagation_node(self, node_hash: str):
        """Manually set the outbound propagation node.

        Args:
            node_hash: The destination hash of the propagation node.

        """
        if self.config.test_mode:
            RNS.log("Cannot set propagation node in test mode", RNS.LOG_WARNING)
            return

        if not self.router:
            RNS.log("Router not initialized", RNS.LOG_WARNING)
            return

        try:
            propagation_node_bytes = bytes.fromhex(node_hash)
            self.router.set_outbound_propagation_node(propagation_node_bytes)
            self.config.propagation_node = node_hash
            RNS.log(
                f"Set outbound propagation node to: {RNS.prettyhexrep(propagation_node_bytes)}",
                RNS.LOG_INFO,
            )
        except ValueError:
            RNS.log(
                f"Invalid propagation node hash format: {node_hash}",
                RNS.LOG_ERROR,
            )
            raise

    def set_message_storage_limit(self, megabytes: float):
        """Set the message storage limit for propagation node mode.

        Args:
            megabytes: Storage limit in megabytes. Set to 0 for unlimited.

        """
        if self.config.test_mode:
            RNS.log("Cannot set storage limit in test mode", RNS.LOG_WARNING)
            return

        if not self.config.enable_propagation_node:
            RNS.log(
                "Storage limit only applies when running as a propagation node",
                RNS.LOG_WARNING,
            )
            return

        if not self.router:
            RNS.log("Router not initialized", RNS.LOG_WARNING)
            return

        try:
            if megabytes <= 0:
                self.router.set_message_storage_limit()
                self.config.message_storage_limit_mb = 0
                RNS.log("Removed message storage limit (unlimited)", RNS.LOG_INFO)
            else:
                self.router.set_message_storage_limit(megabytes=megabytes)
                self.config.message_storage_limit_mb = megabytes
                RNS.log(
                    f"Set message storage limit to {megabytes} MB",
                    RNS.LOG_INFO,
                )
        except Exception as e:
            RNS.log(
                f"Failed to set message storage limit: {e}",
                RNS.LOG_ERROR,
            )
            raise

    def get_propagation_storage_stats(self):
        """Get storage statistics for propagation node mode.

        Returns:
            dict: Dictionary with storage statistics or None if not a propagation node.

        """
        if self.config.test_mode:
            return {"test_mode": True, "error": "Not available in test mode"}

        if not self.config.enable_propagation_node:
            return {
                "is_propagation_node": False,
                "error": "Not running as propagation node",
            }

        if not self.router:
            return {"error": "Router not initialized"}

        try:
            storage_size = self.router.message_storage_size()
            raw_limit = self.router.message_storage_limit
            storage_limit = raw_limit() if callable(raw_limit) else raw_limit
            if not isinstance(storage_limit, int):
                storage_limit = None

            return {
                "is_propagation_node": True,
                "storage_size_bytes": storage_size,
                "storage_size_mb": storage_size / (1000 * 1000) if storage_size else 0,
                "storage_limit_bytes": storage_limit,
                "storage_limit_mb": storage_limit / (1000 * 1000)
                if storage_limit
                else None,
                "utilization_percent": (storage_size / storage_limit * 100)
                if (storage_limit and storage_size)
                else 0,
                "message_count": len(self.router.propagation_entries)
                if hasattr(self.router, "propagation_entries")
                else 0,
            }
        except Exception as e:
            return {"error": f"Failed to get stats: {e}"}

    def sync_propagation_node(self, max_messages: int | None = None) -> bool:
        """Request stored messages from the outbound propagation node.

        Establishes a link to the configured propagation node if needed
        and downloads messages held for this bot's identity. Delivery
        completes asynchronously through the normal inbound pipeline.

        Args:
            max_messages: Maximum messages to request. None requests all.

        Returns False when no router, identity, or outbound propagation
        node is configured.
        """
        if self.router is None or self.router.outbound_propagation_node is None:
            return False
        limit = max_messages if max_messages is not None else LXMRouter.PR_ALL_MESSAGES
        self.router.request_messages_from_propagation_node(self.identity, limit)
        return True

    def cancel_propagation_sync(self) -> bool:
        """Tear down an in-progress propagation node sync."""
        if self.router is None:
            return False
        self.router.cancel_propagation_node_requests()
        return True

    def get_propagation_stats(self) -> dict | None:
        """Compile propagation node statistics.

        Returns None when this bot is not running as a propagation node.
        """
        if self.router is None:
            return None
        return self.router.compile_stats()

    def set_retain_on_node(self, retain: bool) -> bool:
        """Keep copies of synced messages on the propagation node.

        Only meaningful when this bot runs as a propagation node.
        """
        if self.router is None:
            return False
        self.router.set_retain_node_lxms(retain)
        return True

    def announce_propagation_node(self) -> bool:
        """Announce this node as a propagation node.

        Returns False unless the router is running with propagation
        enabled, since the announce requires the propagation destination.
        """
        if self.router is None or not getattr(self.router, "propagation_node", False):
            return False
        self.router.announce_propagation_node()
        return True

    def allow_control_identity(self, destination: str) -> bool:
        """Allow an identity to issue control requests to this node.

        Control requests include peer sync and unpeer operations on a
        propagation node. Returns False on an invalid hash.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        self.router.allow_control(dest)
        return True

    def disallow_control_identity(self, destination: str) -> bool:
        """Revoke control request access for an identity.

        Operates on the list directly because LXMRouter.disallow_control
        pops by index in LXMF 1.1.1 and raises instead of removing.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        if dest in self.router.control_allowed_list:
            self.router.control_allowed_list.remove(dest)
            return True
        return False
