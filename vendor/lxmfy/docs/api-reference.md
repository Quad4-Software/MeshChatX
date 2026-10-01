# Core Components

## LXMFBot

The main bot class that handles message routing, command processing, and
bot lifecycle management.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="MyBot",
    command_prefix="/",
    admins=set(),
    config_path=None,                 # default "config" in the working directory
    reticulum_config_dir=None,        # or LXMFY_RETICULUM_CONFIG_DIR / "~/.reticulum"
    test_mode=False,                  # skip RNS startup, for tests
    log_level="INFO",                 # lxmfy logger level, None leaves logging alone
    loglevel=None,                    # RNS log level 0-7, None uses reticulum config

    # Announces
    announce=600,
    announce_immediately=True,
    announce_enabled=True,
    announce_display_name_file=None,  # filename under config_path overriding the
                                      # announced display name (default file:
                                      # bot_display_name.txt)

    # Spam protection
    rate_limit=5,
    cooldown=60,
    max_warnings=3,
    warning_timeout=300,

    # Cogs
    cogs_dir="cogs",
    cogs_enabled=True,
    dynamic_cogs_enabled=True,
    external_cogs_enabled=True,
    external_cogs_sandbox_enabled=True,
    external_cogs_sandbox_type="auto",  # "auto", "landlock", "bwrap", "firejail", "none"
    external_cogs_timeout=30,
    hot_reloading=False,

    # Storage, events, permissions
    storage_type="json",              # "json", "sqlite", "msgpack", or "memory"
    storage_path="data",
    permissions_enabled=False,
    first_message_enabled=True,
    event_logging_enabled=True,
    max_logged_events=1000,
    event_middleware_enabled=True,

    # Security
    signature_verification_enabled=False,
    require_message_signatures=False,
    require_stamps=False,             # reject messages with invalid stamps
    request_unknown_identities=False, # request sender identities from the network
    stamp_cost=None,                  # inbound stamp cost, None disables
    include_tickets=True,             # attach reply tickets to outbound messages
    identity_pinning_enabled=False,
    landlock_enabled=True,

    # Optional features
    nlp_enabled=False,
    nlp_threshold=0.5,
    link_support_enabled=False,
    lxmf_commands_enabled=True,

    # Delivery
    message_persistence_enabled=True,
    message_queue_size=50,
    opportunistic_sending=True,
    direct_delivery_retries=3,
    propagation_fallback_enabled=True,
    propagation_node=None,            # outbound propagation node hash
    autopeer_propagation=False,       # discover propagation nodes from announces
    autopeer_maxdepth=4,              # max hop depth for autopeering, None = no limit
    enable_propagation_node=False,    # run this bot as a propagation node
    message_storage_limit_mb=500,     # node storage cap, node mode only

    # Deferred sends
    pending_sends_enabled=True,       # hold sends for unknown destinations
    pending_sends_max=200,
    pending_sends_ttl=604800,         # 7 days
    pending_sends_retry=300,          # seconds between retry sweeps

    # RRC
    rrc_enabled=False,
    rrc_hubs=[],
    rrc_rooms=[],
    rrc_nick=None,
    rrc_dest_name="rrc.hub",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)
