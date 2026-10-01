"""RNS link management for LXMFBot."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import RNS

from ._sync import run_sync

if TYPE_CHECKING:
    import logging

    from LXMF import LXMRouter

    from .config import BotConfig


class LinkMixin:
    """Outbound link requests and inbound link tracking."""

    config: BotConfig
    link_handlers: list
    links: dict
    logger: logging.Logger
    router: LXMRouter | None

    def _is_valid_destination_hex(self, destination: str) -> bool: ...

    def request_link(
        self,
        destination_hash: str,
        callback: Callable | None = None,
        app_name: str = "lxmf",
        *aspects: str,
    ):
        """Request an RNS link to a destination.

        Args:
            destination_hash: The destination hash string.
            callback: Optional callback when link is established.
            app_name: The app name for the destination (default: "lxmf").
            *aspects: Additional aspects for the destination (default: "delivery" if none provided).

        """
        if not self.config.link_support_enabled:
            raise RuntimeError("Link support is disabled in config")

        if not aspects:
            aspects = ("delivery",)

        if not self._is_valid_destination_hex(destination_hash):
            raise ValueError(f"Invalid destination hash: {destination_hash}")

        dest_bytes = bytes.fromhex(destination_hash)
        identity = RNS.Identity.recall(dest_bytes)
        if not identity:
            RNS.Transport.request_path(dest_bytes)
            raise LookupError(
                f"Identity for {destination_hash} not known, path requested",
            )

        dest = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            app_name,
            *aspects,
        )
        link = RNS.Link(dest)

        if callback:

            def _link_established(link):
                run_sync(callback, link)

            link.set_link_established_callback(_link_established)

        self._track_link_closed(link, destination_hash)

        self.links[destination_hash] = link
        return link

    def _track_link_closed(self, link, destination_hash: str) -> None:
        """Drop a link from self.links when it closes, chaining any existing callback."""
        existing = getattr(link, "link_closed", None)

        def _on_link_closed(_link):
            self.links.pop(destination_hash, None)
            if callable(existing):
                existing(_link)

        link.set_link_closed_callback(_on_link_closed)

    def on_link(self, callback: Callable):
        """Register a handler for incoming links."""
        self.link_handlers.append(callback)

    def _delivery_link_established(self, link):
        """Handle a link established on the LXMF delivery destination.

        The LXMF router's delivery_link_established wires up the packet and
        resource callbacks inbound deliveries need. It must run first, then
        the lxmfy-level link tracking and user handlers run.
        """
        if self.router is not None:
            self.router.delivery_link_established(link)
        self._link_established(link)

    def _link_established(self, link):
        """Handle an established RNS link."""
        sender = RNS.hexrep(link.destination.hash, delimit=False)
        self.links[sender] = link
        self._track_link_closed(link, sender)
        self.logger.debug("Link established with %s", sender)
        for handler in self.link_handlers:
            try:
                run_sync(handler, link)
            except Exception:
                self.logger.exception("Error in link handler")
