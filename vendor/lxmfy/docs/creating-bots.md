# Creating Bots

## Basic Structure

A minimal LXMFy bot involves:

1.  Importing `LXMFBot`.
2.  Instantiating `LXMFBot` with desired configuration.
3.  Defining commands or event handlers.
4.  Running the bot using `bot.run()`.

``` python
from lxmfy import LXMFBot

# 1. Instantiate the bot
bot = LXMFBot(
    name="SimpleBot",
    command_prefix="!",
    storage_path="simple_data"
)

# 2. Define commands
@bot.command(name="ping", description="Responds with pong")
def ping_command(ctx):
    # ctx is a context object containing message info
    # ctx.sender: Sender's LXMF hash
    # ctx.content: Full message content
    # ctx.args: List of arguments after the command
    # ctx.reply(message): Function to send a reply
    #   (can also take keyword arguments like title="My Title", lxmf_fields=some_fields)
    ctx.reply("Pong!")

# For long-running tasks, you can use threaded commands:
# import time
# @bot.command(name="long_op", description="Performs a long operation in a separate thread", threaded=True)
# def long_op_command(ctx):
#     ctx.reply("Starting long operation...")
#     time.sleep(10) # Simulate a long-running operation
#     ctx.reply("Long operation complete!")
# Important: Threaded commands should not directly interact with RNS or lxmfy.transport.py.

@bot.command(name="greet", description="Greets the user")
def greet_command(ctx):
    if ctx.args:
        name = " ".join(ctx.args)
        ctx.reply(f"Hello, {name}!")
    else:
        ctx.reply("Hello there! Tell me your name: !greet <your_name>")

# 3. Run the bot
if __name__ == "__main__":
    print(f"Starting bot: {bot.config.name}")
    print(f"Bot LXMF Address: {bot.local.hash}")
    bot.run()
```

## Using Templates

LXMFy provides several templates for common bot types. You can use the
CLI to generate a bot file based on a template.

For a full project directory instead of a single file, `lxmfy init`
scaffolds `bot.py`, a `cogs` package, a README, and a `.gitignore`,
asking about template, storage backend, command prefix, and admin
hashes along the way.

``` bash
# Create an echo bot
lxmfy create --template echo my_echo_bot

# Create a reminder bot (uses SQLite storage)
lxmfy create --template reminder my_reminder_bot

# Create a note-taking bot (uses JSON storage)
lxmfy create --template note my_note_bot

# Create a cog test bot (tests cog loading features)
lxmfy create --template cogtest my_cog_test_bot

# Create an RRC room bot (joins hubs and replies to @mentions)
lxmfy create --template rrc my_rrc_bot

# Or run the template directly
lxmfy run rrc
```

Running these commands creates a Python file (e.g., `my_echo_bot.py`)
that imports and runs the chosen template. You can then modify the
generated file or the template code itself (`lxmfy/templates/...`).

**Example generated file (`my_cog_test_bot.py`):**

``` python
from lxmfy.templates import CogTestBot

if __name__ == "__main__":
    bot = CogTestBot() # Creates an instance of the CogTestBot template
    # You can optionally override the default name:
    # bot.bot.name = "My Cog Test Bot"
    bot.run()
```

## Bot Configuration

When creating an `LXMFBot` instance, you can pass various keyword
arguments to configure its behavior. See the `BotConfig` section in the
[API Reference](api-reference.md) or the [Quick Start
Guide](quick-start.md) for a list of common options.

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="ConfiguredBot",
    announce=3600, # Announce every hour
    admins={"your_admin_hash_here"}, # Set admin user(s)
    command_prefix="$", # Use '$' as prefix
    storage_type="sqlite", # Use SQLite database
    storage_path="data/my_bot_data.db", # Specify DB file path
    rate_limit=10, # Allow 10 messages / minute
    cooldown=30, # Cooldown of 30 seconds
    permissions_enabled=True # Enable role-based permissions
)

if __name__ == "__main__":
    # You can also modify config after instantiation
    # Note: some settings are best set during init
    bot.config.max_warnings = 5
    bot.spam_protection.config.max_warnings = 5 # Update spam protector too

    bot.run()