```

All of these are fields on `BotConfig`. `LXMFBot(**kwargs)` forwards every
keyword argument to it, so `bot.config` holds the resolved values.

### Key Methods

- `run(delay=10)`: Start the bot's main loop
- `cleanup()`: Persist queues, cancel conversations, shut down the
  scheduler, router, and RNS. Called automatically when `run()` exits.
- `send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None, method=None, include_ticket=None, defer=None, reply_to=None, quote=None, thread=None)`:
  Send a message to a destination. `stamp_cost` overrides the outbound
  cost for this message, `opportunistic` overrides
  `opportunistic_sending`, `include_ticket` overrides
  `include_tickets`, and `defer` overrides `pending_sends_enabled`.
  `reply_to`, `quote`, and `thread` set the reply threading fields.
- `send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`:
  Send a message with an attachment
- `command(name, description="No description provided", admin_only=False, permissions=None, usage=None, examples=None, category=None, aliases=None, threaded=False, rate_limit=None)`:
  Decorator for registering commands. `permissions` overrides the
  `DefaultPerms` gate (`ALL` when `admin_only`, else `USE_COMMANDS`),
  `threaded` runs the callback in a worker thread, `rate_limit` caps
  invocations per sender per cooldown window, and `usage`, `examples`,
  `category`, `aliases` feed the help system. Commands support
  type-hinted arguments for automatic conversion.
- `intent(name, examples)`: Decorator for registering NLP intent
  handlers.
- `nlp.export_model()`: Export trained NLP model data.
- `nlp.import_model(model_data)`: Import previously exported NLP model
  data.
- `request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`:
  Request an RNS link to a destination. Allows custom `app_name` and
  `aspects` (defaults to "lxmf" and "delivery").
- `on_link(callback)`: Register a handler for incoming RNS links.
- `load_extension(name)`: Load a cog extension module by name (e.g.,
  "cogs.utility").
- `reload_extension(name)`: Reload a cog extension module.
- `add_cog(cog_instance)`: Add a cog class instance to the bot.
- `remove_cog(cog_name)`: Remove a cog from the bot by its class name.
- `on_first_message()`: Decorator for handling first messages from users
- `on_message()`: Decorator for handling all messages (called before
  command processing)
- `received(function)`: Register a callback invoked with the message
  context for every inbound message that made it through the pipeline
  without being consumed by a command or intent
- `on_reaction()`: Decorator for handling inbound reactions. Handlers
  receive `(sender, reaction)` where reaction carries `reaction_to`,
  `reaction_emoji`, and `reaction_sender` keys
- `react(destination, message_hash, reaction)`: Send a reaction to a
  message via the LXMF `FIELD_REACTION` field
- `validate()`: Run validation checks on the bot configuration
- `get_landlock_status()`: Return Landlock LSM sandbox availability and
  activation state for the bot process
- `diagnose_destination(destination, request_path=False, wait=0.0)`:
  Probe identity and path state for a destination hash
- `diagnose_connectivity(destination=None, request_path=False, wait=0.0)`:
  Run the full doctor report and return it as a dict
- `get_debugger()`: Return a `Debugger` bound to this bot
- `set_propagation_node(node_hash)`: Pin the outbound propagation node
- `get_propagation_node_status()`: Configured, discovered, and current
  outbound propagation node state
- `set_message_storage_limit(megabytes)`: Storage cap when running as a
  propagation node
- `get_propagation_storage_stats()`: Node storage usage, or a dict
  explaining why it is unavailable
- `connect_rrc(hub_hash, rooms=None, nick=None, dest_name=None, auto_reconnect=None)`:
  Connect to an RRC hub as a client
- `disconnect_rrc(hub_hash=None)`: Disconnect one or all RRC hub
  sessions
- `on_rrc(callback=None)`: Decorator or register handler for RRC events
  (`handler(event, client, payload)`)
- `on_delivery_event(callback=None)`: Subscribe to the outbound
  delivery event stream, decorator or direct call

### Attributes

- `config`: The resolved `BotConfig`
- `commands`, `cogs`: Registered command and cog registries
- `storage`: The active storage backend
- `scheduler`: `TaskScheduler` for cron-style tasks
- `events`: `EventManager` for event handlers and dispatch
- `middleware`: `MiddlewareManager` for command middleware
- `permissions`: `PermissionManager` for roles and flags
- `spam_protection`: `SpamProtection` for rate limits, warnings, bans
- `signature_manager`: Signature policy layer
- `nlp`: The intent classifier (matches only when `nlp_enabled`)
- `delivery`: `DeliveryTracker`, the outbound event stream
- `conversations`: `ConversationManager` for `msg.ask` questions
- `rrc`: `RRCManager` for multi-hub sessions, `None` until RRC is
  enabled or `connect_rrc()` runs
- `local`: The bot's `RNS.Destination` (its LXMF address is
  `bot.local.hash`)

## Announce Display Name

The name peers see comes from `name`, but two overrides exist for
announces. If `announce_display_name_file` is set and that file exists
under `config_path`, its contents win. Otherwise
`bot_display_name.txt` under `config_path` is read when present.
Either way, assigning `bot.name = "New Name"` re-syncs the announced
display name at runtime.

This lets operators rename a bot without editing code, and lets the
announced name differ from the internal config name.

## Structured Commands via LXMF Fields

Bots can receive commands sent via LXMF `FIELD_COMMANDS` (`0x09`) and
automatically reply with `FIELD_RESULTS` (`0x0A`). This enables
structured request/response workflows alongside normal text commands.

Incoming `FIELD_COMMANDS` are parsed and routed through the same command
registry as text commands, sharing permission checks, type-hinted
argument parsing, threading, and middleware.

``` python
from lxmfy import LXMFBot, FIELD_COMMANDS, FIELD_RESULTS, pack_result, unpack_commands

bot = LXMFBot(name="FieldBot")

@bot.command(name="status", description="Return bot status")
def status_cmd(ctx):
    # ctx.fields contains the raw LXMF fields dict
    # ctx.request_id is set automatically if the command included one
    ctx.reply("Bot is online")

# Sending a structured command from another LXMF client:
# lxm.fields[FIELD_COMMANDS] = {"command": "status", "args": [], "request_id": "abc123"}
# router.handle_outbound(lxm)

# The bot reply automatically includes FIELD_RESULTS with the response and request_id.
```

To disable field command processing, set `lxmf_commands_enabled=False`
in `BotConfig`.

## Reactions

Reactions travel as the LXMF `FIELD_REACTION` (`0x40`) field on an
otherwise empty message. `pack_reaction` and `unpack_reaction` build
and parse that field.

``` python
from lxmfy import pack_reaction, unpack_reaction

# Send a reaction to a message
bot.react(destination_hash, message_hash_hex, "thumbs up emoji")

# Receive reactions
@bot.on_reaction()
def on_reaction(sender, reaction):
    # reaction["reaction_to"]  - hex hash of the target message
    # reaction["reaction_emoji"] - reaction text (up to 16 chars)
    # reaction["reaction_sender"] - sender
    print(f"{sender} reacted {reaction['reaction_emoji']} to {reaction['reaction_to']}")
    return True
```

Reaction text is capped at 16 printable characters. The raw field stays
available in `ctx.fields` and `msg.fields` for compatibility.

## Reply Threading

Replies can carry the LXMF `FIELD_REPLY_TO` (`0x30`), `FIELD_REPLY_QUOTE`
(`0x31`), and `FIELD_THREAD` (`0x08`) fields. Clients that render
threads, like MeshChatX and Sideband, show these as proper quote
replies instead of flat messages.

`msg.reply()` threads automatically: it sets `FIELD_REPLY_TO` to the
inbound message hash and `FIELD_THREAD` to the conversation root.

``` python
@bot.command("status")
def status(msg):
    msg.reply("all systems nominal")          # threaded reply
    msg.reply("flat", reply_to=None)          # opt out of threading
    msg.reply("noted", quote=True)            # quote the inbound text
