"""Core module for LXMFy bot framework.

This module provides the main LXMFBot class that handles message routing,
command processing, and bot lifecycle management for LXMF-based bots on
the Reticulum Network.
"""

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Any

import RNS
from LXMF import LXMRouter

from ._admin import register_admin_commands
from ._announcing import BOT_DISPLAY_NAME_FILE, AnnounceMixin
from ._cogs import CogMixin
from ._dispatch import DispatchMixin
from ._inbound import InboundMixin
from ._links import LinkMixin
from ._outbound import (
    OutboundMixin,
    PendingSendAnnounceHandler,
    _delivery_dest_hex,
    _delivery_hex,
    _delivery_id_hex,
)
from ._propagation import PropagationMixin
from ._rrc import RRCMixin
from .cogs_core import load_cogs_from_directory
from .config import BotConfig
from .conversations import ConversationManager
from .delivery import DeliveryTracker
from .events import EventManager
from .help import HelpSystem
from .landlock_sandbox import apply_landlock_sandbox, landlock_status_dict
from .middleware import MiddlewareManager
from .moderation import SpamProtection
from .nlp import IntentClassifier
from .permissions import PermissionManager
from .reticulum_config import (
    ensure_isolated_share_instance_disabled,
    is_isolated_reticulum_dir,
    resolve_reticulum_config_dir,
)
from .scheduler import TaskScheduler
from .signatures import SignatureManager
from .storage import JSONStorage, MemoryStorage, MsgPackStorage, SQLiteStorage, Storage
from .transport import Transport
from .validation import format_validation_results, validate_bot

__all__ = ["BOT_DISPLAY_NAME_FILE", "LXMFBot"]


