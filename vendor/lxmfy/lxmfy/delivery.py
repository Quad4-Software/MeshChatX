"""Delivery event stream for LXMFy.

Records outbound lifecycle events (queued, deferred, dispatched,
delivered, failed, cancelled, dropped) so bots can observe message
flow in real time and the debugger can render a timeline after the
fact.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

STAGES = (
    "queued",
    "deferred",
    "dispatched",
    "delivered",
    "failed",
    "cancelled",
    "dropped",
)

_EVENT_KEYS = (
    "destination",
    "message_id",
    "hash",
    "method",
    "attempts",
    "reason",
    "title",
)

# Storage key used for the persisted tail of the stream.
STORAGE_KEY = "delivery_events"
PERSIST_LIMIT = 200


class DeliveryTracker:
    """Bounded delivery event stream with subscribers and persistence."""

    def __init__(self, storage=None, maxlen: int = 500):
        """Initialize the tracker.

        Args:
            storage: Optional Storage facade for persisting the recent
                tail of the stream. Pass None to keep events in memory.
            maxlen: Maximum in-memory events retained.

        """
        self.events: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self.subscribers: list[Callable] = []
        self._storage = storage

    def record(self, stage: str, **fields) -> dict[str, Any]:
        """Append a delivery event and notify subscribers.

        Args:
            stage: One of STAGES.
            **fields: Optional event fields: destination, message_id,
                hash, method, attempts, reason, title.

        Returns:
            The recorded event dict.

        """
        event: dict[str, Any] = {"ts": time.time(), "stage": stage}
        for key in _EVENT_KEYS:
            value = fields.get(key)
            if value is not None:
                event[key] = value
        self.events.append(event)
        self._persist(event)
        for callback in list(self.subscribers):
            try:
                callback(dict(event))
            except Exception:
                logger.exception("Delivery event subscriber failed")
        return event

    def subscribe(self, callback: Callable) -> Callable:
        """Register a subscriber called with each new event dict."""
        self.subscribers.append(callback)
        return callback

    def unsubscribe(self, callback: Callable) -> bool:
        """Remove a subscriber. Returns True when it was registered."""
        try:
            self.subscribers.remove(callback)
            return True
        except ValueError:
            return False

    def recent(
        self,
        limit: int | None = None,
        *,
        stage: str | None = None,
        destination: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent events, oldest first.

        Args:
            limit: Maximum events returned, counted from the newest.
            stage: Optional stage filter.
            destination: Optional exact destination filter.

        """
        items = list(self.events)
        if stage is not None:
            items = [e for e in items if e.get("stage") == stage]
        if destination is not None:
            items = [e for e in items if e.get("destination") == destination]
        if limit is not None and limit > 0:
            items = items[-limit:]
        return items

    def load_persisted(self) -> None:
        """Restore the persisted tail into memory at startup."""
        if self._storage is None:
            return
        try:
            stored = self._storage.get(STORAGE_KEY, [])
        except Exception:
            logger.exception("Failed to read persisted delivery events")
            return
        if not isinstance(stored, list):
            return
        for entry in stored:
            if isinstance(entry, dict) and isinstance(entry.get("ts"), (int, float)):
                self.events.append(entry)

    def _persist(self, event: dict[str, Any]) -> None:
        """Write the bounded event tail to storage, best effort."""
        if self._storage is None:
            return
        try:
            tail = list(self.events)[-PERSIST_LIMIT:]
            self._storage.set(STORAGE_KEY, tail)
        except Exception:
            logger.debug("Failed to persist delivery event", exc_info=True)