```

For sends that are not replies, pass the fields explicitly:

``` python
bot.send(dest, "see above", reply_to=msg_hash_hex, quote="earlier text")
```

Inbound replies are parsed onto the message context:

``` python
@bot.command("ctx")
def ctx_cmd(msg):
    msg.reply_to      # hex hash this message replies to, or None
    msg.reply_quote   # quoted text carried by the reply, or None
    msg.thread        # hex thread root hash, or None
```

`pack_reply(message_hash, quote=..., thread=...)` and
`unpack_reply(fields)` are exported for manual field handling.

## Conversations

Commands can ask the sender a question and treat their next message as
the answer, instead of dispatching it as a command:

``` python
@bot.command("report")
def report(msg):
    title = msg.ask("Report title?", timeout=300)
    if title is None:
        msg.reply("Timed out.")
        return
    body = msg.ask("Describe the issue.", timeout=600)
    if body is None:
        msg.reply("Timed out.")
        return
    msg.reply(f"Filed: {title.content}")
```

`msg.ask(prompt, timeout=..., validator=...)` blocks the handler until
the answer arrives, the timeout fires, or the conversation is
cancelled. It returns an `Answer` with `content`, `fields`, `hash`,
`sender`, and a `reply(text)` shortcut.

A validator rejects bad answers and re-prompts:

``` python
num = msg.ask(
    "Pick a number",
    validator=lambda a: None if a.content.isdigit() else "Digits only",
)
```

In async command handlers use `await msg.ask_async(...)`. For long
waits, or when many conversations may be open, use the callback style so
no thread stays parked:

``` python
msg.ask(
    "Send the log file",
    on_answer=lambda ans: ans.reply("received"),
    on_timeout=lambda sender: bot.send(sender, "Too slow."),
    timeout=3600,
)
```

Notes:

- Sending a registered command while a question is pending cancels the
  question and runs the command. Users always have an escape hatch.
- `bot.conversations.pending_count()` and
  `bot.conversations.cancel(sender)` expose the registry for
  diagnostics and admin tools.
- The registry is capped at 1024 pending questions. `ask` returns `None`
  when it is full.
- Blocking `ask` parks the delivery thread handling that message. That
  is safe for direct deliveries, but bots that sync large batches from a
  propagation node should prefer `on_answer` callbacks.

## Storage

The framework provides three storage backends:

### JSONStorage

``` python
from lxmfy import JSONStorage

storage = JSONStorage("data")
```

### SQLiteStorage

``` python
from lxmfy import SQLiteStorage

storage = SQLiteStorage("data/bot.db")
```

### MsgPackStorage

``` python
from lxmfy.storage import MsgPackStorage

storage = MsgPackStorage("data") # {key}.msgpack files
```

### MemoryStorage

``` python
from lxmfy.storage import MemoryStorage

storage = MemoryStorage() # Entirely in-memory
```

## Commands

Command registration and handling:

``` python
@bot.command(name="hello", description="Says hello")
def hello(ctx):
    ctx.reply(f"Hello {ctx.sender}!")
```

Help metadata and access control come from extra decorator kwargs:

``` python
from lxmfy import DefaultPerms

@bot.command(
    name="purge",
    description="Clear stored data",
    permissions=DefaultPerms.MANAGE_MESSAGES,
    usage="/purge <key>",
    examples=["/purge cache"],
    category="Admin",
    aliases=["clear"],
)
def purge(ctx, key: str):
    bot.storage.delete(key)
    ctx.reply(f"Deleted {key}")
```

`permissions` overrides the default gate: `USE_COMMANDS` for normal
commands, `ALL` for `admin_only` ones. `category` groups the command in
`/help` output. `aliases` is help metadata only: alias names are shown
to users but are not registered for dispatch, so `/clear` will not run
`purge` unless you register it as a second command.

### Type-Hinted Arguments

Commands automatically parse and convert arguments based on type hints
in the callback function.

``` python
@bot.command(name="add", description="Adds two numbers")
def add(ctx, a: int, b: int):
    result = a + b
    ctx.reply(f"The result is {result}")
```

### Per-Command Rate Limits

Limit how often a single sender can invoke a command inside the global
`cooldown` window. Hitting the limit rejects the invocation only; it
never adds warnings or bans.

``` python
@bot.command(name="report", rate_limit=3)
def report(ctx):
    # each sender can call this 3 times per cooldown period
    ...
```

Requires `permissions_enabled=True`, like the global rate limit. Users
with the admin role or `BYPASS_SPAM` skip the check.

## Spam Protection

`bot.spam_protection` enforces the global rate limit: a sender may post
`rate_limit` messages inside each `cooldown` window. Exceeding the
limit adds a warning and rejects the message. At `max_warnings` the
sender is banned. Warnings decay after `warning_timeout` seconds of
good behavior.

Spam checks run inside the `message_received` event and require
`permissions_enabled=True`.

``` python
bot = LXMFBot(
    name="GuardedBot",
    permissions_enabled=True,
    rate_limit=5,        # messages per cooldown window
    cooldown=60,         # window length in seconds
    max_warnings=3,      # warnings before a ban
    warning_timeout=300, # seconds before the warning count resets
)

