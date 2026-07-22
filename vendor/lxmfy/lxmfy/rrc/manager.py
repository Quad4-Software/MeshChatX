"""Manage multiple RRC hub sessions for an LXMFy bot."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import RNS

from .client import RRCClient
from .constants import DEFAULT_DEST_NAME
from .envelope import normalize_room

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, RRCClient, Any], None]


class RRCManager:
    """Owns RRCClient sessions and fans events out to bot handlers."""

    STORAGE_KEY = "rrc_sessions"

    def __init__(
        self,
        identity: RNS.Identity | None = None,
        nick: str | None = None,
        dest_name: str = DEFAULT_DEST_NAME,
        auto_reconnect: bool = True,
        storage=None,
        persist_sessions: bool = False,
    ):
        self.identity = identity
        self.nick = nick
        self.dest_name = dest_name or DEFAULT_DEST_NAME
        self.auto_reconnect = auto_reconnect
        self.storage = storage
        self.persist_sessions = bool(persist_sessions)
        self.clients: dict[bytes, RRCClient] = {}
        self._handlers: list[EventCallback] = []

    def on_event(self, callback: EventCallback) -> EventCallback:
        """Register an event callback. Returns the callback for decorator use."""
        self._handlers.append(callback)
        return callback

    def _dispatch(self, event: str, client: RRCClient, payload: Any) -> None:
        for handler in list(self._handlers):
            try:
                handler(event, client, payload)
            except Exception:
                logger.exception("RRC manager handler failed for %s", event)
        if event in ("joined", "parted"):
            self.save_sessions()

    def connect(
        self,
        hub_hash: bytes | str,
        rooms: list[str] | None = None,
        nick: str | None = None,
        dest_name: str | None = None,
        auto_reconnect: bool | None = None,
    ) -> RRCClient:
        """Connect to an RRC hub. Returns the client session."""
        if self.identity is None:
            raise RuntimeError("RRC manager has no identity")

        if isinstance(hub_hash, str):
            hub_bytes = bytes.fromhex(hub_hash)
        else:
            hub_bytes = bytes(hub_hash)

        existing = self.clients.get(hub_bytes)
        if existing is not None:
            if rooms:
                existing.set_auto_join(rooms)
                with existing._lock:
                    for room in rooms:
                        if isinstance(room, str):
                            existing._rejoin_rooms.add(normalize_room(room))
            if nick is not None:
                existing.set_nick(nick)
            if not existing.connected:
                existing.connect()
            elif rooms:
                for room in rooms:
                    try:
                        existing.join(room)
                    except Exception:
                        logger.exception("Failed joining room %s", room)
            self.save_sessions()
            return existing

        client = RRCClient(
            identity=self.identity,
            hub_hash=hub_bytes,
            dest_name=dest_name or self.dest_name,
            nick=nick if nick is not None else self.nick,
            auto_reconnect=(
                self.auto_reconnect if auto_reconnect is None else auto_reconnect
            ),
            on_event=self._dispatch,
        )
        if rooms:
            client.set_auto_join(rooms)
            with client._lock:
                for room in rooms:
                    if isinstance(room, str):
                        client._rejoin_rooms.add(normalize_room(room))
        self.clients[hub_bytes] = client
        client.connect()
        self.save_sessions()
        return client

    def disconnect(self, hub_hash: bytes | str | None = None) -> None:
        """Disconnect one hub, or all hubs when hub_hash is None."""
        if hub_hash is None:
            for client in list(self.clients.values()):
                client.disconnect()
            self.clients.clear()
            self.save_sessions()
            return

        hub_bytes = (
            bytes.fromhex(hub_hash) if isinstance(hub_hash, str) else bytes(hub_hash)
        )
        client = self.clients.pop(hub_bytes, None)
        if client is not None:
            client.disconnect()
        self.save_sessions()

    def get(self, hub_hash: bytes | str) -> RRCClient | None:
        """Return a connected client for a hub hash, if present."""
        hub_bytes = (
            bytes.fromhex(hub_hash) if isinstance(hub_hash, str) else bytes(hub_hash)
        )
        return self.clients.get(hub_bytes)

    def send_message(
        self,
        room: str,
        text: str,
        hub_hash: bytes | str | None = None,
    ) -> bytes:
        """Send a MSG on the first connected hub, or a specific hub."""
        client = self._require_client(hub_hash)
        return client.send_message(room, text)

    def send_notice(
        self,
        room: str,
        text: str,
        hub_hash: bytes | str | None = None,
    ) -> bytes:
        """Send a NOTICE on the first connected hub, or a specific hub."""
        client = self._require_client(hub_hash)
        return client.send_notice(room, text)

    def send_action(
        self,
        room: str,
        text: str,
        hub_hash: bytes | str | None = None,
    ) -> bytes:
        """Send an ACTION on the first connected hub, or a specific hub."""
        client = self._require_client(hub_hash)
        return client.send_action(room, text)

    def join(
        self,
        room: str,
        hub_hash: bytes | str | None = None,
    ) -> str:
        """Join a room on the first connected hub, or a specific hub."""
        client = self._require_client(hub_hash)
        room_n = client.join(room)
        self.save_sessions()
        return room_n

    def part(
        self,
        room: str,
        hub_hash: bytes | str | None = None,
    ) -> str:
        """Part a room on the first connected hub, or a specific hub."""
        client = self._require_client(hub_hash)
        room_n = client.part(room)
        self.save_sessions()
        return room_n

    def _require_client(self, hub_hash: bytes | str | None) -> RRCClient:
        if hub_hash is not None:
            client = self.get(hub_hash)
            if client is None:
                raise RuntimeError("RRC hub not connected")
            return client
        for client in self.clients.values():
            if client.connected:
                return client
        raise RuntimeError("No connected RRC hub")

    def status(self) -> list[dict[str, Any]]:
        """Return status snapshots for all hub sessions."""
        return [client.status_dict() for client in self.clients.values()]

    def save_sessions(self) -> None:
        """Persist hub hashes, rooms, and nick for crash recovery."""
        if not self.persist_sessions or self.storage is None:
            return
        entries = []
        for client in self.clients.values():
            with client._lock:
                rooms = sorted(
                    set(client.rooms)
                    | set(client._rejoin_rooms)
                    | set(client._auto_join_rooms),
                )
            entries.append(
                {
                    "hub_hash": client.hub_hash.hex(),
                    "dest_name": client.dest_name,
                    "nick": client.nick,
                    "rooms": rooms,
                    "auto_reconnect": client.auto_reconnect,
                },
            )
        try:
            self.storage.set(self.STORAGE_KEY, entries)
        except Exception:
            logger.exception("Failed to persist RRC sessions")

    def restore_sessions(self) -> int:
        """Restore persisted hub sessions. Returns number of hubs reconnected."""
        if not self.persist_sessions or self.storage is None:
            return 0
        entries = self.storage.get(self.STORAGE_KEY, [])
        if not isinstance(entries, list):
            return 0
        restored = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            hub_hash = entry.get("hub_hash")
            if not isinstance(hub_hash, str):
                continue
            try:
                self.connect(
                    hub_hash,
                    rooms=entry.get("rooms")
                    if isinstance(entry.get("rooms"), list)
                    else None,
                    nick=entry.get("nick")
                    if isinstance(entry.get("nick"), str)
                    else None,
                    dest_name=entry.get("dest_name")
                    if isinstance(entry.get("dest_name"), str)
                    else None,
                    auto_reconnect=entry.get("auto_reconnect")
                    if isinstance(entry.get("auto_reconnect"), bool)
                    else None,
                )
                restored += 1
            except Exception:
                logger.exception("Failed to restore RRC hub %s", hub_hash)
        return restored

    def shutdown(self) -> None:
        """Persist session state and tear down links without forgetting hubs."""
        self.save_sessions()
        for client in list(self.clients.values()):
            try:
                client.disconnect()
            except Exception:
                logger.exception("RRC client disconnect failed during shutdown")