```

### Setting a Bot Icon (LXMF Field)

You can give your bot a custom icon that appears in compatible LXMF
clients. This uses the `LXMF.FIELD_ICON_APPEARANCE` and can be set when
sending messages.

First, ensure you have the necessary imports:

``` python
from lxmfy import IconAppearance, pack_icon_appearance_field
```

Then, you can define and use the icon:

``` python
# In your bot class or setup
icon_data = IconAppearance(
    icon_name="robot_2",  # Choose from Material Symbols
    fg_color=b'\x00\xFF\x00',  # Green
    bg_color=b'\x33\x33\x33'   # Dark Grey
)
self.bot_icon_field = pack_icon_appearance_field(icon_data)

# When sending a message or replying:
ctx.reply("Message from your bot!", lxmf_fields=self.bot_icon_field)
# or
# bot.send(destination, "Another message", lxmf_fields=self.bot_icon_field)
```

This `self.bot_icon_field` can be pre-calculated and reused for all
messages sent by the bot.

## Structured Commands via LXMF Fields

In addition to text-based commands, LXMFy supports commands sent through
LXMF message fields using `FIELD_COMMANDS` (`0x09`). This is useful for
structured request/response workflows between LXMF clients and bots.

When a message contains `FIELD_COMMANDS`, the bot extracts the command
name and arguments, routes them through the same command registry as
text commands, and automatically includes `FIELD_RESULTS` (`0x0A`) in
the reply.

**Receiving structured commands**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="FieldBot")

@bot.command(name="add", description="Add two numbers")
def add_command(ctx):
    if len(ctx.args) >= 2:
        try:
            result = float(ctx.args[0]) + float(ctx.args[1])
            ctx.reply(str(result))
        except ValueError:
            ctx.reply("Invalid numbers")
    else:
        ctx.reply("Usage: add <a> <b>")
```

The `ctx` object in field command callbacks includes:

- `ctx.fields`: the raw LXMF fields dict from the incoming message
- `ctx.request_id`: the `request_id` from the incoming `FIELD_COMMANDS`
  (if any)

**Sending a structured command from an LXMF client**

``` python
import LXMF
from lxmfy import FIELD_COMMANDS

lxm = LXMF.LXMessage(
    destination,
    source,
    b"",  # content can be empty for field-only commands
    desired_method=LXMF.LXMessage.DIRECT,
)
lxm.fields[FIELD_COMMANDS] = {
    "command": "add",
    "args": ["3", "5"],
    "request_id": "req-42",  # optional, for correlation
}
router.handle_outbound(lxm)
```

**Disabling field commands**

If you want the bot to ignore `FIELD_COMMANDS` and only process text
commands, set:

``` python
bot = LXMFBot(
    name="TextOnlyBot",
    lxmf_commands_enabled=False,
)
```

## Using Cogs (Extensions)

Cogs allow you to organize your commands and event listeners into
separate files (modules), keeping your main bot file cleaner.

1.  **Create a `cogs` directory** (or whatever you set
    `cogs_dir` to in `BotConfig`).
2.  **Create Python files** inside the `cogs` directory (e.g.,
    `utility.py`).
3.  **Define a class** that inherits from `lxmfy.Cog` (optional but good
    practice) or is just a standard class.
4.  **Define commands** as methods within the class using the `@Command`
    decorator.
5.  **Create a `setup(bot)` function** in the cog file, which
    LXMFy will call to register the cog.

**Example (`cogs/utility.py`):**

``` python
from lxmfy import Command
from lxmfy.commands import Cog  # Import Cog if inheriting
import time

class UtilityCog: # Or class UtilityCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @Command(name="uptime", description="Shows bot uptime")
    # Note: Methods in cogs often take 'self' and 'ctx'
    def uptime_command(self, ctx):
        uptime_seconds = time.time() - self.start_time
        ctx.reply(f"Bot has been running for {uptime_seconds:.2f} seconds.")

    @Command(name="info", description="Shows bot info")
    def info_command(self, ctx):
        info = (
            f"Bot Name: {self.bot.config.name}\n"
            f"Owner(s): {', '.join(self.bot.config.admins) or 'None'}\n"
            f"Prefix: {self.bot.config.command_prefix}"
        )
        ctx.reply(info)

    @Command(name="threaded_cog_task", description="Performs a long task in a cog thread", threaded=True)
    def threaded_cog_task(self, ctx):
        ctx.reply("Starting a long cog task... this will run in a separate thread.")
        time.sleep(7) # Simulate a long-running operation
        ctx.reply("Long cog task completed!")

# This function is required for the cog to be loaded
def setup(bot):
    cog_instance = UtilityCog(bot)
    bot.add_cog(cog_instance) # Register the cog instance with the bot
```