# Lift a ban manually
bot.spam_protection.unban(sender_hash)
```

Warnings, bans, and counters persist in the configured storage backend,
so bans survive restarts. Senders with the `BYPASS_SPAM` permission are
never rate limited or banned. Per-command `rate_limit` on `@bot.command`
is gentler: it rejects the invocation only and never warns or bans.

## Help System

The framework includes an interactive help generator that provides
beautiful, categorized help menus based on Cog and Command metadata.

``` python
# The help command is automatically registered.
# Users can use '/help' or '/help <command>'
```

## Threaded Commands

For long-running or blocking operations that do not interact with the
Reticulum Network Stack directly, you can run commands in a separate
thread to keep the bot responsive.

``` python
import time

@bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
def long_task_command(ctx):
    ctx.reply("Starting a long task... please wait.")
    time.sleep(10) # This runs in a separate thread
    ctx.reply("Long task completed!")
```

!!! warning "Thread safety"

    Functions marked as `threaded=True` **must not** directly interact
    with the Reticulum Network Stack (RNS) or any components that rely
    on `lxmfy.transport.py`, as these are generally not thread-safe.
    Use `ctx.reply()` for sending messages back to the user from within
    a threaded command.

## Events

Event system for handling various bot events:

``` python
@bot.events.on("message_received", EventPriority.HIGHEST)
def handle_message(event):
    # event.data carries the payload, e.g. sender and message
    event.cancel()  # stop later handlers and further processing
```

Handlers run in `EventPriority` order: `HIGHEST`, `HIGH`, `NORMAL`,
`LOW`. Spam checking itself is a `message_received` handler at
`HIGHEST`, so cancelling that event is how the rate limiter drops
messages.

Dispatch custom events of your own:

``` python
from lxmfy import Event

bot.events.dispatch(Event("order_placed", data={"user": ctx.sender}))
```

`event_logging_enabled`, `max_logged_events`, and
`event_middleware_enabled` exist on `BotConfig` but are not wired up:
events are not written to storage and `bot.events.use()` is a stub.
Treat them as reserved.

## Testing

`lxmfy.testing.TestBot` is an `LXMFBot` preconfigured for tests. No
Reticulum instance starts. Inbound messages go through the real receive
pipeline (middleware, spam checks, permissions, dispatch) and outbound
sends are captured for assertions.

``` python
from lxmfy import TestBot

def test_ping():
    with TestBot() as bot:
        @bot.command("ping")
        def ping(msg):
            msg.reply("pong")

        sent = bot.receive("/ping", sender="alice")
        assert sent[0].content == "pong"
        assert sent[0].destination == bot.sender_hex("alice")
```

- `bot.receive(content, sender=..., fields=..., message_hash=...)`
  injects a message and returns the `SentMessage` objects it produced.
  Senders are named: `"alice"` maps to a stable fake hash, or pass a hex
  destination hash directly.
- `bot.drain()` pops queued outbound messages. `bot.outbox` accumulates
  everything sent. `bot.last_sent(sender=...)` fetches the latest.
- `bot.wait_sent(n, timeout=...)` waits for threaded commands.
- `bot.receive_later(content, sender=..., delay=...)` answers blocking
  `msg.ask` calls from a daemon thread.
- `fake_message(content, source_hash=..., ...)` builds an inbound
  message for driving `bot._message_received` directly.

`SentMessage` wraps each captured outbound message: `destination` (hex),
`content`, `title`, `fields`, `method`, `include_ticket`,
`stamp_cost`, and `raw` for the underlying object.

The repository test suite also includes reliability and stress
scenarios. Use the repository's test runner to execute them.

### Advanced Reliability Suite

The framework includes an extensive suite of automated tests for harsh
environments:

- **Manifold Testing**: Validates the mathematical topology of NLP
  intent vector space.
- **Chaos Engineering**: Simulates bit-rot, SD card failure, and storage
  corruption.
- **Temporal Drift**: Verifies resilience against system clock jumps (±1
  year).
- **Leak Detection**: Long-term tracking of memory, file descriptors,
  and threads.

## Permissions

Permission system for controlling access to bot features:

``` python
from lxmfy import DefaultPerms

@bot.command(name="admin", description="Admin command", admin_only=True)
def admin_command(ctx):
    if ctx.is_admin:
        ctx.reply("Admin command executed")
```

Enable with `permissions_enabled=True`. `DefaultPerms` flags:

- `USE_BOT`, `SEND_MESSAGES`, `USE_COMMANDS`: basic access
- `MANAGE_MESSAGES`, `MANAGE_COMMANDS`, `MANAGE_USERS`: elevated
- `BYPASS_RATELIMIT`, `BYPASS_SPAM`, `VIEW_ADMIN_COMMANDS`: special
- `VIEW_EVENTS`, `MANAGE_EVENTS`, `BYPASS_EVENT_CHECKS`: event system
- `NONE`, `ALL`: shorthands

`bot.permissions` manages roles and assignments:

``` python
bot.permissions.create_role("moderator", DefaultPerms.MANAGE_MESSAGES | DefaultPerms.BYPASS_SPAM)
bot.permissions.assign_role(user_hash, "moderator")
bot.permissions.remove_role(user_hash, "moderator")
bot.permissions.has_permission(user_hash, DefaultPerms.USE_COMMANDS)
```

Roles and assignments persist in the configured storage backend. Two
built-in roles exist and cannot be deleted: `user` (the default) and
`admin`, which is granted automatically to every hash in `admins`.

## Middleware

Middleware system for processing messages and events:

``` python
from lxmfy import MiddlewareType

@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def pre_command_middleware(ctx):
    # ctx wraps the message context, ctx.cancelled drops it
    if "spamword" in ctx.data.content:
        ctx.cancel()
