"""Delivery announce handling for LXMFBot."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import RNS
import RNS.vendor.umsgpack as msgpack

from .validation import destination_bytes

if TYPE_CHECKING:
    import logging

    from .config import BotConfig

BOT_DISPLAY_NAME_FILE = "bot_display_name.txt"


class AnnounceMixin:
    """Display name resolution and LXMF delivery announces."""

    config: BotConfig
    config_path: str
    local: RNS.Destination | None
    logger: logging.Logger
    announce_enabled: bool
    announce_time: int

    @property
    def name(self) -> str:
        """Bot display name used for LXMF when no file override applies."""
        return self.config.name

    @name.setter
    def name(self, value: str) -> None:
        self.config.name = value
        self._sync_delivery_display_name()

    def _effective_announce_display_name(self) -> str:
        """Resolve the display name for lxmf/delivery announce app_data."""
        if self.config.announce_display_name_file:
            path = os.path.join(
                self.config_path,
                self.config.announce_display_name_file,
            )
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read().strip()
                    if text:
                        return text
                except OSError:
                    pass

        default_path = os.path.join(self.config_path, BOT_DISPLAY_NAME_FILE)
        if os.path.isfile(default_path):
            try:
                with open(default_path, encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    return text
            except OSError:
                pass

        return self.config.name or "LXMFBot"

    def _sync_delivery_display_name(self) -> None:
        if not self.local:
            return
        # RNS Destination.display_name is set dynamically at runtime
        setattr(  # noqa: B010 - direct assignment is untyped on Destination
            self.local,
            "display_name",
            self._effective_announce_display_name(),
        )

    def announce_now(self, force: bool = False) -> None:
        """Send an LXMF delivery announce using the current display name.

        LXMF builds delivery announce app_data from the destination display name
        at announce time; this method refreshes that from :attr:`name`, optional
        ``announce_display_name_file``, or ``bot_display_name.txt`` before
        sending.

        Args:
            force: If True, send now and skip the on-disk announce interval
                throttle (still respects ``announce_enabled`` and requires a
                running router). If False, behave like the periodic announce
                task (honours ``announce_time`` and the throttle file).

        """
        if self.config.test_mode or not self.local:
            RNS.log("Announce skipped (test mode or no router)", RNS.LOG_DEBUG)
            return
        if not self.announce_enabled:
            RNS.log("Announcements disabled", RNS.LOG_DEBUG)
            return
        if not force and self.announce_time == 0:
            RNS.log("Announcements disabled", RNS.LOG_DEBUG)
            return

        announce_path = os.path.join(self.config_path, "announce")
        if not force:
            if os.path.isfile(announce_path):
                with open(announce_path) as f:
                    try:
                        announce = int(f.readline())
                    except ValueError:
                        announce = 0
            else:
                announce = 0

            if announce > int(time.time()):
                RNS.log("Recent announcement", RNS.LOG_DEBUG)
                return

        self._sync_delivery_display_name()
        self.local.announce()

        try:
            with open(announce_path, "w+") as af:
                interval = max(0, self.announce_time)
                af.write(str(int(time.time()) + interval))
        except OSError as e:
            self.logger.warning("Could not write announce throttle file: %s", e)

        RNS.log(
            f"Announcement sent, next announce in {self.announce_time} seconds",
            RNS.LOG_INFO,
        )

    def get_peer_app_data(self, destination: str) -> bytes | None:
        """Recall the app_data a destination last announced, or None.

        App data is whatever the announcing app attached to its announce.
        LXMF delivery announces carry the peer display name; other apps
        publish their own metadata.
        """
        dest = destination_bytes(destination)
        if dest is None:
            return None
        no_use = RNS.Reticulum.get_instance() is None
        return RNS.Identity.recall_app_data(dest, _no_use=no_use)

    def get_peer_lxmf_data(self, destination: str) -> dict | None:
        """Decode an LXMF peer's announced metadata, or None.

        LXMF delivery announces pack app_data as msgpack:
        [display_name, stamp_cost, supported_functionality]. Returns a
        dict with those keys when the peer announced a valid LXMF entry.
        """
        app_data = self.get_peer_app_data(destination)
        if not app_data:
            return None
        try:
            peer_data = msgpack.unpackb(app_data)
        except Exception:
            return None
        if not isinstance(peer_data, list) or len(peer_data) < 3:
            return None
        name = peer_data[0]
        if isinstance(name, (bytes, bytearray)):
            name = bytes(name).decode("utf-8", errors="replace")
        return {
            "display_name": name,
            "stamp_cost": peer_data[1],
            "capabilities": peer_data[2],
        }

    def get_peer_announce(self, destination: str) -> dict | None:
        """Return announce metadata held for a destination, or None.

        Includes hop count, when the announce was heard, which interface
        delivered it, and the announced app_data.
        """
        dest = destination_bytes(destination)
        if dest is None:
            return None
        with RNS.Transport.announce_table_lock:
            entry = RNS.Transport.announce_table.get(dest)
            snapshot = list(entry) if entry else None
        if not snapshot:
            return None
        packet = snapshot[5]
        attached = snapshot[8]
        return {
            "destination": RNS.hexrep(dest, delimit=False),
            "received_at": snapshot[0],
            "hops": snapshot[4],
            "received_from": RNS.hexrep(snapshot[3], delimit=False)
            if isinstance(snapshot[3], bytes)
            else None,
            "interface": getattr(attached, "name", None),
            "app_data": self.get_peer_app_data(destination),
            "packet_hash": RNS.hexrep(packet.packet_hash, delimit=False)
            if getattr(packet, "packet_hash", None)
            else None,
        }

    def list_peer_announces(self, limit: int = 100) -> list[dict]:
        """List destinations whose announces this node has heard.

        Returns up to limit entries sorted newest first, each shaped like
        get_peer_announce output. Useful for discovering propagation
        nodes, peers, and services on the reachable mesh.
        """
        with RNS.Transport.announce_table_lock:
            hashes = list(RNS.Transport.announce_table.keys())
        entries = []
        for dest in hashes:
            info = self.get_peer_announce(RNS.hexrep(dest, delimit=False))
            if info is not None:
                entries.append(info)
        entries.sort(key=lambda e: e.get("received_at") or 0, reverse=True)
        return entries[: max(0, limit)]
