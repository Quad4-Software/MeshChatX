"""Transport module for LXMFy bot framework.

This module provides transport layer functionality for establishing and managing
network connections using Reticulum Network Stack (RNS). It handles path discovery,
link establishment, and caching of active connections. The Transport class serves
as the main interface for network operations, with support for path and request
handlers.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import RNS

from .permissions import DefaultPerms


@dataclass
class PathInfo:
    """Data class to store path information.

    Attributes:
        next_hop (Optional[bytes]): The next hop in the path.
        hops (int): The number of hops in the path.
        updated_at (int): The timestamp of the last path update.

    """

    next_hop: bytes | None
    hops: int
    updated_at: int


class Transport:
    """Manages network transport for LXMFy, handling links and paths."""

    def __init__(self, bot, storage):
        """Initializes the Transport instance.

        Args:
            bot: The LXMFBot instance.
            storage: The storage backend to use for caching paths.

        """
        self.bot = bot
        self.storage = storage
        self.logger = logging.getLogger(__name__)
        self.cached_links = {}
        self.paths = {}
        self._path_handlers = []
        self._request_handlers = {}

    def register_path_handler(self, handler: Callable):
        """Registers a handler for path discovery events.

        Args:
            handler (Callable): The handler function to register.

        """
        self._path_handlers.append(handler)

    def deregister_path_handler(self, handler: Callable):
        """Deregisters a path discovery event handler.

        Args:
            handler (Callable): The handler function to deregister.

        """
        if handler in self._path_handlers:
            self._path_handlers.remove(handler)

    def register_request_handler(self, request_type: str, handler: Callable):
        """Registers a handler for specific request types.

        Args:
            request_type (str): The request type to handle.
            handler (Callable): The handler function to register.

        """
        self._request_handlers[request_type] = handler

    def deregister_request_handler(self, request_type: str):
        """Deregisters a request handler for a specific request type.

        Args:
            request_type (str): The request type to deregister.

        """
        self._request_handlers.pop(request_type, None)

    def load_paths(self):
        """Loads cached paths from storage."""
        self.paths = self.storage.get("transport:paths", {})

    def save_paths(self):
        """Saves cached paths to storage."""
        self.storage.set("transport:paths", self.paths)

    def establish_link(
        self,
        destination_hash: bytes,
        timeout: int = 15,
        app_name: str = "lxmf",
        *aspects: str,
    ) -> RNS.Link:
        """Establish a link with path discovery.

        Args:
            destination_hash (bytes): The destination hash to establish a link with.
            timeout (int): The timeout in seconds for path discovery.
            app_name: The app name for the destination (default: "lxmf").
            *aspects: Additional aspects for the destination (default: "delivery" if none provided).

        Returns:
            RNS.Link: The established RNS link.

        Raises:
            Exception: If the user does not have permission to establish links or if path lookup times out.

        """
        if not aspects:
            aspects = ("delivery",)

        sender = RNS.hexrep(destination_hash, delimit=False)
        if not self.bot.permissions.has_permission(sender, DefaultPerms.USE_BOT):
            raise Exception("User does not have permission to establish links")

        self.load_paths()
        try:
            if RNS.Transport.has_path(destination_hash):
                return self._create_link(destination_hash, timeout, app_name, *aspects)

            RNS.Transport.request_path(destination_hash)

            path_timeout = time.time() + timeout
            while time.time() < path_timeout:
                if RNS.Transport.has_path(destination_hash):
                    return self._create_link(
                        destination_hash,
                        timeout,
                        app_name,
                        *aspects,
                    )
                time.sleep(0.1)

            raise Exception("Path lookup timed out")

        except Exception as e:
            self.logger.error("Error establishing link: %s", str(e))
            raise
        finally:
            self.save_paths()

    def _create_link(
        self,
        destination_hash: bytes,
        timeout: int,
        app_name: str = "lxmf",
        *aspects: str,
    ) -> RNS.Link:
        """Create and establish a link.

        Args:
            destination_hash (bytes): The destination hash for the link.
            timeout (int): The timeout in seconds for link establishment.
            app_name: The app name for the destination.
            *aspects: Additional aspects for the destination.

        Returns:
            RNS.Link: The established RNS link.

        Raises:
            Exception: If the identity is not found or if link establishment times out.

        """
        if not aspects:
            aspects = ("delivery",)

        try:
            identity = RNS.Identity.recall(destination_hash)
            if not identity:
                raise Exception("Identity not found")

            destination = RNS.Destination(
                identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                app_name,
                *aspects,
            )

            link = RNS.Link(destination)

            start_time = time.time()
            while time.time() - start_time < timeout:
                if link.status == RNS.Link.ACTIVE:
                    self.cached_links[destination_hash] = link
                    return link
                time.sleep(0.1)

            raise Exception("Link establishment timed out")

        except Exception as e:
            self.logger.error("Error creating link: %s", str(e))
            raise

    def cleanup(self):
        """Clean up inactive links."""
        for link in list(self.cached_links.values()):
            if link.status != RNS.Link.ACTIVE:
                link.teardown()

        self.cached_links = {
            dest_hash: link
            for dest_hash, link in self.cached_links.items()
            if link.status == RNS.Link.ACTIVE
        }