**Main Bot File (`my_bot.py`):**

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="CogBot",
    cogs_enabled=True, # Make sure cogs are enabled (default)
    cogs_dir="cogs" # Point to the directory
)

if __name__ == "__main__":
    # Cogs are loaded automatically during LXMFBot initialization
    # if cogs_enabled is True.
    bot.run()
```

When the bot starts, it will automatically find `utility.py`, call its
`setup` function, which creates an instance of `UtilityCog` and
registers it using `bot.add_cog()`. The commands defined in the cog
(`uptime`, `info`) will then be available.

## External Script Cogs (Multi-Language Support)

You can also write bot extensions in languages other than Python (e.g.,
Bash, Ruby, Perl, Go, C) using External Script Cogs.

1.  **Create an executable script** in your `cogs` directory.
2.  **Add a shebang** at the top of the script (e.g., `#!/bin/bash`).
3.  **Ensure the script is executable** (`chmod +x your_script`).

When the bot starts, it will automatically register any executable file
in the `cogs` directory (that doesn't end in `.py`) as a bot command.

**Argument Protocol:**

- `$1`: Sender's LXMF hash.
- `$2`: Full message content.
- `$3`, `$4`, ...: Individual command arguments.

**Environment Variables:**

- `LXMFY_SENDER`: The sender's identity hash.
- `LXMFY_CONTENT`: The full message content.
- `LXMFY_HAS_ADMIN`: `true` or `false` depending on the sender's admin
  status.

**Example Bash Cog (`cogs/greet.sh`):**

``` bash
#!/bin/bash
echo "Hello from Bash! You sent: $2"
```

When a user sends `/greet hello`, the bot will execute this script and
reply with its stdout: `Hello from Bash! You sent: /greet hello`.

## Local NLP Intent Classification

LXMFy ships a local intent classifier. It matches message text to
labeled example phrases when the text does not match a command prefix
exactly.

1.  **Enable NLP** in your bot configuration: `nlp_enabled=True`.
2.  **Define intents** using the `@bot.intent` decorator.

``` python
@bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
def help_intent(msg):
    msg.reply("I can help! Try typing /help to see a list of commands.")
```

Matching uses TF-IDF vectors and cosine similarity. All scoring runs on
the bot host. No text is sent to an external API.

**Model export and import**

Export and import a trained model so larger bots skip retraining on
every startup:

``` python
# Export the model
model_data = bot.nlp.export_model()
# Save model_data to a file or database

# Later, import it back
bot.nlp.import_model(model_data)
```

## RNS Link Support

Bots can establish and respond to direct RNS Links for stateful,
streaming, or higher-bandwidth traffic than single LXMF packets.

1.  **Enable Link Support** in configuration:
    `link_support_enabled=True`.
2.  **Request a link**: `bot.request_link(destination_hash)`. You can
    also specify a custom app name and aspects:
    `bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Handle incoming links**: Register a callback with
    `bot.on_link(handler)`.

``` python
def handle_link(link):
    print(f"Link established with {RNS.hexrep(link.destination.hash)}")
    # You can now use the link for direct RNS communication

bot.on_link(handle_link)
```

**Safety & Sandboxing:**

- **Timeouts:** External cogs have a default timeout (30s) to prevent
  hanging. This is configurable via `external_cogs_timeout`.
- **Threading:** All external cogs run in separate threads and do not
  block the bot.
- **Bot process sandbox (Linux only):** When `landlock_enabled=True`
  (default) and the kernel supports Landlock LSM (5.13+), the bot
  applies a filesystem sandbox to its own process after startup.
  Writable paths are limited to storage, config, cogs, Reticulum config,
  and temp directories. Override with the environment variable
  `LXMFY_LANDLOCK=0` to disable or `LXMFY_LANDLOCK=1` to force an
  attempt.
- **External cog sandbox (Linux only):** When
  `external_cogs_sandbox_enabled=True` (default), executable script cogs
  run inside a restricted environment. Set `external_cogs_sandbox_type`
  to one of:
  - `auto` (default): prefer Landlock when supported, otherwise
    `bubblewrap` (`bwrap`), otherwise `firejail`
  - `landlock`: Landlock-only sandbox via `preexec_fn` (narrower rules
    than the bot process sandbox)
  - `bwrap`: bubblewrap read-only bind sandbox
  - `firejail`: firejail private profile with no network
  - `none`: no subprocess sandbox
- **Status:** Call `bot.get_landlock_status()` to inspect kernel
  support, whether Landlock was requested, and whether the bot process
  sandbox is active.

## Handling Messages

LXMFy provides several ways to handle incoming messages at different
stages of processing.

### First Message Handler

Handle the first message from each new user (useful for welcome
messages):

``` python
from lxmfy import LXMFBot

bot = LXMFBot(
    name="WelcomeBot",
    first_message_enabled=True  # Must be True (default)
)

@bot.on_first_message()
def welcome_new_user(sender, message):
    content = message.content.decode("utf-8")
    bot.send(
        sender,
        f"Welcome to the bot! You said: {content}\n\n"
        "Type /help to see available commands."
    )
    return True  # Return True to stop further processing of this message

if __name__ == "__main__":
    bot.run()
```

### General Message Handler

Handle all incoming messages before command processing:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="EchoBot")

@bot.on_message()
def echo_non_commands(sender, message):
    content = message.content.decode("utf-8").strip()

    # Check if this is a command - if so, let command handler deal with it
    if content.startswith(bot.config.command_prefix):
        command_name = content.split()[0][len(bot.config.command_prefix):]
        if command_name in bot.commands:
            return False  # Let command handler process it

    # Not a command, echo it back
    bot.send(sender, f"You said: {content}")
    return False  # Return False to continue processing (though no commands will match)

@bot.command(name="hello", description="Say hello")
def hello_command(ctx):
    ctx.reply("Hello! This is a command response.")

if __name__ == "__main__":
    bot.run()
```

Message Handler Processing Order:

1.  **First Message Handler** (if `first_message_enabled=True` and this
    is first message from sender)
2.  **General Message Handlers** (registered with `@bot.on_message()`)
3.  **Command Processing** (if message matches a registered command)

Handlers can return `True` to stop further processing or `False` to
continue to the next stage.

## Handling Events

You can register handlers for various bot events using the
`@bot.events.on()` decorator.

``` python
from lxmfy import LXMFBot
from lxmfy.events import EventPriority # Optional for priority

bot = LXMFBot(name="EventBot")

@bot.events.on("message_received")
def log_message(event):
    # Event object contains details
    sender = event.data.get("sender")
    message_content = event.data.get("message").content.decode('utf-8', errors='ignore')
    print(f"Received message from {sender}: {message_content}")

    # You can cancel event processing (e.g., stop message handling)
    # if sender == "some_blocked_hash":
    #    event.cancel()

@bot.events.on("command_executed", priority=EventPriority.LOW)
def log_command(event):
    # Example: event.data might contain {'command_name': 'ping', 'sender': '...', ...}
    command_name = event.data.get('command_name', 'unknown')
    sender = event.data.get('sender', 'unknown')
    print(f"Command '{command_name}' executed by {sender}")

# You can define custom events too
@bot.command(name="special")
def special_command(ctx):
    ctx.reply("Doing something special!")
    # Dispatch a custom event
    bot.events.dispatch(Event("special_action_taken", data={"user": ctx.sender}))

@bot.events.on("special_action_taken")
def handle_special(event):
    user = event.data.get("user")
    print(f"Special action was taken by user: {user}")


if __name__ == "__main__":
    bot.run()
```

See `lxmfy/events.py` for more details on the `Event` structure and
priorities.

## Storage

LXMFy provides JSON, SQLite, MsgPack, and In-Memory storage backends.

- **JSON:** Simple, human-readable. Good for small datasets. Configure
  with `storage_type="json"` and `storage_path="your_data_dir"`.
- **SQLite:** More efficient for larger datasets or frequent writes.
  Configure with `storage_type="sqlite"` and
  `storage_path="your_db_file.db"`.
- **MsgPack:** Compact binary format with the same one-file-per-key
  layout as JSON. Configure with `storage_type="msgpack"` and
  `storage_path="your_data_dir"`.
- **Memory:** Entirely in-RAM storage. State is lost on shutdown.
  Configure with `storage_type="memory"`.

You can access the storage interface via `bot.storage`:

``` python
# Save data
bot.storage.set("user_prefs:" + ctx.sender, {"theme": "dark"})

# Get data (with a default value)
prefs = bot.storage.get("user_prefs:" + ctx.sender, {})
theme = prefs.get("theme", "light")

# Check if data exists
if bot.storage.exists("some_key"):
    print("Key exists!")

# Delete data
bot.storage.delete("old_data_key")

# Scan for keys with a prefix (useful for listing user data)
user_keys = bot.storage.scan("user_prefs:")
for key in user_keys:
    user_data = bot.storage.get(key)
    print(f"Data for {key}: {user_data}")
```

See `lxmfy/storage.py` and the API reference for more details.

## Permissions

LXMFy includes an optional role-based permission system. Enable it with
`permissions_enabled=True` during `LXMFBot` initialization.

- **Roles:** Define roles with specific permissions (e.g.,
  `DefaultPerms.MANAGE_USERS`).
- **Permissions:** Granular flags defined in `DefaultPerms` (e.g.,
  `USE_COMMANDS`, `BYPASS_SPAM`).
- **Assignment:** Assign roles to user hashes.

See `lxmfy/permissions.py`, the API reference, and potentially example
cogs (if any are created) for usage details.

## Signature Verification

LXMFy provides configuration for LXMF's built-in cryptographic message
signing and verification. All LXMF messages are automatically signed by
the LXMF/RNS stack - LXMFy simply allows you to enforce signature
verification policies.

**Configuration:**

Enable signature verification in your bot configuration:

``` python
bot = LXMFBot(
    name="SecureBot",
    signature_verification_enabled=True,  # Enable signature checking
    require_message_signatures=False      # Set to True to reject unsigned messages
)
```

**How It Works:**

LXMF automatically handles all cryptographic operations:

1.  **Outgoing Messages:** LXMF automatically signs all messages using
    the sender's RNS identity during message packing.
2.  **Incoming Messages:** LXMF automatically validates signatures using
    the sender's RNS identity and provides validation results.
3.  **LXMFy's Role:** LXMFy checks LXMF's validation results and
    enforces your policy:
    - If `signature_verification_enabled=False`: All messages are
      accepted (default)
    - If `signature_verification_enabled=True` and
      `require_message_signatures=False`: Messages are accepted but
      unsigned/invalid signatures are logged
    - If `signature_verification_enabled=True` and
      `require_message_signatures=True`: Unsigned or invalid messages
      are rejected
4.  **Permission Integration:** Users with `BYPASS_SPAM` permission can
    bypass signature verification requirements.

**CLI Management:**

You can manage signature verification settings using the CLI:

``` bash
# Test signature verification
lxmfy signatures test

# Enable signature verification
lxmfy signatures enable

# Disable signature verification
lxmfy signatures disable
```

**Technical Details:**

LXMF uses Ed25519 signatures provided by the RNS cryptography system.
Every LXMF message includes the sender's signature, which is validated
against their known RNS identity. LXMFy simply reads LXMF's
`message.signature_validated` property and `message.unverified_reason`
to enforce your bot's security policy.

## Message Delivery

### Using Propagation Nodes

Send messages through specific LXMF propagation nodes:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="PropagationBot")