```

Three points in the pipeline run middleware:

- `PRE_COMMAND`: before command dispatch, after spam checks. Returning
  `None` from the chain aborts the message entirely.
- `POST_COMMAND`: after a command's callback finishes (including
  threaded commands, which fire it on the worker thread).
- `PRE_EVENT`: before the `message_received` event dispatch.

`POST_EVENT`, `REQUEST`, and `RESPONSE` exist in `MiddlewareType` but
nothing in the pipeline executes them yet.

## Attachments

Support for sending files, images, and audio:

``` python
from lxmfy import Attachment, AttachmentType

attachment = Attachment(
    type=AttachmentType.IMAGE,
    name="image.jpg",
    data=image_data,
    format="jpg"
)
bot.send_with_attachment(destination, "Here's an image", attachment)
```

## Icon Appearance (LXMF Field)

You can set a custom icon for your bot that compliant LXMF clients can
display. This uses the `LXMF.FIELD_ICON_APPEARANCE`.

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
import LXMF # Required for LXMF.FIELD_ICON_APPEARANCE

# Define the icon appearance
icon_data = IconAppearance(
    icon_name="smart_toy",  # Name from Material Symbols
    fg_color=b'\xFF\xFF\xFF',  # White foreground (3 bytes)
    bg_color=b'\x4A\x90\xE2'   # Blue background (3 bytes)
)

# Pack it into the LXMF field format
icon_lxmf_field = pack_icon_appearance_field(icon_data)

# Send a message with this icon
bot.send(
    destination_hash_str,
    "Hello from your friendly bot!",
    title="Bot Message",
    lxmf_fields=icon_lxmf_field
)

# You can also combine it with other fields, like attachments:
# attachment_field = pack_attachment(some_attachment)
# combined_fields = {**icon_lxmf_field, **attachment_field}
# bot.send(destination, "Message with icon and attachment", lxmf_fields=combined_fields)
```

## Scheduler

Task scheduling system:

``` python
@bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
def daily_task():
    # Run daily at midnight
    pass
```

## Signatures

LXMFy provides configuration options for LXMF's built-in cryptographic
message signing and verification:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Enable signature checks
    require_message_signatures=False      # Set to True to reject unsigned messages
)
```

!!! note "Signature handling"

    LXMF automatically handles all cryptographic signing and
    verification using RNS identities. LXMFy's `SignatureManager` is a
    configuration layer that:

    - Controls whether to enforce signature verification
    - Determines policy for unsigned messages (accept or reject)
    - Integrates with the permission system (e.g., bypass verification
      for trusted users)

The actual cryptographic operations are performed by LXMF/RNS, not by
LXMFy.

### Landlock LSM Sandbox

On Linux kernels with Landlock support (5.13+), LXMFy can restrict
filesystem access for the bot process and for external script cogs.

**Bot process sandbox**

When `landlock_enabled=True` (default) and not running in `test_mode`,
the bot calls `apply_landlock_sandbox()` during initialization. System
directories are read-only; bot storage, config, cogs, Reticulum config,
and temp paths remain writable.

``` python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
# status keys: landlock_kernel_supported, landlock_requested,
# landlock_auto_enabled, landlock_disabled_by_env, landlock_active
```

**Environment override**

- `LXMFY_LANDLOCK=0`: disable Landlock even on supported kernels
- `LXMFY_LANDLOCK=1`: attempt Landlock on Linux regardless of
  auto-detection
- unset: follow `landlock_enabled` and kernel auto-detection

**External cog sandbox**

Script cogs use `external_cogs_sandbox_type`. In `auto` mode, Landlock
is preferred when available because it requires no external tools. See
the [Creating Bots](creating-bots.md) guide for the full sandbox
option list.

### Identity Pinning

LXMFy supports optional identity pinning to prevent impersonation if an
identity is rotated or compromised. When enabled, the bot "pins" an LXMF
address to its first-seen public key.

``` python
bot = LXMFBot(
    identity_pinning_enabled=True
)
```

### SignatureManager Methods

The `SignatureManager` is available as `bot.signature_manager` when
`signature_verification_enabled=True`:

- `should_verify_message(sender)`: Determine if a message from the given
  sender should be verified
- `handle_unsigned_message(sender, message_hash)`: Handle messages that
  lack valid signatures based on policy

### How LXMF Signatures Work

LXMF automatically signs all outgoing messages using the sender's RNS
identity during the `pack()` operation. When messages are received, LXMF
validates signatures and provides:

- `message.signature_validated`: Boolean indicating if the signature is
  valid
- `message.unverified_reason`: Reason code if validation failed (e.g.,
  `SIGNATURE_INVALID`, `SOURCE_UNKNOWN`)

LXMFy uses these built-in LXMF properties to enforce your bot's
signature policy.

## Message Delivery

LXMFy provides advanced message delivery features including propagation
nodes and automatic retries:

### Propagation Nodes

Send messages through specific propagation nodes for improved
reliability on the Reticulum network:

``` python
# Configure the propagation node once at config/runtime level
bot.set_propagation_node("<propagation_node_hash>")

# Send using configured delivery behavior
bot.send(
    destination_hash,
    "Message content"
)

# The propagation node hash should be a valid LXMF propagation node
# on the Reticulum network
```

You can also set the node at construction time with
`propagation_node="<hash>"`, or let the bot discover nodes itself:

``` python
bot = LXMFBot(
    name="AutoBot",
    autopeer_propagation=True, # learn nodes from announces
    autopeer_maxdepth=4,       # ignore nodes deeper than 4 hops
)
```

`bot.get_propagation_node_status()` reports the manual node, the
discovered nodes, and the outbound node currently in use.

### Automatic Retries

Configure automatic retry attempts for failed direct deliveries:

``` python
bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Retry direct delivery up to 5 times
    propagation_fallback_enabled=True
)

