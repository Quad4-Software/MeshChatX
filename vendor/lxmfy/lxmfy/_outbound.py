"""Outbound message delivery for LXMFBot."""

from __future__ import annotations

import time
from queue import Full
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import RNS
from LXMF import LXMessage

from .attachments import Attachment, pack_attachment
from .delivery import DeliveryTracker
from .lxmf_fields import pack_reaction, pack_reply
from .signatures import sign_outgoing_message
from .validation import destination_bytes

if TYPE_CHECKING:
    import logging
    import threading
    from queue import Queue

    from LXMF import LXMRouter

    from .config import BotConfig
    from .core import LXMFBot
    from .storage import Storage


class PendingSendAnnounceHandler:
    """Retries deferred outbound messages when their destination announces."""

    aspect_filter = "lxmf.delivery"

    def __init__(self, bot: LXMFBot):
        self.bot = bot

    def received_announce(self, destination_hash, announced_identity, app_data):
        self.bot._flush_pending_sends(
            RNS.hexrep(destination_hash, delimit=False),
        )


def _hex_or_none(value) -> str | None:
    if isinstance(value, bytes):
        return RNS.hexrep(value, delimit=False)
    return None


def _delivery_hex(lxm) -> str | None:
    """Hex message hash for an lxm-like object, or None."""
    return _hex_or_none(getattr(lxm, "hash", None))


def _delivery_id_hex(lxm) -> str | None:
    """Hex message_id for an lxm-like object, or None."""
    return _hex_or_none(getattr(lxm, "message_id", None))


def _delivery_dest_hex(lxm) -> str | None:
    """Hex destination hash for an lxm-like object, or None."""
    dest = getattr(lxm, "destination", None)
    if dest is not None:
        hashed = _hex_or_none(getattr(dest, "hash", None))
        if hashed:
            return hashed
    return _hex_or_none(getattr(lxm, "destination_hash", None))


