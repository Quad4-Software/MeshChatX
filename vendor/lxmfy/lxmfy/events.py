"""Event system module for LXMFy.

This module provides a comprehensive event handling system including:
- Custom event creation and dispatching
- Event middleware support
- Event logging and monitoring
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Enumeration of event priority levels.

    Members:
        HIGHEST: Highest priority.
        HIGH: High priority.
        NORMAL: Normal priority.
        LOW: Low priority.
    """

    HIGHEST = 3
    HIGH = 2
    NORMAL = 1
    LOW = 0


@dataclass(frozen=True)
class Event:
    """Data class representing an event.

    Attributes:
        name (str): The name of the event.
        data (dict): A dictionary containing event-specific data.
        cancelled (bool): A flag indicating whether the event has been cancelled.

    """

    name: str
    data: dict = field(default_factory=dict)
    cancelled: bool = False

    def __hash__(self):
        """Returns the hash value of the event based on its name.

        Returns:
            int: Hash value of the event name.

        """
        return hash(self.name)

    def __eq__(self, other):
        """Compares this event to another object for equality.

        Args:
            other (Any): The object to compare to.

        Returns:
            bool: True if the other object is an Event instance and has the same name, False otherwise.

        """
        if not isinstance(other, Event):
            return False
        return self.name == other.name

    def cancel(self):
        """Cancels the event, preventing further processing."""
        object.__setattr__(self, "cancelled", True)


@dataclass
class EventHandler:
    """Data class representing an event handler.

    Attributes:
        callback (Callable): The function to be called when the event is dispatched.
        priority (EventPriority): The priority of the event handler.

    """

    callback: Callable
    priority: EventPriority


class EventManager:
    """Manages event registration, dispatching, and logging."""

    def __init__(self, storage):
        """Initializes the EventManager.

        Args:
            storage: The storage object used for logging events.

        """
        self.storage = storage
        self.handlers = {}
        self.logger = logging.getLogger(__name__)

    def on(self, event_name: str, priority: EventPriority = EventPriority.NORMAL):
        """Registers an event handler for a specific event.

        Args:
            event_name (str): The name of the event to handle.
            priority (EventPriority): The priority of the event handler (default: EventPriority.NORMAL).

        Returns:
            Callable: A decorator that registers the decorated function as an event handler.

        """

        def decorator(func):
            """Registers the decorated function as an event handler."""
            if event_name not in self.handlers:
                self.handlers[event_name] = []
            self.handlers[event_name].append((priority, func))
            self.handlers[event_name].sort(key=lambda x: x[0].value, reverse=True)
            return func

        return decorator

    def use(self, middleware: Callable):
        """Adds middleware to the event pipeline.

        Args:
            middleware (Callable): The middleware function to add.

        """

    def dispatch(self, event: Event):
        """Dispatches an event to all registered handlers.

        Args:
            event (Event): The event to dispatch.

        """
        try:
            if event.name in self.handlers:
                for _priority, handler in self.handlers[event.name]:
                    try:
                        handler(event)
                        if event.cancelled:
                            break
                    except Exception as e:
                        self.logger.error(
                            "Error in event handler %s: %s",
                            handler.__name__,
                            str(e),
                        )
        except Exception as e:
            self.logger.error("Error dispatching event: %s", str(e))

    def _log_event(self, event: Event):
        """Logs an event to storage.

        Args:
            event (Event): The event to log.

        """
        try:
            events = self.storage.get("events:log", [])
            events.append(
                {
                    "name": event.name,
                    "data": event.data,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            self.storage.set("events:log", events[-1000:])
        except Exception as e:
            self.logger.error("Error logging event: %s", str(e))
