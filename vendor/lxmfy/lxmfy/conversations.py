"""Multi-step conversations for LXMFBot.

Commands can ask a sender a question and consume their next message as the
answer instead of dispatching it as a command. Supports blocking, awaited,
and callback styles.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .core import LXMFBot

MAX_PENDING = 1024
DEFAULT_TIMEOUT = 300.0


class Answer:
    """The message that answered a pending question."""

    __slots__ = ("_bot", "content", "fields", "hash", "message", "sender")

    def __init__(self, sender: str, message: Any, bot: LXMFBot | None = None):
        self._bot = bot
        self.sender = sender
        self.message = message
        raw = getattr(message, "content", b"") or b""
        self.content = (
            raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        )
        self.fields = getattr(message, "fields", None) or {}
        msg_hash = getattr(message, "hash", None)
        self.hash = msg_hash.hex() if isinstance(msg_hash, (bytes, bytearray)) else None

    def reply(self, text, **kwargs) -> bool:
        """Reply to the sender who answered, threading to their message."""
        if self._bot is None:
            return False
        kwargs.setdefault("reply_to", self.hash)
        return self._bot.send(self.sender, text, **kwargs)


@dataclass
class _Pending:
    sender: str
    created_at: float
    timeout: float
    validator: Callable | None = None
    event: threading.Event | None = None
    loop: asyncio.AbstractEventLoop | None = None
    future: asyncio.Future | None = None
    on_answer: Callable | None = None
    on_timeout: Callable | None = None
    timer: threading.Timer | None = None
    answer: Answer | None = None
    cancelled: bool = False
    attempts: int = 0


class ConversationManager:
    """Tracks pending questions per sender and resolves them on reply."""

    def __init__(self, bot: LXMFBot):
        self.bot = bot
        self._pending: dict[str, _Pending] = {}
        self._lock = threading.Lock()

    def has_pending(self, sender: str) -> bool:
        """True when a question is waiting on this sender."""
        with self._lock:
            return sender in self._pending

    def pending_count(self) -> int:
        """Number of senders with a pending question."""
        with self._lock:
            return len(self._pending)

    def pending_senders(self) -> list[str]:
        """Senders with a pending question."""
        with self._lock:
            return list(self._pending)

    def _register(self, pending: _Pending) -> bool:
        replaced = None
        with self._lock:
            if (
                pending.sender not in self._pending
                and len(self._pending) >= MAX_PENDING
            ):
                return False
            replaced = self._pending.pop(pending.sender, None)
            self._pending[pending.sender] = pending
        if replaced is not None:
            self._abort(replaced)
        return True

    def _pop(self, sender: str) -> _Pending | None:
        with self._lock:
            return self._pending.pop(sender, None)

    def _pop_own(self, pending: _Pending) -> None:
        """Remove pending only if it is still the registered entry."""
        with self._lock:
            if self._pending.get(pending.sender) is pending:
                del self._pending[pending.sender]

    @staticmethod
    def _abort(pending: _Pending) -> None:
        pending.cancelled = True
        if pending.timer is not None:
            pending.timer.cancel()
        if pending.event is not None:
            pending.event.set()
        elif pending.future is not None and pending.loop is not None:
            pending.loop.call_soon_threadsafe(pending.future.set_result, None)

    def _send_prompt(self, sender: str, prompt, title: str | None) -> None:
        if prompt is not None:
            self.bot.send(sender, prompt, title=title or "Question")

    def ask(
        self,
        sender: str,
        prompt,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        title: str | None = None,
        validator: Callable | None = None,
    ) -> Answer | None:
        """Send a prompt and block until the sender replies.

        Returns an Answer with content, fields, and hash, or None on
        timeout or cancellation. In async command handlers use
        ``await msg.ask_async(...)`` instead. For long waits prefer the
        callback style with ``on_answer`` so no thread stays parked.
        """
        event = threading.Event()
        pending = _Pending(
            sender=sender,
            created_at=time.time(),
            timeout=timeout,
            validator=validator,
            event=event,
        )
        if not self._register(pending):
            self.bot.logger.warning(
                "Conversation limit reached, dropping ask for %s",
                sender,
            )
            return None
        try:
            self._send_prompt(sender, prompt, title)
            if not event.wait(timeout):
                return None
            return pending.answer
        finally:
            self._pop_own(pending)

    async def ask_async(
        self,
        sender: str,
        prompt,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        title: str | None = None,
        validator: Callable | None = None,
    ) -> Answer | None:
        """Send a prompt and await the sender's reply.

        Same contract as ask, for async command handlers.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        pending = _Pending(
            sender=sender,
            created_at=time.time(),
            timeout=timeout,
            validator=validator,
            loop=loop,
            future=future,
        )
        if not self._register(pending):
            self.bot.logger.warning(
                "Conversation limit reached, dropping ask for %s",
                sender,
            )
            return None
        try:
            self._send_prompt(sender, prompt, title)
            try:
                return await asyncio.wait_for(future, timeout)
            except TimeoutError:
                return None
        finally:
            self._pop_own(pending)

    def ask_callback(
        self,
        sender: str,
        prompt,
        on_answer: Callable,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        title: str | None = None,
        validator: Callable | None = None,
        on_timeout: Callable | None = None,
    ) -> bool:
        """Send a prompt and invoke on_answer(answer) when the reply arrives.

        Non-blocking. on_timeout(sender) fires if the sender never
        answers. Returns False when the pending limit is reached.
        """
        pending = _Pending(
            sender=sender,
            created_at=time.time(),
            timeout=timeout,
            validator=validator,
            on_answer=on_answer,
            on_timeout=on_timeout,
        )
        if not self._register(pending):
            self.bot.logger.warning(
                "Conversation limit reached, dropping ask for %s",
                sender,
            )
            return False
        timer = threading.Timer(timeout, self._expire, args=(sender,))
        timer.daemon = True
        pending.timer = timer
        timer.start()
        self._send_prompt(sender, prompt, title)
        return True

    def resolve(self, sender: str, message) -> bool:
        """Feed an inbound message to a pending question.

        Returns True when the message was consumed as an answer. When a
        validator rejects the answer the question stays pending.
        """
        with self._lock:
            pending = self._pending.get(sender)
        if pending is None:
            return False

        answer = Answer(sender, message, bot=self.bot)
        if pending.validator is not None:
            pending.attempts += 1
            try:
                error = pending.validator(answer)
            except Exception:
                self.bot.logger.exception(
                    "Conversation validator failed for %s",
                    sender,
                )
                error = "Invalid answer."
            if error:
                self.bot.send(sender, str(error))
                return True

        self._pop(sender)
        if pending.timer is not None:
            pending.timer.cancel()

        if pending.event is not None:
            pending.answer = answer
            pending.event.set()
        elif pending.future is not None and pending.loop is not None:
            pending.loop.call_soon_threadsafe(pending.future.set_result, answer)
        elif pending.on_answer is not None:
            try:
                pending.on_answer(answer)
            except Exception:
                self.bot.logger.exception(
                    "Conversation on_answer failed for %s",
                    sender,
                )
        return True

    def cancel(self, sender: str) -> bool:
        """Cancel a pending question for a sender."""
        pending = self._pop(sender)
        if pending is None:
            return False
        self._abort(pending)
        return True

    def cancel_all(self) -> None:
        """Cancel every pending question."""
        with self._lock:
            senders = list(self._pending)
        for sender in senders:
            self.cancel(sender)

    def _expire(self, sender: str) -> None:
        pending = self._pop(sender)
        if pending is None:
            return
        if pending.on_timeout is not None:
            try:
                pending.on_timeout(sender)
            except Exception:
                self.bot.logger.exception(
                    "Conversation on_timeout failed for %s",
                    sender,
                )