class OutboundMixin:
    """Outbound queueing, delivery retries, and persistence."""

    config: BotConfig
    delivery: DeliveryTracker
    delivery_attempts: dict
    local: RNS.Destination | None
    logger: logging.Logger
    queue: Queue
    router: LXMRouter | None
    storage: Storage
    _delivery_lock: threading.Lock

    def send(
        self,
        destination: str,
        message: str,
        title: str = "Reply",
        lxmf_fields: dict | None = None,
        stamp_cost: int | None = None,
        opportunistic: bool | None = None,
        method=None,
        include_ticket: bool | None = None,
        defer: bool | None = None,
        reply_to: bytes | str | None = None,
        quote: bytes | str | None = None,
        thread: bytes | str | None = None,
    ):
        """Send a message to a destination, optionally with custom LXMF fields.

        Args:
            destination: The destination hash.
            message: The message content (will be utf-8 encoded).
            title: The message title (optional, will be utf-8 encoded).
            lxmf_fields: Optional dictionary of LXMF fields.
            stamp_cost: Optional outbound stamp cost for this message.
                If omitted, LXMF takes the cost from the peer announce.
                BotConfig.stamp_cost only applies to inbound delivery.
            opportunistic: Whether to use opportunistic sending (try direct, then prop).
                           If None, uses config.opportunistic_sending.
            method: Optional explicit LXMF delivery method override for crash recovery.
            include_ticket: Whether to include an LXMF reply ticket.
                If None, uses BotConfig.include_tickets (default True).
            defer: When the destination identity is unknown, hold the message
                and retry after its next announce instead of dropping it.
                If None, uses BotConfig.pending_sends_enabled (default True).
            reply_to: Hash (bytes or hex) of the LXMessage this message replies
                to. Sets FIELD_REPLY_TO so clients render it as a threaded reply.
            quote: Quoted text shown alongside the reply in clients that render
                FIELD_REPLY_QUOTE.
            thread: Thread root hash (bytes or hex) for FIELD_THREAD. Defaults
                to reply_to when only reply_to is given.

        """
        reply_fields = pack_reply(reply_to, quote=quote, thread=thread)
        if reply_fields:
            lxmf_fields = {**(lxmf_fields or {}), **reply_fields}

        if self.config.test_mode:
            # In test mode, just queue a mock message
            mock_message = SimpleNamespace()
            try:
                mock_message.destination_hash = bytes.fromhex(destination)
            except ValueError:
                mock_message.destination_hash = destination.encode("utf-8")
            mock_message.content = message.encode("utf-8")
            mock_message.title = title.encode("utf-8") if title else None
            mock_message.fields = lxmf_fields
            mock_message.desired_method = method
            mock_message.include_ticket = (
                self.config.include_tickets
                if include_ticket is None
                else include_ticket
            )
            mock_message.stamp_cost = stamp_cost
            return self._enqueue_outbound(mock_message)

        try:
            dest_hash_bytes = bytes.fromhex(destination)
        except ValueError:
            RNS.log(f"Invalid destination hash format: {destination}", RNS.LOG_ERROR)
            return False

        if len(dest_hash_bytes) != RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
            RNS.log(f"Invalid destination hash length for {destination}", RNS.LOG_ERROR)
            return False

        identity_instance = RNS.Identity.recall(dest_hash_bytes)
        if identity_instance is None:
            RNS.log(
                f"Could not recall an Identity for {destination}. Requesting path...",
                RNS.LOG_WARNING,
            )
            RNS.Transport.request_path(dest_hash_bytes)
            should_defer = self.config.pending_sends_enabled if defer is None else defer
            if should_defer:
                self._defer_pending_send(
                    destination,
                    message,
                    title,
                    lxmf_fields,
                    stamp_cost,
                    method,
                    include_ticket,
                )
                self.delivery.record(
                    "deferred",
                    destination=destination,
                    title=title,
                    reason="identity_unknown",
                )
                RNS.log(
                    f"Message for {destination} held until its identity is learned",
                    RNS.LOG_INFO,
                )
                return True
            RNS.log(
                "Path requested. If the network knows a path, you will receive an announce shortly.",
                RNS.LOG_INFO,
            )
            return False
        lxmf_destination_obj = RNS.Destination(
            identity_instance,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        # Ensure message and title are bytes
        message_bytes = message.encode("utf-8")
        title_bytes = title.encode("utf-8") if title else None

        # Determine delivery method based on retry count
        attempts = self.delivery_attempts.get(destination, 0)
        max_retries = self.config.direct_delivery_retries

        # Check if we should prefer propagation
        has_prop_node = (
            self.config.propagation_node
            or self.config.autopeer_propagation
            or (
                self.router.get_outbound_propagation_node() is not None
                if self.router
                else False
            )
        )

        is_opportunistic = (
            opportunistic
            if opportunistic is not None
            else self.config.opportunistic_sending
        )

        if attempts >= max_retries and self.config.propagation_fallback_enabled:
            if not has_prop_node and not self.config.enable_propagation_node:
                RNS.log(
                    f"Propagation fallback triggered for {destination}, but no propagation_node configured, "
                    "autopeer disabled, and bot is not a propagation node. Message will likely fail. "
                    "Configure propagation_node, enable autopeer_propagation, run as propagation node, "
                    "or disable propagation_fallback_enabled.",
                    RNS.LOG_ERROR,
                )
            desired_method = LXMessage.PROPAGATED
            RNS.log(
                f"Using propagation for {destination} after {attempts} failed direct attempts",
                RNS.LOG_INFO,
            )
        elif is_opportunistic:
            # Packet delivery without requiring a Link first. Works much more
            # reliably through public TCP/backbone entrypoints than DIRECT.
            desired_method = LXMessage.OPPORTUNISTIC
            peer_ratchet = RNS.Identity.current_ratchet_id(dest_hash_bytes)
            if peer_ratchet is None:
                RNS.log(
                    f"No known ratchet for {destination}. "
                    "Opportunistic delivery will use static identity encryption "
                    "until a peer announce arrives.",
                    RNS.LOG_DEBUG,
                )
        else:
            desired_method = LXMessage.DIRECT

        if method is not None:
            desired_method = method

        # Use the peer stamp cost from LXMF unless the caller overrides it.
        # BotConfig.stamp_cost is only for inbound delivery identity setup.
        do_include_ticket = (
            self.config.include_tickets if include_ticket is None else include_ticket
        )

        lxm = LXMessage(
            lxmf_destination_obj,
            self.local,
            cast("Any", message_bytes),
            title=cast("Any", title_bytes),
            desired_method=desired_method,
            fields=lxmf_fields,
            stamp_cost=stamp_cost,
            include_ticket=do_include_ticket,
        )

        # Register callbacks to reset counter on success or track failure
        def on_delivery_success(_message):
            with self._delivery_lock:
                if destination in self.delivery_attempts:
                    self.delivery_attempts[destination] = 0
                    self._save_delivery_attempts()
                    RNS.log(
                        f"Delivery successful to {destination}, reset retry counter",
                        RNS.LOG_DEBUG,
                    )
            self.delivery.record(
                "delivered",
                destination=destination,
                hash=_delivery_hex(_message),
            )

        def on_delivery_failure(_message):
            with self._delivery_lock:
                current_attempts = self.delivery_attempts.get(destination, 0)
                self.delivery_attempts[destination] = current_attempts + 1
                self._save_delivery_attempts()

            self.delivery.record(
                "failed",
                destination=destination,
                hash=_delivery_hex(_message),
                attempts=current_attempts + 1,
            )

            if current_attempts + 1 < max_retries:
                RNS.log(
                    f"Delivery failed to {destination}, attempt {current_attempts + 1}/{max_retries}",
                    RNS.LOG_WARNING,
                )
            else:
                RNS.log(
                    f"Delivery failed to {destination} after {current_attempts + 1} attempts",
                    RNS.LOG_ERROR,
                )

        lxm.register_delivery_callback(on_delivery_success)
        lxm.register_failed_callback(on_delivery_failure)

        # Sign the message (pass-through for LXMF's built-in signing)
        lxm = sign_outgoing_message(self, lxm)

        if not self._enqueue_outbound(lxm):
            RNS.log(
                f"Failed to queue message for {destination}: outbound queue full",
                RNS.LOG_ERROR,
            )
            return False
        RNS.log(
            f"Message queued for {destination} (method: {desired_method}, opportunistic: {is_opportunistic})",
            RNS.LOG_DEBUG,
        )
        return True

    @staticmethod
    def _destination_hash_len() -> int:
        return RNS.Reticulum.TRUNCATED_HASHLENGTH // 8

    def _is_valid_destination_hex(self, destination: str) -> bool:
        if not isinstance(destination, str) or not destination:
            return False
        try:
            raw = bytes.fromhex(destination)
        except ValueError:
            return False
        return len(raw) == self._destination_hash_len()

    def _enqueue_outbound(self, lxm) -> bool:
        """Enqueue an outbound message without blocking. Drops oldest if full."""
        try:
            self.queue.put_nowait(lxm)
        except Full:
            try:
                dropped = self.queue.get_nowait()
                self.logger.warning(
                    "Outbound queue full (max=%s), dropped oldest message",
                    self.queue.maxsize,
                )
                self.delivery.record(
                    "dropped",
                    destination=_delivery_dest_hex(dropped),
                    reason="queue_full",
                )
                del dropped
                self.queue.put_nowait(lxm)
            except Exception:
                self.logger.exception("Failed to enqueue outbound message")
                return False
        self._persist_queue()
        self.delivery.record(
            "queued",
            destination=_delivery_dest_hex(lxm),
            message_id=_delivery_id_hex(lxm),
            hash=_delivery_hex(lxm),
            method=getattr(lxm, "desired_method", None),
        )
        return True

    def _persist_queue(self):
        """Persist the outgoing message queue to storage."""
        if getattr(self.config, "message_persistence_enabled", False) is not True:
            return

        max_items = max(1, int(self.queue.maxsize or 50))
        max_content = 65536
        queued_messages = []
        with self.queue.mutex:
            snapshot = list(self.queue.queue)
        for lxm in snapshot:
            if len(queued_messages) >= max_items:
                break
            try:
                destination = RNS.hexrep(lxm.destination_hash, delimit=False)
                if not self._is_valid_destination_hex(destination):
                    self.logger.warning(
                        "Skipping persist for invalid destination hash length: %s",
                        destination,
                    )
                    continue
                content = (
                    lxm.content.decode("utf-8")
                    if isinstance(lxm.content, bytes)
                    else lxm.content
                )
                if (
                    isinstance(content, str)
                    and len(content.encode("utf-8")) > max_content
                ):
                    self.logger.warning(
                        "Skipping persist for oversized message to %s",
                        destination,
                    )
                    continue
                msg_data = {
                    "destination": destination,
                    "content": content,
                    "title": lxm.title.decode("utf-8")
                    if isinstance(lxm.title, bytes)
                    else lxm.title,
                    "fields": lxm.fields,
                    "method": lxm.desired_method,
                }
                queued_messages.append(msg_data)
            except Exception:
                self.logger.exception("Failed to serialize message for persistence")

        self.storage.set("persisted_queue", queued_messages)

    def _load_persisted_queue(self):
        """Load persisted messages back into the queue."""
        if getattr(self.config, "message_persistence_enabled", False) is not True:
            return

        persisted = self.storage.get("persisted_queue", [])
        if not persisted:
            return
        if not isinstance(persisted, list):
            self.storage.set("persisted_queue", [])
            return

        max_items = max(1, int(self.queue.maxsize or 50))
        if len(persisted) > max_items:
            self.logger.warning(
                "Truncating persisted queue from %s to %s messages",
                len(persisted),
                max_items,
            )
            persisted = persisted[-max_items:]

        RNS.log(f"Restoring {len(persisted)} messages from persistence", RNS.LOG_INFO)
        deferred = []
        for msg_data in persisted:
            if not isinstance(msg_data, dict):
                continue
            destination = msg_data.get("destination")
            if not isinstance(destination, str) or not self._is_valid_destination_hex(
                destination,
            ):
                self.logger.warning(
                    "Dropping persisted message with invalid destination: %s",
                    destination,
                )
                continue
            title = msg_data.get("title")
            try:
                queued = self.send(
                    destination,
                    msg_data["content"],
                    title=title if isinstance(title, str) else "Reply",
                    lxmf_fields=msg_data.get("fields"),
                    method=msg_data.get("method"),
                )
                if not queued:
                    deferred.append(msg_data)
            except Exception:
                self.logger.exception("Failed to restore message from persistence")
                deferred.append(msg_data)

        # Keep successfully requeued messages on disk until outbound drain.
        self._persist_queue()
        if deferred:
            current = self.storage.get("persisted_queue", [])
            if not isinstance(current, list):
                current = []
            merged = list(current) + deferred
            if len(merged) > max_items:
                merged = merged[-max_items:]
            self.storage.set("persisted_queue", merged)

    def _defer_pending_send(
        self,
        destination: str,
        message: str,
        title,
        lxmf_fields,
        stamp_cost,
        method,
        include_ticket,
    ) -> None:
        """Hold a message whose destination identity is not yet known."""
        entry = {
            "destination": destination,
            "content": message,
            "title": title,
            "fields": lxmf_fields,
            "stamp_cost": stamp_cost,
            "method": method,
            "include_ticket": include_ticket,
            "queued_at": int(time.time()),
            "attempts": 0,
        }
        with self._delivery_lock:
            pending = self.storage.get("pending_sends", [])
            if not isinstance(pending, list):
                pending = []
            pending = [e for e in pending if isinstance(e, dict)]
            pending.append(entry)
            max_pending = max(1, int(self.config.pending_sends_max or 200))
            if len(pending) > max_pending:
                dropped = len(pending) - max_pending
                pending = pending[-max_pending:]
                self.logger.warning(
                    "Pending send backlog full, dropped %s oldest message(s)",
                    dropped,
                )
                self.delivery.record(
                    "dropped",
                    reason="pending_backlog_full",
                    attempts=dropped,
                )
            self.storage.set("pending_sends", pending)

    def _flush_pending_sends(self, destination: str | None = None) -> None:
        """Retry held messages. When destination is set, only that hash runs."""
        if not self.config.pending_sends_enabled:
            return
        if self.config.test_mode or self.router is None:
            return

        now = int(time.time())
        ttl = max(0, int(self.config.pending_sends_ttl or 0))
        with self._delivery_lock:
            pending = self.storage.get("pending_sends", [])
            if not isinstance(pending, list) or not pending:
                return
            kept, retry = [], []
            for entry in pending:
                if not isinstance(entry, dict):
                    continue
                if ttl and now - int(entry.get("queued_at", now)) > ttl:
                    self.logger.debug(
                        "Dropping expired pending send to %s",
                        entry.get("destination"),
                    )
                    self.delivery.record(
                        "dropped",
                        destination=entry.get("destination"),
                        reason="expired",
                    )
                    continue
                if destination is None or entry.get("destination") == destination:
                    retry.append(entry)
                else:
                    kept.append(entry)

        for entry in retry:
            dest = entry.get("destination")
            if not isinstance(dest, str) or not self._is_valid_destination_hex(
                dest,
            ):
                continue
            attempts = int(entry.get("attempts", 0)) + 1
            if attempts > 50:
                self.logger.warning(
                    "Dropping pending send to %s after %s attempts",
                    dest,
                    attempts,
                )
                self.delivery.record(
                    "dropped",
                    destination=dest,
                    reason="max_attempts",
                    attempts=attempts,
                )
                continue
            entry["attempts"] = attempts
            if self.send(
                dest,
                entry.get("content") or "",
                title=entry.get("title") or "Reply",
                lxmf_fields=entry.get("fields"),
                stamp_cost=entry.get("stamp_cost"),
                method=entry.get("method"),
                include_ticket=entry.get("include_ticket"),
                defer=False,
            ):
                self.logger.debug(
                    "Pending send to %s dispatched",
                    dest,
                )
            else:
                kept.append(entry)

        with self._delivery_lock:
            self.storage.set("pending_sends", kept)

    def send_with_attachment(
        self,
        destination: str,
        message: str,
        attachment: Attachment,
        title: str = "Reply",
        stamp_cost: int | None = None,
        opportunistic: bool | None = None,
        include_ticket: bool | None = None,
    ):
        """Send a message with an attachment to a destination.

        Args:
            destination: The destination hash.
            message: The message content.
            attachment: The attachment to send.
            title: The message title.
            stamp_cost: Optional outbound stamp cost for this message.
            opportunistic: Whether to use opportunistic sending.
            include_ticket: Whether to include an LXMF reply ticket.

        """
        attachment_specific_fields = pack_attachment(attachment)
        self.send(
            destination,
            message,
            title=title,
            lxmf_fields=attachment_specific_fields,
            stamp_cost=stamp_cost,
            opportunistic=opportunistic,
            include_ticket=include_ticket,
        )

    def _load_delivery_attempts(self):
        """Load delivery attempts from storage."""
        self.delivery_attempts = self.storage.get("delivery_attempts", {})

    def _save_delivery_attempts(self):
        """Save delivery attempts to storage."""
        self.storage.set("delivery_attempts", self.delivery_attempts)

    def _reset_delivery_attempts(self, destination: str):
        """Reset delivery attempts for a destination when they come back online.

        Args:
            destination: The destination hash.

        """
        with self._delivery_lock:
            if (
                destination in self.delivery_attempts
                and self.delivery_attempts[destination] > 0
            ):
                self.delivery_attempts[destination] = 0
                self._save_delivery_attempts()
                RNS.log(
                    f"Reset delivery attempts for {destination} (user came back online)",
                    RNS.LOG_DEBUG,
                )

    def react(self, destination: str, message_hash: str, reaction: str) -> bool:
        """Send a reaction to a message.

        Args:
            destination: The destination hash of the message author.
            message_hash: The full LXMessage hash being reacted to, hex.
            reaction: The reaction content, usually a single emoji.

        Reactions travel as an LXMF FIELD_REACTION dict on an otherwise
        empty message. Clients that understand the field attach it to the
        target message; clients that do not see a short empty delivery.
        """
        try:
            raw = bytes.fromhex(message_hash)
        except (ValueError, TypeError):
            return False
        if len(raw) != 32:
            return False
        return self.send(
            destination,
            "",
            title="",
            lxmf_fields=pack_reaction(raw, reaction),
        )

    def delivery_link_available(self, destination: str) -> bool:
        """Check whether a direct link is up for a destination.

        When True, outbound messages to this destination can deliver over
        an established link instead of opportunistic packets or a
        propagation node.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return False
        return bool(self.router.delivery_link_available(dest))

    def outbound_queue(self) -> list[dict]:
        """Snapshot pending outbound messages.

        Each entry carries hash, message_id, destination, state, and
        progress so callers can feed hashes back into cancel_outbound or
        get_outbound_progress.
        """
        if self.router is None:
            return []
        queue = []
        for lxm in self.router.pending_outbound:
            entry = {
                "hash": RNS.hexrep(lxm.hash, delimit=False) if lxm.hash else None,
                "message_id": RNS.hexrep(lxm.message_id, delimit=False)
                if lxm.message_id
                else None,
                "destination": RNS.hexrep(lxm.destination.hash, delimit=False)
                if getattr(lxm, "destination", None)
                else None,
                "state": lxm.state,
                "progress": lxm.progress,
            }
            queue.append(entry)
        return queue

    def get_outbound_progress(self, lxm_hash: str) -> float | None:
        """Get transfer progress (0.0-1.0) for a pending outbound LXM.

        Accepts a hex hash from outbound_queue. Returns None when the
        message is not in the outbound queue.
        """
        if self.router is None:
            return None
        try:
            raw = bytes.fromhex(lxm_hash)
        except (ValueError, TypeError):
            return None
        return self.router.get_outbound_progress(raw)

    def cancel_outbound(self, message_id: str) -> bool:
        """Cancel a pending outbound message by its message_id.

        The message_id is available from outbound_queue entries.
        Returns False when no pending message carries that id.
        """
        if self.router is None:
            return False
        try:
            raw = bytes.fromhex(message_id)
        except (ValueError, TypeError):
            return False
        pending = {entry.get("message_id") for entry in self.outbound_queue()}
        if message_id not in pending:
            return False
        self.router.cancel_outbound(raw)
        self.delivery.record(
            "cancelled",
            message_id=message_id,
            reason="admin_cancel",
        )
        return True

    def get_outbound_ticket(self, destination: str) -> bytes | None:
        """Get a valid outbound ticket held for a destination, or None.

        Outbound tickets are tickets a peer sent us so our deliveries to
        them satisfy their stamp requirement.
        """
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return None
        return self.router.get_outbound_ticket(dest)

    def get_outbound_ticket_expiry(self, destination: str) -> float | None:
        """Get the expiry timestamp of the outbound ticket for a destination."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return None
        return self.router.get_outbound_ticket_expiry(dest)

    def get_outbound_stamp_cost(self, destination: str) -> int | None:
        """Get the stamp cost a destination announced it requires, or None."""
        dest = destination_bytes(destination)
        if self.router is None or dest is None:
            return None
        return self.router.get_outbound_stamp_cost(dest)

    @staticmethod
    def _hash32_bytes(value) -> bytes | None:
        if isinstance(value, (bytes, bytearray)):
            raw = bytes(value)
        elif isinstance(value, str):
            try:
                raw = bytes.fromhex(value.strip())
            except ValueError:
                return None
        else:
            return None
        return raw if len(raw) == RNS.Identity.HASHLENGTH // 8 else None

    def has_message(self, message_hash: bytes | str) -> bool:
        """Check whether an inbound LXM hash was already delivered."""
        raw = self._hash32_bytes(message_hash)
        if raw is None or self.router is None:
            return False
        return bool(self.router.has_message(raw))

    def inbound_count(self) -> int:
        """Number of inbound resource transfers currently in progress."""
        if self.router is None:
            return 0
        return int(self.router.inbound_count())

    def inbound_transfers(self) -> list[dict]:
        """Snapshot active inbound resource transfers.

        Each entry carries the resource hash, byte sizes, transfer
        progress, and status so callers can monitor or cancel large
        inbound deliveries.
        """
        if self.router is None:
            return []
        transfers = []
        for resource in self.router.inbound_resources():
            entry = {
                "hash": RNS.hexrep(resource.hash, delimit=False)
                if resource.hash
                else None,
                "size": getattr(resource, "size", None),
                "status": getattr(resource, "status", None),
                "progress": None,
                "transfer_size": None,
            }
            for key, getter in (
                ("progress", "get_progress"),
                ("transfer_size", "get_transfer_size"),
            ):
                try:
                    entry[key] = getattr(resource, getter)()
                except Exception:
                    entry[key] = None
            transfers.append(entry)
        return transfers

    def cancel_inbound(self, resource_hash: bytes | str) -> bool:
        """Cancel an active inbound resource transfer by its hash.

        The hash is available from inbound_transfers. Returns False when
        no active transfer carries that hash.
        """
        raw = self._hash32_bytes(resource_hash)
        if raw is None or self.router is None:
            return False
        active = {entry.get("hash") for entry in self.inbound_transfers()}
        hex_hash = RNS.hexrep(raw, delimit=False)
        if hex_hash not in active:
            return False
        self.router.cancel_inbound(raw)
        return True

    def cancel_all_inbound(self) -> int:
        """Cancel all active inbound resource transfers.

        Returns the number of transfers that were in progress.
        """
        if self.router is None:
            return 0
        count = self.inbound_count()
        self.router.cancel_all_inbound()
        return count
