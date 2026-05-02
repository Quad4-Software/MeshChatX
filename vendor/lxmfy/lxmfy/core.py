"""Core module for LXMFy bot framework.

This module provides the main LXMFBot class that handles message routing,
command processing, and bot lifecycle management for LXMF-based bots on
the Reticulum Network.
"""

import importlib
import inspect
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Callable
from types import SimpleNamespace

import RNS
from LXMF import LXMessage, LXMRouter

from .attachments import Attachment, pack_attachment
from .cogs_core import load_cogs_from_directory
from .commands import Command
from .config import BotConfig
from .events import Event, EventManager, EventPriority
from .help import HelpSystem
from .middleware import MiddlewareContext, MiddlewareManager, MiddlewareType
from .moderation import SpamProtection
from .nlp import IntentClassifier
from .permissions import DefaultPerms, PermissionManager
from .scheduler import TaskScheduler
from .signatures import SignatureManager, sign_outgoing_message, verify_incoming_message
from .storage import JSONStorage, MemoryStorage, SQLiteStorage, Storage
from .transport import Transport
from .validation import format_validation_results, validate_bot

BOT_DISPLAY_NAME_FILE = "bot_display_name.txt"


class LXMFBot:
    """Main bot class for handling LXMF messages and commands.

    This class manages the bot's lifecycle, including:
    - Message routing and delivery
    - Command registration and execution
    - Cog (extension) loading and management
    - Spam protection
    - Admin privileges
    """

    def __init__(self, **kwargs):
        """Initialize a new LXMFBot instance.

        Args:
            **kwargs: Override default configuration settings

        """
        self.config = BotConfig(**kwargs)
        self.commands = {}
        self.cogs = {}
        self.first_message_handlers = []
        self.message_handlers = []
        self.delivery_callbacks = []
        self.receipts = []
        self.queue = Queue(maxsize=50)
        self.announce_time = 600
        self.router = None
        self.local = None
        self.logger = logging.getLogger(__name__)
        self.thread_pool = ThreadPoolExecutor(
            max_workers=5,
        )  # For offloading CPU-bound or blocking I/O tasks
        self.scheduler = TaskScheduler(self)  # Initialize the scheduler

        if self.config.config_path:
            self.config_path = self.config.config_path
        else:
            self.config_path = os.path.join(os.getcwd(), "config")

        os.makedirs(self.config_path, exist_ok=True)
        if self.config.reticulum_config_dir:
            self.reticulum_config_dir = os.path.abspath(
                os.path.expanduser(self.config.reticulum_config_dir),
            )
        else:
            self.reticulum_config_dir = self.config_path
        os.makedirs(self.reticulum_config_dir, exist_ok=True)

        if self.config.storage_type == "json":
            self.storage = Storage(JSONStorage(self.config.storage_path))
        elif self.config.storage_type == "sqlite":
            self.storage = Storage(SQLiteStorage(self.config.storage_path))
        elif self.config.storage_type == "memory":
            self.storage = Storage(MemoryStorage())

        self.permissions = PermissionManager(
            storage=self.storage,
            enabled=self.config.permissions_enabled,
        )

        self.events = EventManager(self.storage)

        self._register_builtin_events()

        self.middleware = MiddlewareManager()

        self.cogs_dir = os.path.join(self.config_path, self.config.cogs_dir)
        os.makedirs(self.cogs_dir, exist_ok=True)

        init_file = os.path.join(self.cogs_dir, "__init__.py")
        if not os.path.exists(init_file):
            open(init_file, "w", encoding="utf-8").close()

        self.transport = Transport(self, self.storage)
        self.spam_protection = SpamProtection(
            storage=self.storage,
            bot=self,
            rate_limit=self.config.rate_limit,
            cooldown=self.config.cooldown,
            max_warnings=self.config.max_warnings,
            warning_timeout=self.config.warning_timeout,
        )

        self._load_delivery_attempts()

        identity_file = os.path.join(self.config_path, "identity")

        if not self.config.test_mode:
            # Initialize Reticulum (will raise exception if already running)
            try:
                RNS.Reticulum(
                    configdir=self.reticulum_config_dir,
                    loglevel=RNS.LOG_VERBOSE,
                )
            except OSError as e:
                if "reinitialise" in str(e).lower():
                    # Reticulum already running, continue
                    pass
                else:
                    raise

            if not os.path.isfile(identity_file):
                RNS.log("No Primary Identity file found, creating new...", RNS.LOG_INFO)
                identity = RNS.Identity(True)
                identity.to_file(identity_file)
            self.identity = RNS.Identity.from_file(identity_file)
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
            self._sync_delivery_display_name()
            self.router.register_delivery_callback(self._message_received)
            self.local.set_link_established_callback(self._link_established)

        if self.router and self.config.enable_propagation_node:
            try:
                self.router.enable_propagation(
                    enforce_stamps=self.config.require_stamps,
                )

                if self.config.message_storage_limit_mb > 0:
                    self.router.set_message_storage_limit(
                        megabytes=self.config.message_storage_limit_mb,
                    )
                    RNS.log(
                        f"Set propagation node message storage limit to {self.config.message_storage_limit_mb} MB",
                        RNS.LOG_INFO,
                    )

                RNS.log(
                    f"Enabled propagation node mode on {RNS.prettyhexrep(self.local.hash) if self.local else 'unknown'}",
                    RNS.LOG_INFO,
                )
            except Exception as e:
                RNS.log(
                    f"Failed to enable propagation node: {e}",
                    RNS.LOG_ERROR,
                )

        if self.router and self.config.propagation_node:
            try:
                propagation_node_bytes = bytes.fromhex(self.config.propagation_node)
                self.router.set_outbound_propagation_node(propagation_node_bytes)
                RNS.log(
                    f"Configured outbound propagation node: {RNS.prettyhexrep(propagation_node_bytes)}",
                    RNS.LOG_INFO,
                )
            except ValueError:
                RNS.log(
                    f"Invalid propagation node hash format: {self.config.propagation_node}",
                    RNS.LOG_ERROR,
                )
        elif self.router and self.config.autopeer_propagation:
            RNS.log(
                f"Auto-peering enabled for propagation nodes within {self.config.autopeer_maxdepth} hops",
                RNS.LOG_INFO,
            )
        elif (
            self.config.propagation_fallback_enabled
            and not self.config.enable_propagation_node
        ):
            RNS.log(
                "Propagation fallback is enabled but no propagation_node configured and autopeer_propagation is disabled. "
                "Propagated delivery will fail. Set propagation_node, enable autopeer_propagation, or disable propagation_fallback_enabled.",
                RNS.LOG_WARNING,
            )

        if self.local:
            RNS.log(
                f"LXMF Router ready to receive on: {RNS.prettyhexrep(self.local.hash)}",
                RNS.LOG_INFO,
            )
        else:
            # Test mode - create mock components
            if os.path.isfile(identity_file):
                self.identity = RNS.Identity.from_file(identity_file)
            else:
                self.identity = RNS.Identity()  # Create a basic identity for testing
                if self.config.config_path:
                    self.identity.to_file(identity_file)

            self.router = None
            self.local = None

        self.announce_enabled = self.config.announce_enabled
        self.announce_time = self.config.announce

        if self.announce_enabled and not self.config.test_mode:
            # Schedule the announce task
            self.scheduler.add_task(
                "announce_task",
                self.announce_now,
                f"*/{self.announce_time // 60} * * * *",  # Convert seconds to minutes for cron
            )
            if self.config.announce_immediately:
                self.announce_now(force=True)
                RNS.log("Initial announce sent", RNS.LOG_INFO)

        self.admins = set(self.config.admins or [])
        self.hot_reloading = self.config.hot_reloading
        self.command_prefix = self.config.command_prefix

        self.help_system = HelpSystem(self)

        self.nlp = IntentClassifier(threshold=self.config.nlp_threshold)
        self.intents = {}  # {intent_name: callback}

        self.link_handlers = []
        self.links = {}  # {dest_hash: Link}

        self.signature_manager = SignatureManager(
            self,
            verification_enabled=self.config.signature_verification_enabled,
            require_signatures=self.config.require_message_signatures,
            request_unknown_identities=self.config.request_unknown_identities,
        )

        self._load_delivery_attempts()
        self._load_persisted_queue()

        if self.config.cogs_enabled:
            load_cogs_from_directory(self)

    @property
    def name(self) -> str:
        """Bot display name used for LXMF when no file override applies."""
        return self.config.name

    @name.setter
    def name(self, value: str) -> None:
        self.config.name = value
        self._sync_delivery_display_name()

    def _effective_announce_display_name(self) -> str:
        """Resolve the display name for lxmf/delivery announce app_data."""
        if self.config.announce_display_name_file:
            path = os.path.join(
                self.config_path,
                self.config.announce_display_name_file,
            )
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read().strip()
                    if text:
                        return text
                except OSError:
                    pass

        default_path = os.path.join(self.config_path, BOT_DISPLAY_NAME_FILE)
        if os.path.isfile(default_path):
            try:
                with open(default_path, encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    return text
            except OSError:
                pass

        return self.config.name if self.config.name else "LXMFBot"

    def _sync_delivery_display_name(self) -> None:
        if not self.local:
            return
        self.local.display_name = self._effective_announce_display_name()

    def command(self, *args, **kwargs):
        """Decorator for registering commands.

        Args:
            *args: Command name (optional).
            **kwargs: Command attributes (name, description, admin_only).

        """

        def decorator(func):
            """The actual decorator that registers the command."""
            name = args[0] if len(args) > 0 else kwargs.get("name", func.__name__)

            description = kwargs.get("description", "No description provided")
            admin_only = kwargs.get("admin_only", False)

            cmd = Command(name=name, description=description, admin_only=admin_only)
            cmd.callback = func
            self.commands[name] = cmd
            return func

        return decorator

    def load_extension(self, name: str) -> None:
        """Load an extension (cog) by name.

        Args:
            name: The name of the extension to load.

        Raises:
            ValueError: If the module name contains invalid characters.
            ImportError: If the extension is missing setup function or fails to load.

        """
        if not re.match(r"^[a-zA-Z0-9_\.]+$", name):
            raise ValueError(f"Invalid module name format: {name}")

        if not name.startswith("cogs."):
            name = f"cogs.{name}"

        try:
            if self.hot_reloading and name in sys.modules:
                module = importlib.reload(sys.modules[name])
            else:
                module = importlib.import_module(name)

            if not hasattr(module, "setup"):
                raise ImportError(f"Extension {name} missing setup function")
            module.setup(self)
        except ImportError as e:
            raise ImportError(f"Failed to load extension {name}: {e!s}") from e

    def add_cog(self, cog):
        """Add a cog to the bot.

        Args:
            cog: The cog instance to add.

        """
        self.cogs[cog.__class__.__name__] = cog
        for _name, method in inspect.getmembers(
            cog,
            predicate=lambda x: hasattr(x, "command"),
        ):
            if _name.startswith("_") or _name == "bot":
                continue

            try:
                cmd_descriptor = method.command

                if hasattr(cmd_descriptor, "__get__") and hasattr(
                    cmd_descriptor,
                    "name",
                ):
                    cmd = cmd_descriptor.__get__(cog, cog.__class__)
                elif hasattr(cmd_descriptor, "name"):
                    cmd = cmd_descriptor
                    if cmd.callback is None:
                        cmd.callback = method
                else:
                    self.logger.warning(
                        "Unexpected command type for %s: %s",
                        _name,
                        type(cmd_descriptor),
                    )
                    continue

                self.commands[cmd.name] = cmd
            except Exception as e:
                self.logger.error(
                    "Error adding command %s from cog %s: %s",
                    _name,
                    cog.__class__.__name__,
                    e,
                )
                continue

    def remove_cog(self, cog_name: str) -> None:
        """Remove a cog from the bot by its class name.

        Args:
            cog_name: The name of the cog class to remove.

        """
        if cog_name in self.cogs:
            cog = self.cogs.pop(cog_name)
            # Remove associated commands
            commands_to_remove = [
                name
                for name, cmd in self.commands.items()
                if hasattr(cmd, "callback")
                and (
                    getattr(cmd.callback, "__self__", None) == cog
                    or (
                        hasattr(cmd.callback, "__func__")
                        and getattr(cmd.callback, "__self__", None) == cog
                    )
                )
            ]
            for name in commands_to_remove:
                del self.commands[name]

    def reload_extension(self, name: str) -> None:
        """Reload an extension (cog) by name."""
        if not name.startswith("cogs."):
            ext_name = f"cogs.{name}"
        else:
            ext_name = name

        # Find the cog associated with this extension to remove it first
        for cname, cog in list(self.cogs.items()):
            if cog.__module__ == ext_name:
                self.remove_cog(cname)
                break

        self.load_extension(name)

    def is_admin(self, sender):
        """Check if a sender is an admin.

        Args:
            sender: The sender's identity hash.

        Returns:
            True if the sender is an admin, False otherwise.

        """
        return sender in self.admins

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
                    self.send(sender, msg)
                    return

            self._reset_delivery_attempts(sender)

    def _process_message(self, message, sender):
        """Process an incoming message."""
        try:
            content = message.content.decode("utf-8")
            receipt = RNS.hexrep(message.hash, delimit=False)

            def reply(response, **kwargs):
                """Helper function to reply to a message."""
                self.send(sender, response, **kwargs)

            if self.config.first_message_enabled:
                first_messages = self.storage.get("first_messages", {})
                if sender not in first_messages:
                    first_messages[sender] = True
                    self.storage.set("first_messages", first_messages)
                    handled = False
                    for handler in self.first_message_handlers:
                        if handler(sender, message):
                            handled = True
                            break
                    if handled:
                        return

            if not self.permissions.has_permission(sender, DefaultPerms.USE_BOT):
                return

            # Call message handlers
            for handler in self.message_handlers:
                if handler(sender, message):
                    return

            msg_ctx = {
                "lxmf": message,
                "reply": reply,
                "sender": sender,
                "content": content,
                "hash": receipt,
            }
            msg = SimpleNamespace(**msg_ctx)

            ctx = MiddlewareContext(MiddlewareType.PRE_COMMAND, msg)
            if self.middleware.execute(MiddlewareType.PRE_COMMAND, ctx) is None:
                return

            if self.command_prefix is None or content.startswith(self.command_prefix):
                command_name = (
                    content.split()[0][len(self.command_prefix) :]
                    if self.command_prefix
                    else content.split()[0]
                )
                if command_name in self.commands:
                    cmd = self.commands[command_name]

                    if not self.permissions.has_permission(sender, cmd.permissions):
                        self.send(
                            sender,
                            "You don't have permission to use this command.",
                        )
                        return

                    try:
                        args = content.split()[1:] if len(content.split()) > 1 else []

                        sig = inspect.signature(cmd.callback)
                        params = list(sig.parameters.values())

                        converted_args = []
                        for i, arg_val in enumerate(args):
                            param_idx = i + 1
                            if param_idx < len(params):
                                param = params[param_idx]
                                annotation = param.annotation
                                if (
                                    annotation != inspect.Parameter.empty
                                    and hasattr(annotation, "__call__")
                                    and not isinstance(annotation, str)
                                ):
                                    try:
                                        converted_args.append(annotation(arg_val))
                                    except (ValueError, TypeError):
                                        converted_args.append(arg_val)
                                else:
                                    converted_args.append(arg_val)
                            else:
                                converted_args.append(arg_val)

                        msg.args = converted_args
                        msg.is_admin = sender in self.admins

                        if cmd.threaded:
                            self.thread_pool.submit(cmd.callback, msg)
                        else:
                            cmd.callback(msg)

                        self.middleware.execute(MiddlewareType.POST_COMMAND, msg)
                        return

                    except Exception as e:
                        self.logger.error(
                            "Error executing command %s: %s",
                            command_name,
                            str(e),
                        )
                        self.send(sender, "Error executing command: %s", str(e))
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
                        self.intents[intent_name](msg)
                        return
                    except Exception as e:
                        self.logger.error(
                            "Error executing intent %s: %s",
                            intent_name,
                            e,
                        )

            for callback in self.delivery_callbacks:
                callback(msg)

        except Exception as e:
            self.logger.error("Error processing message: %s", str(e))

    def _message_received(self, message):
        """Handle received messages."""
        try:
            sender = RNS.hexrep(message.source_hash, delimit=False)
            receipt = RNS.hexrep(message.hash, delimit=False)

            if receipt in self.receipts:
                return

            self.receipts.append(receipt)
            if len(self.receipts) > 100:
                self.receipts = self.receipts[-100:]

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

        except Exception as e:
            self.logger.error("Error handling received message: %s", str(e))

    def announce_now(self, force: bool = False) -> None:
        """Send an LXMF delivery announce using the current display name.

        LXMF builds delivery announce app_data from the destination display name
        at announce time; this method refreshes that from :attr:`name`, optional
        ``announce_display_name_file``, or ``bot_display_name.txt`` before
        sending.

        Args:
            force: If True, send now and skip the on-disk announce interval
                throttle (still respects ``announce_enabled`` and requires a
                running router). If False, behave like the periodic announce
                task (honours ``announce_time`` and the throttle file).

        """
        if self.config.test_mode or not self.local:
            RNS.log("Announce skipped (test mode or no router)", RNS.LOG_DEBUG)
            return
        if not self.announce_enabled:
            RNS.log("Announcements disabled", RNS.LOG_DEBUG)
            return
        if not force and self.announce_time == 0:
            RNS.log("Announcements disabled", RNS.LOG_DEBUG)
            return

        announce_path = os.path.join(self.config_path, "announce")
        if not force:
            if os.path.isfile(announce_path):
                with open(announce_path) as f:
                    try:
                        announce = int(f.readline())
                    except ValueError:
                        announce = 0
            else:
                announce = 0

            if announce > int(time.time()):
                RNS.log("Recent announcement", RNS.LOG_DEBUG)
                return

        with open(announce_path, "w+") as af:
            interval = self.announce_time if self.announce_time > 0 else 0
            next_announce = int(time.time()) + interval
            af.write(str(next_announce))

        self._sync_delivery_display_name()
        self.local.announce()
        RNS.log(
            f"Announcement sent, next announce in {self.announce_time} seconds",
            RNS.LOG_INFO,
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

    def send(
        self,
        destination: str,
        message: str,
        title: str = "Reply",
        lxmf_fields: dict | None = None,
        stamp_cost: int | None = None,
        opportunistic: bool | None = None,
    ):
        """Send a message to a destination, optionally with custom LXMF fields.

        Args:
            destination: The destination hash.
            message: The message content (will be utf-8 encoded).
            title: The message title (optional, will be utf-8 encoded).
            lxmf_fields: Optional dictionary of LXMF fields.
            stamp_cost: Optional stamp cost override. If None, uses config.stamp_cost.
            opportunistic: Whether to use opportunistic sending (try direct, then prop).
                           If None, uses config.opportunistic_sending.

        """
        if self.config.test_mode:
            # In test mode, just queue a mock message
            mock_message = SimpleNamespace()
            mock_message.content = message.encode("utf-8")
            mock_message.title = title.encode("utf-8") if title else None
            mock_message.fields = lxmf_fields
            self.queue.put(mock_message)
            return

        try:
            dest_hash_bytes = bytes.fromhex(destination)
        except ValueError:
            RNS.log(f"Invalid destination hash format: {destination}", RNS.LOG_ERROR)
            return

        if len(dest_hash_bytes) != RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
            RNS.log(f"Invalid destination hash length for {destination}", RNS.LOG_ERROR)
            return

        identity_instance = RNS.Identity.recall(dest_hash_bytes)
        if identity_instance is None:
            RNS.log(
                f"Could not recall an Identity for {destination}. Requesting path...",
                RNS.LOG_ERROR,
            )
            RNS.Transport.request_path(dest_hash_bytes)
            RNS.log(
                "Path requested. If the network knows a path, you will receive an announce shortly.",
                RNS.LOG_INFO,
            )
            return

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
        else:
            desired_method = LXMessage.DIRECT

        # Use provided stamp_cost or fall back to config
        final_stamp_cost = (
            stamp_cost if stamp_cost is not None else self.config.stamp_cost
        )

        lxm = LXMessage(
            lxmf_destination_obj,
            self.local,
            message_bytes,
            title=title_bytes,
            desired_method=desired_method,
            fields=lxmf_fields,
            stamp_cost=final_stamp_cost,
        )

        # Register callbacks to reset counter on success or track failure
        def on_delivery_success(_message):
            if destination in self.delivery_attempts:
                self.delivery_attempts[destination] = 0
                self._save_delivery_attempts()
                RNS.log(
                    f"Delivery successful to {destination}, reset retry counter",
                    RNS.LOG_DEBUG,
                )

        def on_delivery_failure(_message):
            current_attempts = self.delivery_attempts.get(destination, 0)
            self.delivery_attempts[destination] = current_attempts + 1
            self._save_delivery_attempts()

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

        # Set propagation fallback if enabled
        if (
            desired_method == LXMessage.DIRECT
            and (self.config.propagation_fallback_enabled or is_opportunistic)
            and has_prop_node
        ):
            lxm.try_propagation_on_fail = True

        self.queue.put(lxm)
        self._persist_queue()
        RNS.log(
            f"Message queued for {destination} (method: {desired_method}, opportunistic: {is_opportunistic})",
            RNS.LOG_DEBUG,
        )

    def _persist_queue(self):
        """Persist the outgoing message queue to storage."""
        if getattr(self.config, "message_persistence_enabled", False) is not True:
            return

        # Persist destination/content/title/fields/method; LXMessage is not trivially serializable.

        queued_messages = []
        for lxm in list(self.queue.queue):
            try:
                msg_data = {
                    "destination": RNS.hexrep(lxm.destination_hash, delimit=False),
                    "content": lxm.content.decode("utf-8")
                    if isinstance(lxm.content, bytes)
                    else lxm.content,
                    "title": lxm.title.decode("utf-8")
                    if isinstance(lxm.title, bytes)
                    else lxm.title,
                    "fields": lxm.fields,
                    "method": lxm.desired_method,
                }
                queued_messages.append(msg_data)
            except Exception as e:
                self.logger.error("Failed to serialize message for persistence: %s", e)

        self.storage.set("persisted_queue", queued_messages)

    def _load_persisted_queue(self):
        """Load persisted messages back into the queue."""
        if getattr(self.config, "message_persistence_enabled", False) is not True:
            return

        persisted = self.storage.get("persisted_queue", [])
        if not persisted:
            return

        RNS.log(f"Restoring {len(persisted)} messages from persistence", RNS.LOG_INFO)
        for msg_data in persisted:
            try:
                self.send(
                    msg_data["destination"],
                    msg_data["content"],
                    title=msg_data.get("title"),
                    lxmf_fields=msg_data.get("fields"),
                )
            except Exception as e:
                self.logger.error("Failed to restore message from persistence: %s", e)

        # Clear after loading to avoid duplicates if send() fails again
        self.storage.set("persisted_queue", [])

    def send_with_attachment(
        self,
        destination: str,
        message: str,
        attachment: Attachment,
        title: str = "Reply",
        stamp_cost: int | None = None,
        opportunistic: bool | None = None,
    ):
        """Send a message with an attachment to a destination.

        Args:
            destination: The destination hash.
            message: The message content.
            attachment: The attachment to send.
            title: The message title.
            stamp_cost: Optional stamp cost override.
            opportunistic: Whether to use opportunistic sending.

        """
        attachment_specific_fields = pack_attachment(attachment)
        self.send(
            destination,
            message,
            title=title,
            lxmf_fields=attachment_specific_fields,
            stamp_cost=stamp_cost,
            opportunistic=opportunistic,
        )

    def run(self, delay=10):
        """Run the bot"""
        self.scheduler.start()  # Start the scheduler
        try:
            while True:
                # Process outgoing queue with a timeout to prevent hanging
                while not self.queue.empty():
                    try:
                        # Non-blocking get with a small timeout for safety
                        lxm = self.queue.get(block=False)
                        if self.router:
                            self.router.handle_outbound(lxm)
                    except Exception:
                        break

                time.sleep(delay)

        except KeyboardInterrupt:
            self.cleanup()  # Call cleanup on KeyboardInterrupt

    def received(self, function):
        """Decorator for registering delivery callbacks.

        Args:
            function: The function to call when a message is delivered.

        """
        self.delivery_callbacks.append(function)
        return function

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
        except Exception as e:
            self.logger.error("Error requesting page: %s", str(e))
            raise

    def cleanup(self):
        """Clean up resources."""
        RNS.log("Cleaning up LXMFBot...", RNS.LOG_DEBUG)
        self.transport.cleanup()
        self.thread_pool.shutdown(wait=False)
        self.scheduler.stop()
        if hasattr(self, "router") and self.router:
            try:
                self.router.exit_handler()
            except Exception:  # noqa: S110
                pass

        # Ensure Reticulum exits cleanly
        if not self.config.test_mode:
            try:
                RNS.Reticulum.exit_handler()
            except Exception:  # noqa: S110
                pass
        RNS.log("LXMFBot cleanup complete", RNS.LOG_DEBUG)

    def get_propagation_node_status(self):
        """Get information about configured and discovered propagation nodes.

        Returns:
            dict: Dictionary with propagation node configuration and status.

        """
        if self.config.test_mode:
            return {
                "test_mode": True,
                "error": "Not available in test mode",
            }

        status = {
            "manual_node": self.config.propagation_node,
            "autopeer_enabled": self.config.autopeer_propagation,
            "autopeer_maxdepth": self.config.autopeer_maxdepth,
            "is_propagation_node": self.config.enable_propagation_node,
            "current_outbound_node": None,
            "discovered_peers": [],
        }

        current_node = self.router.get_outbound_propagation_node()
        if current_node:
            status["current_outbound_node"] = RNS.hexrep(current_node, delimit=False)

        if hasattr(self.router, "peers") and self.router.peers:
            status["discovered_peers"] = [
                {
                    "hash": RNS.hexrep(peer_hash, delimit=False),
                    "hops": RNS.Transport.hops_to(peer_hash),
                }
                for peer_hash in self.router.peers.keys()
            ]

        return status

    def set_propagation_node(self, node_hash: str):
        """Manually set the outbound propagation node.

        Args:
            node_hash: The destination hash of the propagation node.

        """
        if self.config.test_mode:
            RNS.log("Cannot set propagation node in test mode", RNS.LOG_WARNING)
            return

        try:
            propagation_node_bytes = bytes.fromhex(node_hash)
            self.router.set_outbound_propagation_node(propagation_node_bytes)
            self.config.propagation_node = node_hash
            RNS.log(
                f"Set outbound propagation node to: {RNS.prettyhexrep(propagation_node_bytes)}",
                RNS.LOG_INFO,
            )
        except ValueError:
            RNS.log(
                f"Invalid propagation node hash format: {node_hash}",
                RNS.LOG_ERROR,
            )
            raise

    def set_message_storage_limit(self, megabytes: float):
        """Set the message storage limit for propagation node mode.

        Args:
            megabytes: Storage limit in megabytes. Set to 0 for unlimited.

        """
        if self.config.test_mode:
            RNS.log("Cannot set storage limit in test mode", RNS.LOG_WARNING)
            return

        if not self.config.enable_propagation_node:
            RNS.log(
                "Storage limit only applies when running as a propagation node",
                RNS.LOG_WARNING,
            )
            return

        try:
            if megabytes <= 0:
                self.router.set_message_storage_limit()
                self.config.message_storage_limit_mb = 0
                RNS.log("Removed message storage limit (unlimited)", RNS.LOG_INFO)
            else:
                self.router.set_message_storage_limit(megabytes=megabytes)
                self.config.message_storage_limit_mb = megabytes
                RNS.log(
                    f"Set message storage limit to {megabytes} MB",
                    RNS.LOG_INFO,
                )
        except Exception as e:
            RNS.log(
                f"Failed to set message storage limit: {e}",
                RNS.LOG_ERROR,
            )
            raise

    def get_propagation_storage_stats(self):
        """Get storage statistics for propagation node mode.

        Returns:
            dict: Dictionary with storage statistics or None if not a propagation node.

        """
        if self.config.test_mode:
            return {"test_mode": True, "error": "Not available in test mode"}

        if not self.config.enable_propagation_node:
            return {
                "is_propagation_node": False,
                "error": "Not running as propagation node",
            }

        try:
            storage_size = self.router.message_storage_size()
            storage_limit = self.router.message_storage_limit

            stats = {
                "is_propagation_node": True,
                "storage_size_bytes": storage_size,
                "storage_size_mb": storage_size / (1000 * 1000) if storage_size else 0,
                "storage_limit_bytes": storage_limit,
                "storage_limit_mb": storage_limit / (1000 * 1000)
                if storage_limit
                else None,
                "utilization_percent": (storage_size / storage_limit * 100)
                if (storage_limit and storage_size)
                else 0,
                "message_count": len(self.router.propagation_entries)
                if hasattr(self.router, "propagation_entries")
                else 0,
            }

            return stats
        except Exception as e:
            return {"error": f"Failed to get stats: {e}"}  # Stop the scheduler

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

    def request_link(
        self,
        destination_hash: str,
        callback: Callable = None,
        app_name: str = "lxmf",
        *aspects: str,
    ):
        """Request an RNS link to a destination.

        Args:
            destination_hash: The destination hash string.
            callback: Optional callback when link is established.
            app_name: The app name for the destination (default: "lxmf").
            *aspects: Additional aspects for the destination (default: "delivery" if none provided).

        """
        if not self.config.link_support_enabled:
            raise Exception("Link support is disabled in config")

        if not aspects:
            aspects = ("delivery",)

        dest_bytes = bytes.fromhex(destination_hash)
        identity = RNS.Identity.recall(dest_bytes)
        if not identity:
            RNS.Transport.request_path(dest_bytes)
            raise Exception(
                f"Identity for {destination_hash} not known, requesting path",
            )

        dest = RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            app_name,
            *aspects,
        )
        link = RNS.Link(dest)

        if callback:

            def _link_established(link):
                callback(link)

            link.set_link_established_callback(_link_established)

        self.links[destination_hash] = link
        return link

    def on_link(self, callback: Callable):
        """Register a handler for incoming links."""
        self.link_handlers.append(callback)

    def _link_established(self, link):
        """Handle an established RNS link."""
        sender = RNS.hexrep(link.destination.hash, delimit=False)
        self.links[sender] = link
        for handler in self.link_handlers:
            try:
                handler(link)
            except Exception as e:
                self.logger.error("Error in link handler: %s", e)

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

    def validate(self) -> str:
        """Run validation checks and return formatted results."""
        results = validate_bot(self)
        return format_validation_results(results)
