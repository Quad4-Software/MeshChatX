# LXMFy

Python framework for LXMF bots on the Reticulum Network.

[Docs](https://lxmfy.quad4.io)

## Features

| Category | Capabilities |
| :--- | :--- |
| Core | Interactive CLI, command prefixes, cron-style task scheduler, middleware and event systems |
| Connectivity | Direct delivery with propagation fallback, auto-peering, RNS links, opportunistic sending, RRC hub client |
| Security | Spam protection, role-based permissions, identity pinning, message signature policy, Landlock LSM filesystem sandbox on Linux |
| NLP | Local offline intent classification, type-hinted argument parsing |
| Extensions | Python cogs, external script cogs (Bash, Go, C, and others), subprocess sandboxing via Landlock, `bwrap`, or `firejail` |
| Storage | JSON, SQLite, and in-memory backends, crash-safe outgoing message persistence |
| Reliability | Stability and stress tests, chaos engineering hooks, resource leak checks |
| UX | Help on first message, auto-generated help menus, customizable bot icons, attachments |

## Installation

**Requirements:** Python 3.11+, [RNS](https://pypi.org/project/rns/) 1.5.4+, [LXMF](https://pypi.org/project/lxmf/) 1.1.1+, [cborx](https://pypi.org/project/cborx/) 0.2.5+ (pulled in with LXMFy).

### From PyPI

```bash
# pip
pip install lxmfy

# pipx
pipx install lxmfy
```

### From source

```bash
git clone https://github.com/Quad4-Software/LXMFy.git
cd LXMFy
poetry install
```

### Standalone zipapp

Each GitHub release ships a `lxmfy-x.y.z.pyz` with all dependencies bundled:

```bash
python3 lxmfy-2.0.4.pyz --help
```

## Usage

```bash
lxmfy
```

Create a bot project:

```bash
lxmfy create
```

Debug send and receive:

```bash
lxmfy debug
lxmfy debug --config ./config --output ./lxmfy-debug-report.txt
lxmfy debug probe <destination_hash> --request-path --wait 30
lxmfy debug send <destination_hash>
lxmfy debug receive
lxmfy debug compare <hash_a> <hash_b>
```

Doctor mode prints a verdict and next steps, then categorized checks (OS, shared vs owned instance, disk permissions, interfaces, announce, send pipeline / storage history, receive readiness). It saves a privacy-redacted `lxmfy-debug-*.txt` you can share. Colors turn off when stdout is not a TTY, when `NO_COLOR` is set, or when Windows VT is unavailable. Use `--no-color` or `NO_COLOR=1` for plain output.

## Docker

### Build and run

From the project root:

```bash
docker build -t lxmfy-test .
```

```bash
docker run -d \
    --name lxmfy-test-bot \
    -v $(pwd)/config:/bot/config \
    -v $(pwd)/.reticulum:/root/.reticulum \
    --restart unless-stopped \
    lxmfy-test
```

Host networking (AutoInterface):

```bash
docker run -d \
    --name lxmfy-test-bot \
    --network host \
    -v $(pwd)/config:/bot/config \
    -v $(pwd)/.reticulum:/root/.reticulum \
    --restart unless-stopped \
    lxmfy-test
```

### Build a wheel

```bash
docker build -f docker/Dockerfile.Build -t lxmfy-wheel-builder .
docker run --rm -v "$(pwd)/dist_output:/output" lxmfy-wheel-builder
```

That copies the built wheel into `./dist_output`.

## Example

The smallest working bot needs a name and one command:

```python
from lxmfy import LXMFBot

bot = LXMFBot("LXMFy Test Bot")


@bot.command("ping", description="Test if bot is responsive")
def ping(ctx):
    ctx.reply("Pong!")


@bot.command("echo", description="Echo a message", admin_only=True)
def echo(ctx, message: str):
    ctx.reply(message)


bot.run()
```

Everything else has defaults. Pass keyword arguments to `LXMFBot` to override them:

```python
bot = LXMFBot(
    "LXMFy Test Bot",
    announce=5400,  # Announce every hour, set to 0 to disable.
    announce_enabled=True,  # Set to False to disable all announces (both initial and periodic)
    announce_immediately=True,  # Set to False to disable initial announce
    admins=["your_lxmf_hash_here"],  # List of admin hashes.
    hot_reloading=True,  # Enable hot reloading.
    command_prefix="/",  # Set to None to process all messages as commands.
    cogs_dir="cogs",  # Specify cogs directory name.
    rate_limit=5,  # 5 messages per minute
    cooldown=5,  # 5 seconds cooldown
    max_warnings=3,  # 3 warnings before ban
    warning_timeout=300,  # Warnings reset after 5 minutes
    signature_verification_enabled=True,  # Enable cryptographic signature verification
    require_message_signatures=False,  # Allow unsigned messages but log them
    propagation_fallback_enabled=True,  # Enable propagation fallback after direct delivery fails
    propagation_node="your_propagation_node_hash_here",  # Manual propagation node (optional)
    autopeer_propagation=True,  # Auto-discover propagation nodes (optional)
    autopeer_maxdepth=4,  # Max hops for auto-peering (default: 4)
    enable_propagation_node=False,  # Run as propagation node (default: False)
    message_storage_limit_mb=500,  # Storage limit in MB for propagation node (default: 500)
    direct_delivery_retries=3,  # Number of direct delivery attempts before falling back to propagation
    landlock_enabled=True,  # Linux Landlock LSM sandbox for the bot process (default)
    external_cogs_sandbox_enabled=True,  # Sandbox external script cogs on Linux
    external_cogs_sandbox_type="auto",  # auto, landlock, bwrap, firejail, or none
)
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

LXMFy supports three modes for propagation node usage.

### Manual configuration

Set a specific propagation node by hash:

```python
bot = LXMFBot(
    name="MyBot",
    propagation_fallback_enabled=True,
    propagation_node="your_propagation_node_hash_here",
    direct_delivery_retries=3,
)
```

### Automatic discovery (auto-peering)

Discover propagation nodes from network announces:

```python
bot = LXMFBot(
    name="MyBot",
    propagation_fallback_enabled=True,
    autopeer_propagation=True,
    autopeer_maxdepth=4,
)
```

The bot peers with suitable nodes within `autopeer_maxdepth` hops.

### Run as a propagation node

Store and forward messages for offline recipients:

```python
bot = LXMFBot(
    name="MyPropagationBot",
    enable_propagation_node=True,
    message_storage_limit_mb=500,
)
```

`message_storage_limit_mb` caps disk use. Set to 0 for unlimited storage (not recommended).

### Querying propagation status

```python
status = bot.get_propagation_node_status()
print(f"Current outbound node: {status['current_outbound_node']}")
print(f"Discovered peers: {status['discovered_peers']}")
```

### Setting the propagation node at runtime

```python
bot.set_propagation_node("new_propagation_node_hash")
```

### Storage limits

```python
stats = bot.get_propagation_storage_stats()
print(f"Storage used: {stats['storage_size_mb']:.2f} MB")
print(f"Storage limit: {stats['storage_limit_mb']} MB")
print(f"Utilization: {stats['utilization_percent']:.1f}%")
print(f"Messages stored: {stats['message_count']}")

bot.set_message_storage_limit(megabytes=1000)
```

### Propagation notes

- Without manual config, auto-peering, or running as a node, messages that need propagation fail
- You can combine modes (manual node plus auto-peering as backup)
- A propagation-node bot still sends and receives normally
- Auto-peering respects `autopeer_maxdepth` so distant nodes are skipped

## Security and Sandboxing

On Linux kernels with Landlock support (5.13+), LXMFy can restrict filesystem access for the bot process and for external script cogs.

### Bot process sandbox

When `landlock_enabled=True` (default), the bot applies a Landlock LSM sandbox after startup. System paths are read-only. Bot storage, config, cogs, Reticulum config, and temp directories stay writable.

```python
bot = LXMFBot(
    name="SecureBot",
    landlock_enabled=True,
)

status = bot.get_landlock_status()
print(status)
```

Environment overrides:

- `LXMFY_LANDLOCK=0`: disable Landlock
- `LXMFY_LANDLOCK=1`: force an attempt on Linux
- unset: follow `landlock_enabled` and kernel auto-detection

### External script cog sandbox

Executable cogs in `cogs/` can run in a restricted environment when `external_cogs_sandbox_enabled=True` (default). Set `external_cogs_sandbox_type` to:

- `auto` (default): prefer Landlock, then `bwrap`, then `firejail`
- `landlock`: Landlock-only via `preexec_fn`
- `bwrap`: bubblewrap read-only bind sandbox
- `firejail`: firejail private profile with no network
- `none`: no subprocess sandbox

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

Send ideas and issues to LXMF: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

## License

[0BSD](LICENSE)