@bot.command(name="send", description="Send via propagation node")
def send_command(ctx):
    # Set a specific propagation node once (config-level)
    bot.set_propagation_node("<propagation_node_hash_here>")

    # Send using configured delivery strategy
    bot.send(
        ctx.sender,
        "This message will use direct delivery with propagation fallback as configured"
    )
```

Use a propagation node when the destination is offline or direct
delivery keeps failing on the current path.

### Configuring Retries

Configure automatic retry attempts for failed message deliveries via bot
config:

``` python
from lxmfy import LXMFBot

bot = LXMFBot(name="ReliableBot")

bot = LXMFBot(
    name="ReliableBot",
    direct_delivery_retries=5,  # Retry direct delivery up to 5 times
    propagation_fallback_enabled=True
)

@bot.command(name="important", description="Send important message with retries")
def important_command(ctx):
    bot.send(ctx.sender, "This is an important message")

@bot.command(name="normal", description="Send with default retries")
def normal_command(ctx):
    # Default direct_delivery_retries is 3
    bot.send(ctx.sender, "This message uses default retry settings")
```

The retry system:

- Automatically tracks delivery attempts per destination
- Retries failed direct deliveries up to `direct_delivery_retries`
- Resets the retry counter on successful delivery
- Logs retry attempts and failures for debugging

### Deferred Sends and Stamps

Two delivery details are worth knowing early:

- **Deferred sends**: when the destination identity is not known yet,
  `send()` holds the message in storage (the `pending_sends_*` config
  keys control the backlog) and flushes it when the peer announces.
  Pass `defer=False` to a send to drop instead of holding.
- **Stamps**: `stamp_cost` sets an inbound proof-of-work requirement,
  `require_stamps` rejects messages that fail it, and
  `include_tickets` (default) attaches reply tickets so peers can
  answer your bot without paying their own stamp cost.

When delivery misbehaves, `lxmfy debug` walks the whole path (config,
instance, interfaces, identity, send pipeline) and writes a redacted
report you can share. The same checks are callable as
`bot.diagnose_connectivity()` and `bot.diagnose_destination(hash)`.

See the [API Reference](api-reference.md#message-delivery) for the full
delivery surface: retries, propagation nodes, queue persistence, the
delivery event stream, and the `/queue`, `/cancel`, `/inbox`,
`/delivery` admin commands.

## Reticulum Relay Chat (RRC)

LXMFy bots can join [RRC](https://rrc.kc1awv.net/) hubs as ordinary
clients over RNS Links using CBOR envelopes. This is compatible with
NomadNet and rrcd style hubs (including MeshChatX when it hosts or joins
the same hub).

### Reticulum config matters

The bot must use the **same** Reticulum network as the hub. MeshChatX
typically uses `~/.reticulum` with backbone or TCP interfaces. The
project-local `config/` directory often uses an isolated instance name
and AutoInterface only, so hub announces never arrive and you see
`Hub identity unknown`.

Prefer one of:

- Set `reticulum_config_dir` to your user config (usually
  `~/.reticulum`)
- Or export `LXMFY_RETICULUM_CONFIG_DIR=~/.reticulum`
- Keep MeshChatX or `rnsd` running so the shared instance is up before
  the bot starts

The `rrc` template defaults to `~/.reticulum` when that directory
exists.

### Quick start with the template

``` bash
lxmfy run rrc
```

Defaults:

- Hub: `664fc0e8d2e448658e37bb3f34e6c88f`
- Room: `#general`
- Reticulum config: `~/.reticulum` (or `LXMFY_RETICULUM_CONFIG_DIR`)