class LXMFBot(
    AnnounceMixin,
    DispatchMixin,
    CogMixin,
    InboundMixin,
    OutboundMixin,
    LinkMixin,
    RRCMixin,
    PropagationMixin,
):
    """Main bot class for handling LXMF messages and commands.

    This class manages the bot's lifecycle, including:
    - Message routing and delivery
    - Command registration and execution
    - Cog (extension) loading and management
    - Spam protection
    - Admin privileges
    """

    def __init__(self, name: str | None = None, **kwargs: Any):
        """Initialize a new LXMFBot instance.

        Args:
            name: Optional bot name, same as the name config key.
            **kwargs: Override default configuration settings

        """
        if name is not None:
            kwargs["name"] = name
        self.config = BotConfig(**kwargs)
        self.commands = {}
        self.cogs = {}
        self.first_message_handlers = []
        self.message_handlers = []
        self.reaction_handlers = []
        self.delivery_callbacks = []
        self.receipts = []
        self._receive_lock = threading.Lock()
        self._delivery_lock = threading.Lock()
        self._last_pending_flush = 0.0
        queue_size = max(1, int(getattr(self.config, "message_queue_size", 50) or 50))
        self.queue = Queue(maxsize=queue_size)
        self.announce_time = 600
        self.router = None
        self.local = None
        self.logger = logging.getLogger("lxmfy")
        self._configure_logging()
        self.thread_pool = ThreadPoolExecutor(
            max_workers=5,
        )  # For offloading CPU-bound or blocking I/O tasks
        self.scheduler = TaskScheduler(self)  # Initialize the scheduler

        if self.config.config_path:
            self.config_path = self.config.config_path
        else:
            self.config_path = os.path.join(os.getcwd(), "config")

        os.makedirs(self.config_path, exist_ok=True)
        if self.config.test_mode and not self.config.reticulum_config_dir:
            self.reticulum_config_dir = os.path.abspath(self.config_path)
        else:
            self.reticulum_config_dir = resolve_reticulum_config_dir(
                self.config.reticulum_config_dir,
                self.config_path,
            )
        os.makedirs(self.reticulum_config_dir, exist_ok=True)
        if not self.config.test_mode and is_isolated_reticulum_dir(
            self.reticulum_config_dir,
            self.config_path,
        ):
            ensure_isolated_share_instance_disabled(self.reticulum_config_dir)

        if self.config.storage_type == "json":
            self.storage = Storage(JSONStorage(self.config.storage_path))
        elif self.config.storage_type == "sqlite":
            self.storage = Storage(SQLiteStorage(self.config.storage_path))
        elif self.config.storage_type == "msgpack":
            self.storage = Storage(MsgPackStorage(self.config.storage_path))
        elif self.config.storage_type == "memory":
            self.storage = Storage(MemoryStorage())
        else:
            raise ValueError(
                f"Unknown storage_type {self.config.storage_type!r}; "
                "expected 'json', 'sqlite', 'msgpack', or 'memory'",
            )

        self.admins = set(self.config.admins or [])
        self.permissions = PermissionManager(
            storage=self.storage,
            enabled=self.config.permissions_enabled,
            admins=self.admins,
        )

        self.events = EventManager(self.storage)

        self._register_builtin_events()

        self.middleware = MiddlewareManager()

        self.cogs_dir = os.path.join(self.config_path, self.config.cogs_dir)
        if self.config.cogs_enabled:
            os.makedirs(self.cogs_dir, exist_ok=True)
            init_file = os.path.join(self.cogs_dir, "__init__.py")
            if not os.path.exists(init_file):
                open(init_file, "w", encoding="utf-8").close()

        self.transport = Transport(self, self.storage)
        self.delivery = DeliveryTracker(storage=self.storage)
        self.delivery.load_persisted()
        self.spam_protection = SpamProtection(
            storage=self.storage,
            bot=self,
            rate_limit=self.config.rate_limit,
            cooldown=self.config.cooldown,
            max_warnings=self.config.max_warnings,
            warning_timeout=self.config.warning_timeout,
        )

        self.delivery_attempts = {}
        self._load_delivery_attempts()
        self.conversations = ConversationManager(self)

        self.landlock_active = False
        if not self.config.test_mode:
            storage_dir = os.path.abspath(
                os.path.expanduser(self.config.storage_path),
            )
            self.landlock_active = apply_landlock_sandbox(
                storage_dir=storage_dir,
                reticulum_config_dir=self.reticulum_config_dir,
                config_dir=self.config_path,
                cogs_dir=self.cogs_dir,
                config_enabled=self.config.landlock_enabled,
            )

        identity_file = os.path.join(self.config_path, "identity")

        self._owns_reticulum = False
        if not self.config.test_mode:
            # Initialize Reticulum (will raise exception if already running)
            if RNS.Reticulum.get_instance() is None:
                try:
                    RNS.Reticulum(
                        configdir=self.reticulum_config_dir,
                        loglevel=self.config.loglevel,
                    )
                    self._owns_reticulum = True
                except OSError:
                    if RNS.Reticulum.get_instance() is None:
                        raise

            if not os.path.isfile(identity_file):
                RNS.log("No Primary Identity file found, creating new...", RNS.LOG_INFO)
                identity = RNS.Identity(True)
                identity.to_file(identity_file)
            identity = RNS.Identity.from_file(identity_file)
            if identity is None:
                raise RuntimeError(f"Failed to load identity from {identity_file}")
            self.identity = identity
            RNS.log("Loaded identity from file", RNS.LOG_INFO)

            self.router = LXMRouter(
                identity=self.identity,
                storagepath=self.config_path,
                autopeer=self.config.autopeer_propagation,
                autopeer_maxdepth=self.config.autopeer_maxdepth,
                enforce_stamps=self.config.require_stamps,
            )
            self.local = self.router.register_delivery_identity(
                self.identity,
                display_name=self.config.name,
                stamp_cost=self.config.stamp_cost,
            )
            if self.local is None:
                raise RuntimeError("Failed to register delivery identity")
            self._sync_delivery_display_name()
            self.router.register_delivery_callback(self._message_received)
            self.local.set_link_established_callback(
                self._delivery_link_established,
            )

            if self.config.pending_sends_enabled:
                RNS.Transport.register_announce_handler(
                    PendingSendAnnounceHandler(self),
                )

        self._configure_propagation()

        if self.local:
            RNS.log(
                f"LXMF Router ready to receive on: {RNS.prettyhexrep(self.local.hash)}",
                RNS.LOG_INFO,
            )
        else:
            # Test mode - create mock components
            if os.path.isfile(identity_file):
                identity = RNS.Identity.from_file(identity_file)
                if identity is None:
                    raise RuntimeError(
                        f"Failed to load identity from {identity_file}",
                    )
                self.identity = identity
            else:
                self.identity = RNS.Identity()  # Create a basic identity for testing
                if self.config.config_path:
                    self.identity.to_file(identity_file)

            self.router = None
            self.local = None

        self.announce_enabled = self.config.announce_enabled
        self.announce_time = self.config.announce

        if self.announce_enabled and not self.config.test_mode:
            if self.announce_time > 0:
                # Schedule the announce task. announce_now throttles on the
                # announce interval file, so a sub-minute cron step still
                # respects announce_time.
                minutes = max(1, self.announce_time // 60)
                self.scheduler.add_task(
                    "announce_task",
                    self.announce_now,
                    f"*/{minutes} * * * *",  # Convert seconds to minutes for cron
                )
            if self.config.announce_immediately:
                self.announce_now(force=True)
                RNS.log("Initial announce sent", RNS.LOG_INFO)

        self.hot_reloading = self.config.hot_reloading
        self.command_prefix = self.config.command_prefix

        self.help_system = HelpSystem(self)
        register_admin_commands(self)

        self.nlp = IntentClassifier(threshold=self.config.nlp_threshold)
        self.intents = {}  # {intent_name: callback}

        self.link_handlers = []
        self.links = {}  # {dest_hash: Link}

        self.rrc = None
        self.rrc_handlers = []
        self._init_rrc()

        self.signature_manager = SignatureManager(
            self,
            verification_enabled=self.config.signature_verification_enabled,
            require_signatures=self.config.require_message_signatures,
            request_unknown_identities=self.config.request_unknown_identities,
        )

        self._load_persisted_queue()

        if self.config.cogs_enabled:
            load_cogs_from_directory(self)

    def _configure_logging(self) -> None:
        level = self.config.log_level
        if level is None:
            return
        if isinstance(level, str):
            level = logging.getLevelNamesMapping().get(level.upper())
            if level is None:
                raise ValueError(
                    f"Unknown log_level {self.config.log_level!r}",
                )
        logger = logging.getLogger("lxmfy")
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    "%H:%M:%S",
                ),
            )
            logger.addHandler(handler)
        logger.setLevel(level)

    def get_debugger(self):
        """Return a Debugger bound to this bot."""
        from .debugger import Debugger

        return Debugger(bot=self)

    def diagnose_destination(
        self,
        destination: str,
        *,
        request_path: bool = False,
        wait: float = 0.0,
    ) -> dict:
        """Probe path and identity for a destination hash.

        Args:
            destination: Hex destination hash.
            request_path: Whether to request a path if missing.
            wait: Seconds to wait for a path after requesting.

        Returns:
            Dict describing identity/path status and hints.

        """
        return (
            self.get_debugger()
            .probe_destination(
                destination,
                request_path=request_path,
                wait=wait,
            )
            .to_dict()
        )

    def diagnose_connectivity(
        self,
        destination: str | None = None,
        *,
        request_path: bool = False,
        wait: float = 0.0,
    ) -> dict:
        """Run a connectivity doctor report for this bot.

        Args:
            destination: Optional peer hash to include in send diagnosis.
            request_path: Request a path when probing destination.
            wait: Seconds to wait for path discovery.

        Returns:
            Structured doctor report dict.

        """
        return (
            self.get_debugger()
            .run_doctor(
                destination,
                request_path=request_path,
                wait=wait,
            )
            .to_dict()
        )

    def on_delivery_event(self, callback=None):
        """Subscribe to the outbound delivery event stream.

        Usable as bot.on_delivery_event(fn) or as a decorator
        @bot.on_delivery_event(). Subscribers receive event dicts with
        ts, stage (queued, deferred, dispatched, delivered, failed,
        cancelled, dropped), and destination/message_id/hash/reason
        fields when available.
        """
        if callback is None:
            return self.delivery.subscribe
        return self.delivery.subscribe(callback)

    def get_landlock_status(self) -> dict[str, bool]:
        """Return Landlock LSM sandbox availability and activation state."""
        return landlock_status_dict(
            active=self.landlock_active,
            config_enabled=self.config.landlock_enabled,
        )

    def run(self, delay=10):
        """Run the bot"""
        self.scheduler.start()  # Start the scheduler
        try:
            while True:
                # Process outgoing queue with a timeout to prevent hanging
                while not self.queue.empty():
                    try:
                        lxm = self.queue.get(block=False)
                    except Exception:
                        break
                    try:
                        if self.router:
                            self.router.handle_outbound(lxm)
                            self.delivery.record(
                                "dispatched",
                                destination=_delivery_dest_hex(lxm),
                                message_id=_delivery_id_hex(lxm),
                                hash=_delivery_hex(lxm),
                            )
                        self._persist_queue()
                    except Exception as e:
                        self.logger.exception(
                            "Outbound send failed, requeueing",
                        )
                        self.delivery.record(
                            "failed",
                            destination=_delivery_dest_hex(lxm),
                            reason=str(e)[:120],
                        )
                        if not self._enqueue_outbound(lxm):
                            self.logger.exception(
                                "Failed to requeue after outbound error"
                            )
                        break

                retry_interval = max(
                    0,
                    int(getattr(self.config, "pending_sends_retry", 300) or 0),
                )
                if retry_interval and (
                    time.time() - self._last_pending_flush >= retry_interval
                ):
                    self._last_pending_flush = time.time()
                    self._flush_pending_sends()

                time.sleep(delay)

        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def request_page(
        self,
        destination_hash: str,
        page_path: str,
        field_data: dict | None = None,
    ) -> dict:
        """Request a page from a destination.

        Args:
            destination_hash: The destination hash.
            page_path: The path to the page.
            field_data: Optional field data to send with the request.

        Returns:
            The response from the destination.

        """
        try:
            dest_hash_bytes = bytes.fromhex(destination_hash)
            return self.transport.request_page(dest_hash_bytes, page_path, field_data)
        except Exception:
            self.logger.exception("Error requesting page")
            raise

    def cleanup(self):
        """Clean up resources."""
        RNS.log("Cleaning up LXMFBot...", RNS.LOG_DEBUG)
        try:
            self._persist_queue()
        except Exception:
            self.logger.exception("Failed to persist queue during cleanup")
        self.conversations.cancel_all()
        if hasattr(self, "rrc") and self.rrc:
            try:
                self.rrc.shutdown()
            except Exception:
                self.logger.exception("RRC shutdown failed")
        self.transport.cleanup()
        self.thread_pool.shutdown(wait=False)
        self.scheduler.stop()
        if hasattr(self, "router") and self.router:
            try:
                self.router.exit_handler()
            except Exception as e:
                self.logger.debug("Router exit handler failed: %s", e)

        # Ensure Reticulum exits cleanly, but only if this bot started it.
        # A shared instance may still be serving other bots or tests.
        if not self.config.test_mode and self._owns_reticulum:
            try:
                RNS.Reticulum.exit_handler()
            except Exception as e:
                self.logger.debug("Reticulum exit handler failed: %s", e)
        RNS.log("LXMFBot cleanup complete", RNS.LOG_DEBUG)

    def validate(self) -> str:
        """Run validation checks and return formatted results."""
        results = validate_bot(self)
        return format_validation_results(results)
