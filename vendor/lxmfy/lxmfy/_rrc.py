"""RRC hub connectivity for LXMFBot."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import RNS

from ._sync import run_sync
from .events import Event
from .rrc import DEFAULT_DEST_NAME, RRCManager, RRCMessage

if TYPE_CHECKING:
    import logging

    from .config import BotConfig
    from .events import EventManager
    from .storage import Storage


class RRCMixin:
    """RRC session lifecycle and event fan-out."""

    config: BotConfig
    events: EventManager
    identity: RNS.Identity
    logger: logging.Logger
    rrc: RRCManager | None
    rrc_handlers: list
    storage: Storage

    def _init_rrc(self) -> None:
        self.rrc_handlers = []
        self.rrc = RRCManager(
            identity=self.identity,
            nick=self.config.rrc_nick or self.config.name,
            dest_name=self.config.rrc_dest_name or DEFAULT_DEST_NAME,
            auto_reconnect=self.config.rrc_auto_reconnect,
            storage=self.storage,
            persist_sessions=self.config.rrc_persist_sessions,
        )
        self.rrc.on_event(self._rrc_event)

        if not (self.config.rrc_enabled and not self.config.test_mode):
            return

        config_rooms = list(self.config.rrc_rooms or [])
        restored = 0
        if self.config.rrc_persist_sessions:
            try:
                restored = self.rrc.restore_sessions()
            except Exception:
                self.logger.exception("Failed to restore RRC sessions")
        for hub in self.config.rrc_hubs or []:
            try:
                RNS.log(
                    f"RRC connecting to hub {hub} rooms={config_rooms or ['(none)']}",
                    RNS.LOG_INFO,
                )
                self.connect_rrc(hub, rooms=list(config_rooms))
            except Exception as e:
                self.logger.exception("Failed to connect RRC hub %s", hub)
                RNS.log(f"RRC hub connect failed for {hub}: {e}", RNS.LOG_ERROR)
        if restored:
            RNS.log(f"Restored {restored} RRC hub session(s)", RNS.LOG_INFO)
        # Ensure persisted hubs not listed in config still get config rooms
        # when their saved room list was empty.
        if config_rooms:
            for client in list(self.rrc.clients.values()):
                with client._lock:
                    planned = (
                        set(client.rooms)
                        | set(client._rejoin_rooms)
                        | set(
                            client._auto_join_rooms,
                        )
                    )
                if planned:
                    continue
                try:
                    self.connect_rrc(
                        client.hub_hash.hex(),
                        rooms=list(config_rooms),
                    )
                except Exception:
                    self.logger.exception(
                        "Failed to apply RRC rooms to hub %s", client.hub_hash.hex()
                    )

    def connect_rrc(
        self,
        hub_hash: str,
        rooms: list[str] | None = None,
        nick: str | None = None,
        dest_name: str | None = None,
        auto_reconnect: bool | None = None,
    ):
        """Connect to an RRC hub as a client.

        Args:
            hub_hash: Hub destination hash as hex.
            rooms: Optional rooms to join after WELCOME.
            nick: Optional nickname override for this hub.
            dest_name: Destination name (default rrc.hub).
            auto_reconnect: Override auto-reconnect for this session.

        Returns:
            The RRCClient session.

        """
        if self.config.test_mode:
            raise RuntimeError("RRC connections are unavailable in test_mode")
        if self.rrc is None:
            raise RuntimeError("RRC is not initialized")
        return self.rrc.connect(
            hub_hash,
            rooms=rooms,
            nick=nick,
            dest_name=dest_name,
            auto_reconnect=auto_reconnect,
        )

    def disconnect_rrc(self, hub_hash: str | None = None) -> None:
        """Disconnect one or all RRC hub sessions."""
        if self.rrc is not None:
            self.rrc.disconnect(hub_hash)

    def on_rrc(self, callback: Callable | None = None):
        """Register a handler for RRC events.

        Handler signature: ``handler(event, client, payload)``.
        Payload is an RRCMessage for room events, or a dict for status/welcome.
        """

        def decorator(func):
            self.rrc_handlers.append(func)
            return func

        if callback is not None:
            return decorator(callback)
        return decorator

    def _rrc_event(self, event: str, client, payload) -> None:
        """Fan RRC events to bot handlers and the event manager."""
        event_data = {
            "event": event,
            "hub_hash": client.hub_hash.hex() if client else None,
            "payload": payload,
        }
        if isinstance(payload, RRCMessage):
            event_data.update(
                {
                    "kind": payload.kind,
                    "room": payload.room,
                    "text": payload.text,
                    "nick": payload.nick,
                    "src": payload.src.hex() if payload.src else None,
                    "mention": payload.mention,
                },
            )
        try:
            self.events.dispatch(Event(f"rrc_{event}", event_data))
        except Exception:
            self.logger.exception("Error dispatching RRC event")

        for handler in self.rrc_handlers:
            try:
                run_sync(handler, event, client, payload)
            except Exception:
                self.logger.exception("Error in RRC handler")