bot.send(destination_hash, "Important message")

# Default direct_delivery_retries is 3
# Retry logic automatically handles delivery callbacks
```

The retry system tracks delivery attempts per destination and
automatically retries failed deliveries. Successful deliveries reset the
retry counter for that destination.

### Deferred Sends

Sending to a destination whose identity the node has not heard yet
normally fails outright. With `pending_sends_enabled` (default) the
message is held in storage instead, then flushed automatically when the
destination announces or on a periodic sweep.

``` python
bot = LXMFBot(
    pending_sends_enabled=True,
    pending_sends_max=200,     # oldest held messages drop beyond this
    pending_sends_ttl=604800,  # held messages expire after 7 days
    pending_sends_retry=300,   # seconds between sweeps in run()
)

# Per-send override
bot.send(dest, "hold this", defer=True)
bot.send(dest, "send or drop", defer=False)
```

Held sends appear as `held (unknown peers)` in the `/queue` admin
command and produce `deferred` events on the delivery tracker.

### Message Persistence

Outgoing messages can be persisted to disk to ensure they are delivered
even after a bot restart. Persistence is enabled by default. The
in-memory outbound queue is bounded (`message_queue_size`, default 50)
and drops the oldest message when full. Invalid destination hashes are
not restored.

``` python
bot = LXMFBot(
    message_persistence_enabled=True,
    message_queue_size=50,
)
```

### Stamps and Tickets

Stamp costs make senders pay proof-of-work before their message is
accepted, which throttles unsolicited traffic. LXMFy exposes both sides
of the mechanism.

``` python
bot = LXMFBot(
    stamp_cost=16,          # require this inbound stamp cost
    require_stamps=True,    # reject messages with invalid stamps
    include_tickets=True,   # let peers reply without grinding a stamp
)
```

- `stamp_cost` is the inbound requirement. The outbound cost for a send
  still comes from the peer's announce unless you pass `stamp_cost=`
  to `bot.send()`.
- `include_tickets` (default True) attaches a reply ticket to outbound
  messages, so a peer that requires stamps can answer without paying.
  Override per send with `include_ticket=`.
- `request_unknown_identities=True` asks the network for a sender
  identity when a message arrives from an unknown source, which helps
  stamp and signature checks resolve instead of failing blind.

Runtime control lives under [Router Controls](#router-controls):
`set_inbound_stamp_cost`, `enforce_stamps`, `ignore_stamps`,
`generate_ticket`, and the ticket inspection methods.

### Running a Propagation Node

A bot can double as an LXMF propagation node, storing messages for
peers that are offline:

``` python
bot = LXMFBot(
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)

bot.set_message_storage_limit(750)
stats = bot.get_propagation_storage_stats()
```

`get_propagation_node_status()` works for both roles: it reports the
outbound node this bot uses and whether it is serving as a node itself.
Related controls: `announce_propagation_node()` advertises the node,
`set_retain_on_node()` keeps delivered messages on it, and
`allow_control_identity()` / `disallow_control_identity()` manage which
identities may use the node's control channel.

### Delivery Events

`bot.delivery` records a bounded stream of outbound lifecycle events so
you can watch message flow without reading logs. Stages: `queued`,
`deferred`, `dispatched`, `delivered`, `failed`, `cancelled`, `dropped`.
The recent tail is persisted to storage and restored on startup.

``` python
@bot.on_delivery_event()
def watch(event):
    print(event["stage"], event.get("destination"), event.get("reason"))