You should see logs for hub connect, welcome, auto-join, and
`RRC joined #general`.

### Programmatic RRC bot

``` python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    reticulum_config_dir="~/.reticulum",
    rrc_enabled=True,
    rrc_hubs=["your_rrc_hub_destination_hash"],
    rrc_rooms=["general"],
    rrc_nick="RoomBot",
    rrc_auto_reconnect=True,
    rrc_persist_sessions=True,
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "welcome":
        bot.logger.info("Welcomed by hub")
        return
    if event != "msg" or not isinstance(payload, RRCMessage):
        return
    if payload.mention and payload.room:
        client.send_message(
            payload.room,
            f"Heard you, {payload.nick}",
        )

bot.run()
```

Or connect at runtime:

``` python
bot.connect_rrc("hub_destination_hash", rooms=["general"])
bot.rrc.send_message("general", "hello room")
bot.rrc.send_action("general", "waves")
bot.disconnect_rrc()
```

### Session behavior

- HELLO / WELCOME, JOIN / PART, MSG / NOTICE / ACTION, PING / PONG,
  ERROR, RESOURCE_ENVELOPE
- Auto-reconnect with room re-join after WELCOME
- Client-side hub limit and rate-limit enforcement
- Session persistence across restarts (`rrc_persist_sessions`, default
  on)
- Outgoing LXMF queue persistence is separate
  (`message_persistence_enabled`)
