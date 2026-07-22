# LXMFy

Easily create LXMF bots for the Reticulum Network with this extensible framework.

[Docs](https://lxmfy.quad4.io)

## Feature

| Category | Key Capabilities |
| :--- | :--- |
| **Core** | Interactive CLI, Command Prefixes, Cron-style Task Scheduler, Middleware & Event Systems |
| **Connectivity** | Direct Delivery & Propagation Fallback, Auto-Peering, RNS Link Support, Opportunistic Sending, **RRC (Reticulum Relay Chat) hub client** |
| **Security** | Spam Protection, Role-based Permissions, Identity Pinning, Message Signing/Verification, Landlock LSM Filesystem Sandbox (Linux) |
| **NLP** | Local NLP Intent Classification (Offline/Private), Type-hinted Argument Parsing |
| **Extensions** | Python Cogs, External Script Cogs (Bash, Go, C, etc.), Linux Sandboxing (Landlock LSM, `bwrap`/`firejail`) |
| **Storage** | Extensible Backends (JSON, SQLite, In-Memory), Message Persistence (Crash Recovery) |
| **Reliability** | Extensive Stability & Mathematical Stress Testing, Chaos Engineering, Resource Leak Detection |
| **UX** | Help on First Message, Auto-generated Help Menus, Customizable Bot Icons, Attachments |

## Installation

**Requirements:** Python 3.11+, [RNS](https://pypi.org/project/rns/) 1.3.8+, [LXMF](https://pypi.org/project/lxmf/) 1.0.1+, [cbor2](https://pypi.org/project/cbor2/) 5.4.0+ (installed automatically with LXMFy).

There are many ways to install LXMFy, you pick:

### From PyPI

```bash
# pip
pip install lxmfy

# pipx
pipx install lxmfy
```

### Development Installation

For development, clone the repository and install with poetry:

```bash
git clone https://git.quad4.io/LXMFy/LXMFy.git
cd LXMFy
```

```bash
poetry install
```

## Usage

```bash
lxmfy
```

**Create bots:**

```bash
lxmfy create
```

## Docker

### Building Manually

To build the Docker image, navigate to the root of the project and run:

```bash
docker build -t lxmfy-test .
```

Once built, you can run the Docker image:

```bash
docker run -d \
    --name lxmfy-test-bot \
    -v $(pwd)/config:/bot/config \
    -v $(pwd)/.reticulum:/root/.reticulum \
    --restart unless-stopped \
    lxmfy-test
```

Auto-Interface support (network host):

```bash
docker run -d \
    --name lxmfy-test-bot \
    --network host \
    -v $(pwd)/config:/bot/config \
    -v $(pwd)/.reticulum:/root/.reticulum \
    --restart unless-stopped \
    lxmfy-test
```

### Building Wheels with docker/Dockerfile.Build

The `docker/Dockerfile.Build` is used to build the `lxmfy` Python package into a wheel file within a Docker image.

```bash
docker build -f docker/Dockerfile.Build -t lxmfy-wheel-builder .
```

This will create an image named `lxmfy-wheel-builder`. To extract the built wheel file from the image, you can run a container from this image and copy the `dist` directory:

```bash
docker run --rm -v "$(pwd)/dist_output:/output" lxmfy-wheel-builder
```

This command will create a `dist_output` directory in your current working directory and copy the built wheel file into it.

## Example

```python
from lxmfy import LXMFBot, load_cogs_from_directory

bot = LXMFBot(
    name="LXMFy Test Bot", # Name of the bot that appears on the network.
    announce=5400, # Announce every hour, set to 0 to disable.
    announce_enabled=True, # Set to False to disable all announces (both initial and periodic)
    announce_immediately=True, # Set to False to disable initial announce
    admins=["your_lxmf_hash_here"], # List of admin hashes.
    hot_reloading=True, # Enable hot reloading.
    command_prefix="/", # Set to None to process all messages as commands.
    cogs_dir="cogs", # Specify cogs directory name.
    rate_limit=5, # 5 messages per minute
    cooldown=5, # 5 seconds cooldown
    max_warnings=3, # 3 warnings before ban
    warning_timeout=300, # Warnings reset after 5 minutes
    signature_verification_enabled=True, # Enable cryptographic signature verification
    require_message_signatures=False, # Allow unsigned messages but log them
    propagation_fallback_enabled=True, # Enable propagation fallback after direct delivery fails
    propagation_node="your_propagation_node_hash_here", # Manual propagation node (optional)
    autopeer_propagation=True, # Auto-discover propagation nodes (optional)
    autopeer_maxdepth=4, # Max hops for auto-peering (default: 4)
    enable_propagation_node=False, # Run as propagation node (default: False)
    message_storage_limit_mb=500, # Storage limit in MB for propagation node (default: 500)
    direct_delivery_retries=3, # Number of direct delivery attempts before falling back to propagation
    landlock_enabled=True, # Linux Landlock LSM sandbox for the bot process (default)
    external_cogs_sandbox_enabled=True, # Sandbox external script cogs on Linux
    external_cogs_sandbox_type="auto", # auto, landlock, bwrap, firejail, or none
)

# Dynamically load all cogs
load_cogs_from_directory(bot)

@bot.command(name="ping", description="Test if bot is responsive")
def ping(ctx):
    ctx.reply("Pong!")

# Admin Only Command
@bot.command(name="echo", description="Echo a message", admin_only=True)
def echo(ctx, message: str):
    ctx.reply(message)

bot.run()
```

## RRC (Reticulum Relay Chat)

Bots can join [RRC](https://rrc.kc1awv.net/) hubs as ordinary clients over RNS Links with CBOR envelopes:

```python
from lxmfy import LXMFBot, RRCMessage

bot = LXMFBot(
    name="RoomBot",
    rrc_enabled=True,
    rrc_hubs=["your_rrc_hub_destination_hash"],
    rrc_rooms=["lobby"],
    rrc_nick="RoomBot",
)

@bot.on_rrc
def on_rrc(event, client, payload):
    if event == "msg" and isinstance(payload, RRCMessage) and payload.mention:
        client.send_message(payload.room, f"Heard you, {payload.nick}")

bot.run()
```

Or connect at runtime with `bot.connect_rrc(hub_hash, rooms=["lobby"])`.

Hub sessions persist across restarts by default (`rrc_persist_sessions=True`). Outgoing LXMF messages are also persisted by default (`message_persistence_enabled=True`) so a crash mid-queue does not drop them. The outbound queue is bounded (`message_queue_size`, default 50) and drops the oldest message when full.

## Propagation Node Configuration

LXMFy supports three modes for propagation node usage:

### 1. Manual Configuration

Set a specific propagation node by hash:

```python
bot = LXMFBot(
    name="MyBot",
    propagation_fallback_enabled=True,
    propagation_node="your_propagation_node_hash_here",  # Manual node configuration
    direct_delivery_retries=3,
)
```

### 2. Automatic Discovery (Auto-Peering)

Let the bot automatically discover and use propagation nodes from network announces:

```python
bot = LXMFBot(
    name="MyBot",
    propagation_fallback_enabled=True,
    autopeer_propagation=True,  # Enable automatic discovery
    autopeer_maxdepth=4,  # Maximum hop distance for auto-peering (default: 4)
)
```

The bot will listen for propagation node announces and automatically peer with suitable nodes within the configured hop depth.

### 3. Run as Propagation Node

Your bot can act as a propagation node itself to store and forward messages:

```python
bot = LXMFBot(
    name="MyPropagationBot",
    enable_propagation_node=True,  # Enable propagation node mode
    message_storage_limit_mb=500,  # Limit storage to 500 MB (default)
)
```

When running as a propagation node, the bot will store messages for offline users and forward them when the recipients come online. The `message_storage_limit_mb` prevents the bot from consuming unlimited disk space. Set to 0 for unlimited storage (not recommended).

### Querying Propagation Status

You can check the current propagation configuration and discovered nodes:

```python
status = bot.get_propagation_node_status()
print(f"Current outbound node: {status['current_outbound_node']}")
print(f"Discovered peers: {status['discovered_peers']}")
```

### Dynamically Setting Propagation Node

You can change the propagation node at runtime:

```python
bot.set_propagation_node("new_propagation_node_hash")
```

### Managing Storage Limits

When running as a propagation node, you can query and adjust storage limits:

```python
# Get current storage statistics
stats = bot.get_propagation_storage_stats()
print(f"Storage used: {stats['storage_size_mb']:.2f} MB")
print(f"Storage limit: {stats['storage_limit_mb']} MB")
print(f"Utilization: {stats['utilization_percent']:.1f}%")
print(f"Messages stored: {stats['message_count']}")

# Change storage limit at runtime
bot.set_message_storage_limit(megabytes=1000)  # Set to 1 GB
```

### Important Notes

- Without configuring propagation (manual, auto-peer, or running as a node), messages requiring propagation will fail
- You can combine modes: e.g., set a manual node AND enable auto-peering as backup
- When running as a propagation node, your bot can still send and receive messages normally
- Auto-peering respects the `autopeer_maxdepth` setting to avoid connecting to distant nodes

## Security & Sandboxing

On Linux kernels with Landlock support (5.13+), LXMFy can restrict filesystem access for the bot process and for external script cogs.

### Bot process sandbox

When `landlock_enabled=True` (default), the bot applies a Landlock LSM sandbox after startup. System paths are read-only; bot storage, config, cogs, Reticulum config, and temp directories remain writable.

```python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
print(status)
```

Environment overrides:

- `LXMFY_LANDLOCK=0` — disable Landlock
- `LXMFY_LANDLOCK=1` — force an attempt on Linux
- unset — follow `landlock_enabled` and kernel auto-detection

### External script cog sandbox

Executable cogs in `cogs/` can run in a restricted environment when `external_cogs_sandbox_enabled=True` (default). Set `external_cogs_sandbox_type` to:

- `auto` (default) — prefer Landlock, then `bwrap`, then `firejail`
- `landlock` — Landlock-only via `preexec_fn`
- `bwrap` — bubblewrap read-only bind sandbox
- `firejail` — firejail private profile with no network
- `none` — no subprocess sandbox

See the [docs](https://lxmfy.quad4.io) for full configuration details.

## Development

- Python 3.11+
- [Poetry](https://python-poetry.org/)

```bash
poetry install
poetry run lxmfy run echo
```

Common Makefile targets:

```bash
make lint       # ruff check
make typecheck  # pyright lxmfy
make test       # pytest
make ci         # lint, typecheck, security check, test, build
```

## Contributing

For now send ideas and issues to LXMF: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

## License

[0BSD](LICENSE)