# Or inspect directly
recent = bot.delivery.recent(20)
failures = bot.delivery.recent(stage="failed")
to_peer = bot.delivery.recent(destination="aa11bb...")
```

Each event is a dict with `ts`, `stage`, and optional `destination`,
`message_id`, `hash`, `method`, `attempts`, `reason`, `title`.

Admins get a `/delivery [limit]` command that renders the same timeline
in chat, and `lxmfy debug` shows a delivery timeline summary in the
send pipeline checks.

### Built-in Admin Commands

These commands are registered automatically and require the sender to
be in `admins` when permissions are enabled:

| Command | Action |
| --- | --- |
| `/queue` | Show router outbound queue, internal queue, and held sends |
| `/cancel <id|all>` | Cancel pending outbound messages |
| `/inbox [cancel <hash|all>]` | List or cancel active inbound transfers |
| `/delivery [n]` | Show the last n delivery events (default 15, max 50) |
| `/loadext <name>` | Load a cog extension |
| `/reloadext <name>` | Reload a loaded cog extension |

### Router Controls

Thin wrappers over the underlying `LXMRouter` for sender control,
tickets, outbound queue management, and propagation node sync. All take
destination hashes as hex strings and return `False` when the router is
not running (for example in `test_mode`).

**Sender control (inbound)**

- `ignore_destination(destination)` / `unignore_destination(destination)` / `is_ignored(destination)`:
  Drop inbound messages from a sender
- `allow_destination(destination)` / `disallow_destination(destination)`:
  Whitelist management when the router runs in allow-list mode
- `prioritise_destination(destination)` / `unprioritise_destination(destination)`:
  Prioritized sender list
- `set_inbound_stamp_cost(stamp_cost)`: Require a stamp cost on inbound
  messages (`None` clears)
- `enforce_stamps()` / `ignore_stamps()`: Inbound stamp enforcement
  toggles

**Tickets**

- `generate_ticket(destination, expiry=None)`: Issue an inbound stamp
  ticket for a sender
- `get_inbound_tickets(destination)`: Tickets held for a sender
- `get_outbound_ticket(destination)` / `get_outbound_ticket_expiry(destination)` /
  `get_outbound_stamp_cost(destination)`: Outbound ticket state learned
  from the network

**Outbound queue**

- `outbound_queue()`: Snapshot of pending outbound messages
- `get_outbound_progress(lxm_hash)`: Delivery progress for a message
  hash, or `None`
- `cancel_outbound(message_id)`: Remove a queued message before
  delivery
- `delivery_link_available(destination)`: Whether an active RNS link
  exists to the destination

**Inbound queue**

- `has_message(message_hash)`: Whether an inbound LXM hash was already
  delivered
- `inbound_count()`: Active inbound resource transfers in progress
- `inbound_transfers()`: Snapshot of each transfer with hash, size,
  progress, and status
- `cancel_inbound(resource_hash)`: Abort an active inbound transfer
- `cancel_all_inbound()`: Abort every active inbound transfer, returns
  the count cancelled

**Peer discovery**

Announce metadata for destinations this node has heard:

- `get_peer_app_data(destination)`: Raw announced app_data bytes
- `get_peer_lxmf_data(destination)`: Decoded LXMF announce metadata
  (`display_name`, `stamp_cost`, `capabilities`), or `None` when the
  peer has not announced valid LXMF data
- `get_peer_announce(destination)`: Full announce record with hops,
  received_at, interface, and app_data
- `list_peer_announces(limit=100)`: All heard announces, newest first

**Propagation**

- `sync_propagation_node(max_messages=None)`: Pull messages from the
  configured propagation node
- `cancel_propagation_sync()`: Stop an in-progress sync
- `get_propagation_stats()`: Node transfer state and limits, or `None`
- `set_retain_on_node(retain)`: Keep delivered messages on the node
- `announce_propagation_node()`: Announce this node as a propagation
  node
- `allow_control_identity(destination)` / `disallow_control_identity(destination)`:
  Propagation control channel whitelist

**Ingest**

- `ingest_lxm_uri(uri)`: Import an `lxm://` URI message into the
  inbound queue

## Diagnostics

When messages do not flow, the debugger checks the whole path instead
of guessing: Reticulum config, shared instance state, interfaces,
identity, announce behavior, delivery config, and the send pipeline.

``` bash
lxmfy debug                          # full doctor report, saved to a file
lxmfy debug probe <hash> --request-path --wait 30
lxmfy debug send <hash>              # trace a test send
lxmfy debug receive                  # check inbound readiness
lxmfy debug compare <hash_a> <hash_b>
lxmfy debug tips                     # common failure fixes
```

Reports are privacy-redacted by default: home paths and hashes are
truncated. `--json` emits machine-readable output, `-o FILE` writes the
report, `--no-save` skips the file, `--no-privacy` keeps full values
for local use, and `--no-color` or `NO_COLOR` disables ANSI output.

The same checks are callable from code:

``` python
report = bot.diagnose_connectivity()            # doctor report as dict
probe = bot.diagnose_destination(               # identity and path probe
    "<peer_hash>", request_path=True, wait=30,
)

debugger = bot.get_debugger()                   # full API
checks = debugger.check_send_pipeline()
verdict = debugger.run_doctor(destination)
```

`lxmfy/debugger.py` also exports a standalone
`diagnose_destination(hash, ...)` helper plus the report types
`CheckResult`, `DestinationProbe`, `DoctorReport`, and
`MessageDebugger` for custom tooling.

## Message Handlers

LXMFy provides decorators for handling different types of incoming
messages:

### First Message Handler

Handle the first message from each user:

``` python
@bot.on_first_message()
def welcome_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(sender, f"Welcome! You said: {content}")
    return True  # Return True to stop further processing
```

### General Message Handler

Handle all incoming messages before command processing:

``` python
@bot.on_message()
def handle_all_messages(sender, message):
    content = message.content.decode("utf-8").strip()

    # Custom logic here
    if content.startswith("echo:"):
        bot.send(sender, content[5:])
        return True  # Stop further processing

    return False  # Continue to command processing
```

Message handlers are called in this order: 1. First message handler (if
this is the first message from this sender) 2. General message handlers
(registered with `on_message()`) 3. Command processing (if message
starts with command prefix)

### Fallback Callback

`bot.received(fn)` registers a callback that runs at the end of the
pipeline for messages nothing else consumed: no first-message handler,
no `on_message` handler that returned True, no matching command or NLP
intent. The callback gets the same message context commands receive,
with `msg.sender`, `msg.content`, `msg.reply()`, and friends.

``` python
@bot.received
def fallback(msg):
    msg.reply("Sorry, I did not understand that.")
```

Use it as a catch-all for free-text input.

## Reticulum Relay Chat (RRC)

