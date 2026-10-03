"""In-process test harness for LXMFy bots.

TestBot runs a real LXMFBot in test mode: inbound messages go through the
full pipeline (middleware, spam checks, permissions, dispatch) and outbound
sends are captured for assertions. No Reticulum instance is started.
"""

from __future__ import annotations

import secrets
import tempfile
import threading
import time
from types import SimpleNamespace
from typing import ClassVar

import RNS

from .core import LXMFBot


class SentMessage:
    """An outbound message captured from the bot queue."""

    __slots__ = (
        "content",
        "destination",
        "fields",
        "include_ticket",
        "method",
        "raw",
        "stamp_cost",
        "title",
    )

    def __init__(self, lxm):
        self.raw = lxm
        dest = getattr(lxm, "destination_hash", None)
        self.destination = (
            dest.hex() if isinstance(dest, (bytes, bytearray)) else str(dest)
        )
        content = getattr(lxm, "content", b"") or b""
        self.content = (
            content.decode("utf-8", errors="replace")
            if isinstance(content, (bytes, bytearray))
            else str(content)
        )
        title = getattr(lxm, "title", None)
        self.title = (
            title.decode("utf-8", errors="replace")
            if isinstance(title, (bytes, bytearray))
            else title
        )
        self.fields = getattr(lxm, "fields", None) or {}
        self.method = getattr(lxm, "desired_method", None)
        self.include_ticket = getattr(lxm, "include_ticket", None)
        self.stamp_cost = getattr(lxm, "stamp_cost", None)

    def __repr__(self) -> str:
        return f"SentMessage(to={self.destination[:16]}..., content={self.content!r})"


def fake_message(
    content: str | bytes,
    *,
    source_hash: bytes,
    title: str | bytes | None = None,
    fields: dict | None = None,
    message_hash: bytes | None = None,
) -> SimpleNamespace:
    """Build an LXMessage-shaped object for inbound injection."""
    return SimpleNamespace(
        content=content.encode("utf-8") if isinstance(content, str) else content,
        title=title.encode("utf-8") if isinstance(title, str) else title,
        hash=message_hash or secrets.token_bytes(32),
        source_hash=source_hash,
        fields=fields or {},
        signature_validated=True,
        unverified_reason=None,
    )


class TestBot(LXMFBot):
    """LXMFBot preconfigured for tests, with message injection.

    Args:
        name: Bot name.
        **overrides: Any LXMFBot/BotConfig keyword. Test-friendly defaults
            apply unless overridden.
    """

    __test__ = False  # not a pytest test class

    _DEFAULTS: ClassVar[dict] = {
        "test_mode": True,
        "storage_type": "memory",
        "announce_enabled": False,
        "first_message_enabled": False,
        "cogs_enabled": False,
        "signature_verification_enabled": False,
        "require_message_signatures": False,
        "landlock_enabled": False,
        "command_prefix": "/",
        "rate_limit": 1000,
        "cooldown": 0,
        "permissions_enabled": False,
    }

    def __init__(self, name: str = "TestBot", **overrides):
        self._tmp = tempfile.TemporaryDirectory(prefix="lxmfy-test-")
        config = {
            "name": name,
            "config_path": self._tmp.name,
            "storage_path": self._tmp.name + "/storage",
        }
        config.update(self._DEFAULTS)
        config.update(overrides)
        self._sender_hashes: dict[str, bytes] = {}
        self.outbox: list[SentMessage] = []
        super().__init__(**config)

    def sender_hash(self, sender: str = "alice") -> bytes:
        """Stable source hash for a named fake sender.

        Accepts a name (mapped to a fixed random hash per bot) or a hex
        destination hash.
        """
        if sender in self._sender_hashes:
            return self._sender_hashes[sender]
        try:
            raw = bytes.fromhex(sender)
            if len(raw) == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
                self._sender_hashes[sender] = raw
                return raw
        except ValueError:
            pass
        raw = secrets.token_bytes(RNS.Reticulum.TRUNCATED_HASHLENGTH // 8)
        self._sender_hashes[sender] = raw
        return raw

    def sender_hex(self, sender: str = "alice") -> str:
        """Hex source hash for a named fake sender."""
        return self.sender_hash(sender).hex()

    def receive(
        self,
        content: str | bytes,
        *,
        sender: str = "alice",
        title: str | bytes | None = None,
        fields: dict | None = None,
        message_hash: bytes | None = None,
    ) -> list[SentMessage]:
        """Inject an inbound message through the real receive pipeline.

        Returns the outbound messages produced while handling it. For
        threaded commands use wait_sent after receive.
        """
        self.drain()
        message = fake_message(
            content,
            source_hash=self.sender_hash(sender),
            title=title,
            fields=fields,
            message_hash=message_hash,
        )
        self._message_received(message)
        return self.drain()

    def receive_later(
        self,
        content: str | bytes,
        *,
        sender: str = "alice",
        delay: float = 0.05,
        **kwargs,
    ) -> threading.Thread:
        """Deliver an inbound message on a daemon thread after a delay.

        Used to answer blocking msg.ask calls inside command handlers.
        """
        thread = threading.Thread(
            target=lambda: (
                time.sleep(delay),
                self.receive(content, sender=sender, **kwargs),
            ),
            daemon=True,
        )
        thread.start()
        return thread

    def drain(self) -> list[SentMessage]:
        """Pop all queued outbound messages and append them to outbox."""
        out = []
        while not self.queue.empty():
            try:
                out.append(SentMessage(self.queue.get(block=False)))
            except Exception:
                break
        self.outbox.extend(out)
        return out

    def wait_sent(self, count: int = 1, timeout: float = 5.0) -> list[SentMessage]:
        """Wait until at least count new outbound messages are queued."""
        collected: list[SentMessage] = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            collected += self.drain()
            if len(collected) >= count:
                return collected
            time.sleep(0.01)
        return collected

    def last_sent(self, sender: str | None = None) -> SentMessage | None:
        """Most recent outbound message, optionally filtered by sender."""
        self.drain()
        sent = self.outbox
        if sender is not None:
            target = self.sender_hex(sender)
            sent = [m for m in sent if m.destination == target]
        return sent[-1] if sent else None

    def close(self) -> None:
        """Shut down the bot and remove temporary storage."""
        try:
            self.cleanup()
        finally:
            self._tmp.cleanup()

    def __enter__(self) -> TestBot:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
