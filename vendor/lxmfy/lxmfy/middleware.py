"""Middleware system for LXMFy.

This module provides a flexible middleware system for processing messages
and events, allowing users to add custom processing logic to the bot's
message handling pipeline.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MiddlewareType(Enum):
    """Types of middleware execution points"""

    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"
    PRE_EVENT = "pre_event"
    POST_EVENT = "post_event"
    REQUEST = "request"
    RESPONSE = "response"


@dataclass
class MiddlewareContext:
    """Context passed through middleware chain"""

    type: MiddlewareType
    data: Any
    metadata: dict = field(default_factory=dict)
    cancelled: bool = False

    def cancel(self):
        """Cancel middleware processing"""
        self.cancelled = True


class MessageTracker:
    """Tracks processed messages to prevent duplicates"""

    def __init__(self, max_size=1000):
        self.processed_set = set()
        self.processed_list = []
        self.max_size = max_size

    def is_processed(self, msg_hash: str) -> bool:
        """Check if message was already processed"""
        if msg_hash in self.processed_set:
            return True

        self.processed_set.add(msg_hash)
        self.processed_list.append(msg_hash)

        if len(self.processed_list) > self.max_size:
            oldest = self.processed_list.pop(0)
            self.processed_set.discard(oldest)

        return False


class MiddlewareManager:
    """Manages middleware registration and execution"""

    def __init__(self):
        self.middleware: dict[MiddlewareType, list[Callable]] = {
            t: [] for t in MiddlewareType
        }
        self.message_tracker = MessageTracker()
        self.logger = logging.getLogger(__name__)

    def register(self, middleware_type: MiddlewareType, func: Callable = None):
        """Register a middleware function"""
        if func is None:
            # Decorator usage: @middleware.register(MiddlewareType.PRE_COMMAND)
            def decorator(f):
                self.middleware[middleware_type].append(f)
                return f

            return decorator
        # Direct usage: middleware.register(MiddlewareType.PRE_COMMAND, func)
        self.middleware[middleware_type].append(func)
        return func

    def remove(self, middleware_type: MiddlewareType, func: Callable):
        """Remove a middleware function"""
        if func in self.middleware[middleware_type]:
            self.middleware[middleware_type].remove(func)

    def execute(self, mw_type: MiddlewareType, data: Any) -> Any:
        """Execute middleware chain for given type"""
        try:
            # If data is already a MiddlewareContext, use it directly
            if isinstance(data, MiddlewareContext):
                ctx = data
            else:
                ctx = MiddlewareContext(mw_type, data)

            for mw in self.middleware.get(mw_type, []):
                try:
                    mw(ctx)
                    if ctx.cancelled:
                        break
                except Exception as e:
                    self.logger.error("Error in middleware %s: %s", mw.__name__, str(e))

            return None if ctx.cancelled else ctx.data

        except Exception as e:
            self.logger.error("Error executing middleware chain: %s", str(e))
            return data