Bots can join [RRC](https://rrc.kc1awv.net/) hubs over RNS Links with
CBOR envelopes. Package: `lxmfy.rrc`.

### BotConfig options

- `rrc_enabled` (bool, default `False`): Connect configured hubs on
  startup
- `rrc_hubs` (list of hex hashes): Hub destination hashes
- `rrc_rooms` (list of str): Rooms to auto-join after WELCOME
- `rrc_nick` (str or None): Nickname on HELLO and room messages
- `rrc_dest_name` (str, default `"rrc.hub"`): Destination name used to
  build the hub destination
- `rrc_auto_reconnect` (bool, default `True`): Reconnect after link loss
- `rrc_persist_sessions` (bool, default `True`): Persist hubs and rooms
  across restarts
- `reticulum_config_dir` (str or None): Reticulum config directory. Also
  set via `LXMFY_RETICULUM_CONFIG_DIR`. Use the same config as MeshChatX
  (often `~/.reticulum`) so hub announces are visible.

### Example

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "msg" and isinstance(payload, RRCMessage) and payload.mention:
        client.send_message(payload.room, f"Hi {payload.nick}")

# Runtime API
# bot.connect_rrc(hub_hash, rooms=["general"])
# bot.rrc.send_message("general", "hello")
# bot.rrc.send_notice("general", "notice")
# bot.rrc.send_action("general", "waves")
# bot.rrc.join("ops")
# bot.rrc.part("ops")
# bot.rrc.status()
# bot.disconnect_rrc()
```

### Exported types

- `RRCClient`: Single-hub session
- `RRCManager`: Multi-hub manager (`bot.rrc`)
- `RRCMessage`: Room event payload (`kind`, `room`, `text`, `nick`,
  `src`, `mention`, ...)
- `RRC_VERSION`: Wire protocol version constant
- `DEFAULT_DEST_NAME`: Default hub destination name (`"rrc.hub"`)
- `make_envelope`, `encode_envelope`, `decode_envelope`,
  `validate_envelope`, `normalize_room`: Wire-format helpers for
  tooling that talks to hubs directly

Common events passed to `@bot.on_rrc` handlers include `status`,
`welcome`, `joined`, `parted`, `msg`, `notice`, `action`, `motd`,
`error`, and `rtt`.

# Templates

The framework includes several ready-to-use bot templates:

## EchoBot

Simple echo bot that repeats messages:

``` python
from lxmfy.templates import EchoBot

bot = EchoBot()
bot.run()
```

## NoteBot

Note-taking bot with JSON storage:

``` python
from lxmfy.templates import NoteBot

bot = NoteBot()
bot.run()
```

## ReminderBot

Reminder bot with SQLite storage:

``` python
from lxmfy.templates import ReminderBot

bot = ReminderBot()
bot.run()
```

## RRCBot

RRC room bot that joins configured hubs and replies to `@mentions`.
Defaults to hub `664fc0e8d2e448658e37bb3f34e6c88f`, room `#general`, and
`~/.reticulum` when available.

``` python
from lxmfy.templates import RRCBot

bot = RRCBot(
    hubs=["664fc0e8d2e448658e37bb3f34e6c88f"],
    rooms=["general"],
    nick="RRCBot",
    reticulum_config_dir="~/.reticulum",
)
bot.run()
```

# CLI Tools

The framework provides command-line tools for bot management. Running
`lxmfy` with no arguments opens an interactive menu.

``` bash
# Scaffold a full project interactively
lxmfy init mybot                 # project dir, bot.py, cogs/, README
lxmfy init --here --yes          # current dir, accept all defaults

# Create a single bot file
lxmfy create mybot
lxmfy create --template echo mybot
lxmfy create --template rrc my_rrc_bot
lxmfy create mybot --no-cogs     # skip the cogs package
lxmfy create --output dir/bot.py --name MyBot

# Run a template bot
lxmfy run echo
lxmfy run rrc
lxmfy run reminder --name "MyReminder"

# Diagnose connectivity (see the Diagnostics section)
lxmfy debug
lxmfy debug probe <hash> --request-path --wait 30

# Test signature verification with a message
lxmfy signatures test

# Enable signature verification
lxmfy signatures enable

# Disable signature verification
lxmfy signatures disable
```

`lxmfy init` prompts for project name, template, storage backend,
command prefix, and admin hashes. Every prompt accepts a flag instead:
`--dir`, `--bot-name`, `--template`, `--storage`, `--prefix`,
`--admins`, `--no-cogs`, `--force`, `--yes`. On a non-TTY stdin it
takes the defaults.

Templates for `create` and `run`: `basic`, `echo`, `reminder`, `note`,
`cogtest`, `rrc`.

# Error Handling

Catch shutdown and runtime failures around `bot.run()`:

``` python
try:
    bot.run()
except KeyboardInterrupt:
    bot.cleanup()
except Exception as e:
    logger.error(f"Error running bot: {str(e)}")
```

# Module Reference

Generated from source docstrings.

::: lxmfy.LXMFBot

::: lxmfy.BotConfig

::: lxmfy.Command

::: lxmfy.Attachment

::: lxmfy.AttachmentType

::: lxmfy.IconAppearance

::: lxmfy.Event

::: lxmfy.EventManager

::: lxmfy.EventPriority

::: lxmfy.MiddlewareContext

::: lxmfy.MiddlewareManager

::: lxmfy.MiddlewareType

::: lxmfy.DefaultPerms

::: lxmfy.PermissionManager

::: lxmfy.Role

::: lxmfy.HelpFormatter

::: lxmfy.HelpSystem

::: lxmfy.TaskScheduler

::: lxmfy.ScheduledTask

::: lxmfy.Storage

::: lxmfy.JSONStorage

::: lxmfy.SQLiteStorage

::: lxmfy.storage.MemoryStorage

::: lxmfy.MsgPackStorage

::: lxmfy.ConversationManager

::: lxmfy.Answer

::: lxmfy.DeliveryTracker

::: lxmfy.TestBot

::: lxmfy.SentMessage

::: lxmfy.Debugger

::: lxmfy.MessageDebugger

::: lxmfy.DoctorReport

::: lxmfy.DestinationProbe

::: lxmfy.CheckResult

::: lxmfy.RRCClient

::: lxmfy.RRCManager

::: lxmfy.RRCMessage
