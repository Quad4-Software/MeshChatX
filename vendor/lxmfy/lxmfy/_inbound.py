"""Inbound message pipeline for LXMFBot."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import RNS

from ._sync import run_sync
from .events import Event, EventPriority
from .lxmf_fields import (
    FIELD_RESULTS,
    pack_result,
    unpack_commands,
    unpack_reaction,
    unpack_reply,
)
from .middleware import MiddlewareContext, MiddlewareType
from .permissions import DefaultPerms
from .signatures import verify_incoming_message
from .validation import destination_bytes

if TYPE_CHECKING:
    import logging
    import threading
    from collections.abc import Callable

    from LXMF import LXMRouter

    from .config import BotConfig
    from .conversations import ConversationManager
    from .events import EventManager
    from .middleware import MiddlewareManager
    from .moderation import SpamProtection
    from .nlp import IntentClassifier
    from .permissions import PermissionManager
    from .storage import Storage


class InboundMixin:
    """Message intake, dispatch, and handler registration."""

    command_prefix: str | None
    commands: dict
    config: BotConfig
    conversations: ConversationManager
    delivery_callbacks: list
    events: EventManager
    first_message_handlers: list
    intents: dict
    local: RNS.Destination | None
    logger: logging.Logger
    message_handlers: list
    middleware: MiddlewareManager
    nlp: IntentClassifier
    permissions: PermissionManager
    reaction_handlers: list
    receipts: list
    router: LXMRouter | None
    spam_protection: SpamProtection
    storage: Storage
    _receive_lock: threading.Lock
    send: Callable[..., bool]
    _execute_command: Callable[..., bool]
    _reset_delivery_attempts: Callable[..., None]

    def _register_builtin_events(self):
        """Register built-in event handlers."""

        @self.events.on("message_received", EventPriority.HIGHEST)
        def handle_message(event):
            """Handles incoming messages, performing spam checks."""
            sender = event.data["sender"]
            if not self.permissions.has_permission(sender, DefaultPerms.BYPASS_SPAM):
                allowed, msg = self.spam_protection.check_spam(sender)
                if not allowed:
                    event.cancel()
                    if msg:
                        self.send(sender, msg)
                    return

            self._reset_delivery_attempts(sender)

    def _process_message(self, message, sender):
        """Process an incoming message."""
        try:
            content = message.content.decode("utf-8") if message.content else ""
            receipt = RNS.hexrep(message.hash, delimit=False)
            msg_fields = getattr(message, "fields", None) or {}
            reply_info = unpack_reply(msg_fields) or {}

            field_commands = unpack_commands(msg_fields)
            request_id = None
            if field_commands:
                request_id = field_commands[0].get("request_id")
            has_field_commands = bool(field_commands)

            def reply(response, **kwargs):
                """Helper function to reply to a message."""
                lxmf_fields = kwargs.pop("lxmf_fields", None) or {}
                if has_field_commands or request_id is not None:
                    lxmf_fields[FIELD_RESULTS] = pack_result(
                        response,
                        request_id,
                        kwargs.pop("status", "ok"),
                    )
                if lxmf_fields:
                    kwargs["lxmf_fields"] = lxmf_fields
                reply_to = kwargs.pop("reply_to", "auto")
                if reply_to is True or reply_to == "auto":
                    kwargs["reply_to"] = getattr(message, "hash", None)
                    if reply_info.get("thread"):
                        kwargs.setdefault("thread", reply_info["thread"])
                elif reply_to:
                    kwargs["reply_to"] = reply_to
                if kwargs.get("quote") is True:
                    kwargs["quote"] = content[:200]
                self.send(sender, response, **kwargs)

            if self.config.first_message_enabled:
                is_first = False
                with self._receive_lock:
                    first_messages = self.storage.get("first_messages", {})
                    if not isinstance(first_messages, dict):
                        first_messages = {}
                    if sender not in first_messages:
                        is_first = True
                        first_messages[sender] = True
                        while len(first_messages) > 10000:
                            first_messages.pop(next(iter(first_messages)))
                        self.storage.set("first_messages", first_messages)
                if is_first:
                    self.logger.debug("First message from %s", sender)
                    for handler in self.first_message_handlers:
                        if run_sync(handler, sender, message):
                            self.logger.debug(
                                "First message from %s consumed by handler",
                                sender,
                            )
                            return

            if not self.permissions.has_permission(sender, DefaultPerms.USE_BOT):
                self.logger.debug("Message from %s denied by permissions", sender)
                return

            reaction = unpack_reaction(msg_fields, sender)

            if self.conversations.has_pending(sender):
                if has_field_commands or self._is_command_text(content):
                    self.conversations.cancel(sender)
                elif reaction is not None and not content.strip():
                    pass  # bare reactions reach reaction handlers normally
                elif self.conversations.resolve(sender, message):
                    return

            if reaction is not None:
                for handler in self.reaction_handlers:
                    if run_sync(handler, sender, reaction):
                        self.logger.debug(
                            "Reaction from %s consumed by reaction handler",
                            sender,
                        )
                        return

            # Call message handlers
            for handler in self.message_handlers:
                if run_sync(handler, sender, message):
                    self.logger.debug(
                        "Message from %s consumed by message handler",
                        sender,
                    )
                    return

            def ask(prompt, **kwargs):
                """Ask the sender a question and get the answer.

                Blocks until the reply arrives unless on_answer is given,
                in which case the reply invokes that callback instead.
                """
                if kwargs.get("on_answer") is not None:
                    return self.conversations.ask_callback(sender, prompt, **kwargs)
                return self.conversations.ask(sender, prompt, **kwargs)

            async def ask_async(prompt, **kwargs):
                """Ask the sender a question and await the answer."""
                return await self.conversations.ask_async(sender, prompt, **kwargs)

            msg_ctx = {
                "lxmf": message,
                "reply": reply,
                "ask": ask,
                "ask_async": ask_async,
                "cancel_conversation": lambda: self.conversations.cancel(sender),
                "conversation_pending": lambda: self.conversations.has_pending(
                    sender,
                ),
                "sender": sender,
                "content": content,
                "hash": receipt,
                "fields": msg_fields,
                "reaction": reaction,
                "request_id": request_id,
                "reply_to": reply_info.get("reply_to"),
                "reply_quote": reply_info.get("quote"),
                "thread": reply_info.get("thread"),
            }
            msg = SimpleNamespace(**msg_ctx)

            ctx = MiddlewareContext(MiddlewareType.PRE_COMMAND, msg)
            if self.middleware.execute(MiddlewareType.PRE_COMMAND, ctx) is None:
                return

            # Process structured commands from LXMF fields
            if getattr(self.config, "lxmf_commands_enabled", True) and field_commands:
                for cmd_data in field_commands:
                    cmd_name = cmd_data.get("command") or cmd_data.get("cmd")
                    cmd_args = cmd_data.get("args", [])
                    if isinstance(cmd_args, str):
                        cmd_args = [cmd_args]
                    if not isinstance(cmd_args, list):
                        cmd_args = []
                    if cmd_name and self._execute_command(cmd_name, cmd_args, msg):
                        return
                    reply(f"Unknown command: {cmd_name}", status="error")
                    return

            parts = content.split()
            if parts and (
                self.command_prefix is None or content.startswith(self.command_prefix)
            ):
                command_name = (
                    parts[0][len(self.command_prefix) :]
                    if self.command_prefix
                    else parts[0]
                )
                args = parts[1:]
                self.logger.debug(
                    "Dispatching command %s for %s",
                    command_name,
                    sender,
                )
                if self._execute_command(command_name, args, msg):
                    return

            # NLP Intent matching
            if self.config.nlp_enabled:
                intent_name, score = self.nlp.predict(content)
                if intent_name and intent_name in self.intents:
                    self.logger.debug(
                        "NLP Intent Matched: %s (score: %.2f)",
                        intent_name,
                        score,
                    )
                    msg.intent = intent_name
                    msg.intent_score = score
                    try:
                        run_sync(self.intents[intent_name], msg)
                        return
                    except Exception:
                        self.logger.exception(
                            "Error executing intent %s",
                            intent_name,
                        )

            for callback in self.delivery_callbacks:
                run_sync(callback, msg)

        except Exception:
            self.logger.exception("Error processing message from %s", sender)

    def _is_command_text(self, content: str) -> bool:
        """True when content starts with a registered command name."""
        parts = content.split()
        if not parts:
            return False
        name = parts[0]
        if self.command_prefix:
            if not name.startswith(self.command_prefix):
                return False
            name = name[len(self.command_prefix) :]
        return name in self.commands

    def _message_received(self, message):
        """Handle received messages."""
        try:
            sender = RNS.hexrep(message.source_hash, delimit=False)
            receipt = RNS.hexrep(message.hash, delimit=False)

            with self._receive_lock:
                if receipt in self.receipts:
                    self.logger.debug(
                        "Duplicate delivery of %s from %s ignored",
                        receipt,
                        sender,
                    )
                    return
                self.receipts.append(receipt)
                if len(self.receipts) > 100:
                    del self.receipts[:-100]

            self.logger.debug("Message %s received from %s", receipt, sender)

            event_data = {
                "message": message,
                "sender": sender,
                "receipt": receipt,
            }

            ctx = MiddlewareContext(MiddlewareType.PRE_EVENT, event_data)
            if self.middleware.execute(MiddlewareType.PRE_EVENT, ctx) is None:
                return

            event = Event("message_received", event_data)
            self.events.dispatch(event)

            if not event.cancelled:
                # Verify message signature if enabled
                if verify_incoming_message(self, message, sender):
                    self._process_message(message, sender)
                else:
                    RNS.log(
                        f"Rejected message from {sender} due to invalid signature",
                        RNS.LOG_WARNING,
                    )

        except Exception:
            self.logger.exception("Error handling received message")

    def received(self, function):
        """Decorator for registering delivery callbacks.

        Args:
            function: The function to call when a message is delivered.

        """
        self.delivery_callbacks.append(function)
        return function

    def intent(self, name: str, examples: list[str]):
        """Decorator for registering intent handlers.

        Args:
            name: The name of the intent.
            examples: A list of example phrases for this intent.

        """

        def decorator(func):
            self.nlp.add_intent(name, examples)
            self.intents[name] = func
            return func

        return decorator

    def on_first_message(self):
        """Decorator for registering first message handlers"""

        def decorator(func):
            """Registers a function to be called on the first message from a sender."""
            self.first_message_handlers.append(func)
            return func

        return decorator

    def on_message(self):
        """Decorator for registering message handlers"""

        def decorator(func):
            """Registers a function to be called on every message."""
            self.message_handlers.append(func)
            return func

        return decorator

    def on_reaction(self):
        """Decorator for registering reaction handlers.

        Handlers are called as handler(sender, reaction) where reaction
        carries reaction_to, reaction_emoji, and reaction_sender.
        """

        def decorator(func):
            """Registers a function to be called on inbound reactions."""
            self.reaction_handlers.append(func)
            return func

        return decorator

    def ignore_destination(self, destination: str) -> bool:
        """Silently drop all inbound LXMF traffic from a destination.

        Returns False when the router is not running or the hash is invalid.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        self.router.ignore_destination(dest)
        return True

    def unignore_destination(self, destination: str) -> bool:
        """Stop dropping inbound traffic from a destination."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        self.router.unignore_destination(dest)
        return dest not in self.router.ignored_list

    def is_ignored(self, destination: str) -> bool:
        """Check whether inbound traffic from a destination is dropped."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        return dest in self.router.ignored_list

    def allow_destination(self, destination: str) -> bool:
        """Add an identity to the router allow list.

        When the allow list is non-empty, LXMF only accepts deliveries
        from listed identities. Returns False on an invalid hash.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        self.router.allow(dest)
        return True

    def disallow_destination(self, destination: str) -> bool:
        """Remove an identity from the router allow list.

        Operates on the list directly because LXMRouter.disallow pops by
        index in LXMF 1.1.1 and raises instead of removing the entry.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        if dest in self.router.allowed_list:
            self.router.allowed_list.remove(dest)
            return True
        return False

    def prioritise_destination(self, destination: str) -> bool:
        """Mark a destination for prioritised outbound processing."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        self.router.prioritise(dest)
        return True

    def unprioritise_destination(self, destination: str) -> bool:
        """Remove a destination from the prioritised list.

        Operates on the list directly because LXMRouter.unprioritise in
        LXMF 1.1.1 references an unbound name and always fails.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        if dest in self.router.prioritised_list:
            self.router.prioritised_list.remove(dest)
            return True
        return False

    def set_inbound_stamp_cost(self, stamp_cost: int | None) -> bool:
        """Require a proof-of-work stamp for inbound deliveries.

        Args:
            stamp_cost: Required stamp value between 1 and 254, or None
                to clear the requirement.

        Returns False when the bot's delivery destination is not
        registered or LXMF rejects the cost.
        """
        if self.router is None or self.local is None:
            return False
        return bool(self.router.set_inbound_stamp_cost(self.local.hash, stamp_cost))

    def enforce_stamps(self) -> bool:
        """Enforce stamp requirements for inbound deliveries."""
        if self.router is None:
            return False
        self.router.enforce_stamps()
        return True

    def ignore_stamps(self) -> bool:
        """Disable stamp enforcement for inbound deliveries."""
        if self.router is None:
            return False
        self.router.ignore_stamps()
        return True

    def generate_ticket(self, destination: str, expiry: int | None = None):
        """Generate an LXMF ticket that lets a destination bypass stamp costs.

        Args:
            destination: The destination hash the ticket is valid for.
            expiry: Seconds until expiry. None uses the LXMF default.

        Returns a dict with expires and ticket keys, or None when a valid
        ticket was recently delivered or the hash is invalid.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return None
        kwargs = {} if expiry is None else {"expiry": expiry}
        entry = self.router.generate_ticket(dest, **kwargs)
        if entry is None:
            return None
        return {"expires": entry[0], "ticket": entry[1]}

    def get_inbound_tickets(self, destination: str):
        """List valid inbound tickets held for a destination, or None."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return None
        return self.router.get_inbound_tickets(dest)

    def ingest_lxm_uri(self, uri: str) -> bool:
        """Import an LXM from an lxm:// URI as if it arrived off the wire."""
        if self.router is None or not isinstance(uri, str):
            return False
        return bool(self.router.ingest_lxm_uri(uri))
