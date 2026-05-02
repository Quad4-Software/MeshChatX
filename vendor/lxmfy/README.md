# LXMFy

Easily create LXMF bots for the Reticulum Network with this extensible framework.

[Docs](https://lxmfy.quad4.io)

## Features

| Category | Key Capabilities |
| :--- | :--- |
| **Core** | Interactive CLI, Command Prefixes, Cron-style Task Scheduler, Middleware & Event Systems |
| **Connectivity** | Direct Delivery & Propagation Fallback, Auto-Peering, RNS Link Support, Opportunistic Sending |
| **Security** | Spam Protection, Role-based Permissions, Identity Pinning, Message Signing/Verification |
| **NLP** | Local NLP Intent Classification (Offline/Private), Type-hinted Argument Parsing |
| **Extensions** | Python Cogs, External Script Cogs (Bash, Go, C, etc.), Linux Sandboxing (`bwrap`/`firejail`) |
| **Storage** | Extensible Backends (JSON, SQLite, In-Memory), Message Persistence (Crash Recovery) |
| **Reliability** | Extensive Stability & Mathematical Stress Testing, Chaos Engineering, Resource Leak Detection |
| **UX** | Help on First Message, Auto-generated Help Menus, Customizable Bot Icons, Attachments |

## Installation

There are many ways to install LXMFy, you pick:

### From PyPI

```bash
# pip
pip install lxmfy

# pipx
pipx install lxmfy
```

### From Gitea Packages

```bash
# pip
pip install --index-url https://git.quad4.io/api/packages/LXMFy/pypi/simple/ --extra-index-url https://pypi.org/simple lxmfy

# pipx
pipx install --pip-args="--index-url https://git.quad4.io/api/packages/LXMFy/pypi/simple/ --extra-index-url https://pypi.org/simple" lxmfy
```

**Permanent Configuration:**

To avoid typing the index URLs every time, add them to your `pip.conf`:

```ini
# ~/.config/pip/pip.conf
[global]
index-url = https://git.quad4.io/api/packages/LXMFy/pypi/simple/
extra-index-url = https://pypi.org/simple
```

Then you can simply use:

```bash
pip install lxmfy
# or
pipx install lxmfy
```

### Git

```bash
pip install git+https://git.quad4.io/LXMFy/LXMFy.git
```

```bash
pipx install git+https://git.quad4.io/LXMFy/LXMFy.git
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

## Development

- poetry
- python 3.11 or higher

```
poetry install
poetry run lxmfy run echo
```

## Contributing

For now send ideas and issues to LXMF: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

## License

[0BSD](LICENSE)
