# Quick Start

## Prerequisites

- Python 3.11+
- Reticulum Network Stack (`pip install rns`, version 1.5.4+)
- LXMF (`pip install lxmf`, version 1.1.1+; installed automatically with
  LXMFy)
- CBOR (`cborx`, installed automatically, required for RRC)

=== "PyPI"

    ``` bash
    pip install lxmfy
    ```

=== "Source"

    ``` bash
    git clone https://github.com/Quad4-Software/LXMFy
    cd LXMFy
    poetry install
    ```

## Creating Your First Bot (Using the CLI)

Use the LXMFy CLI to scaffold a project. Two ways:

- `lxmfy init` asks a few questions (name, template, storage, prefix,
  admins) and writes a ready-to-run project directory.
- `lxmfy create` writes a single bot file with defaults, no questions.

This walkthrough uses `lxmfy create`.

1.  **Open your terminal** in the directory where you want to create
    your bot project.

2.  **Run the create command:**

    ``` bash
    lxmfy create my_first_bot
    ```

    This command will generate the following files:

    - `my_first_bot.py`: Your main bot file, configured with sensible
      defaults.
    - `cogs/`: A directory for bot extensions (cogs).
    - `cogs/__init__.py`: Makes the `cogs` directory a Python package.
    - `cogs/basic.py`: An example cog with simple "hello" and "about"
      commands.
    - `data/`: A directory where the bot will store its data (using JSON
      by default).
    - `config/`: A directory where the bot stores its identity and
      announce status.

3.  **Review the `my_first_bot.py` file:**

    ``` python
    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="my_first_bot",  # Bot name used in announces/identity
        announce=600,         # Announce interval in seconds (10 minutes)
        announce_immediately=True, # Announce on first run?
        admins=set(),         # Set of admin LXMF address hashes
        hot_reloading=False,  # Enable/disable hot reloading of cogs
        rate_limit=5,         # Max messages per minute per user
        cooldown=60,          # Cooldown period in seconds for rate limit
        max_warnings=3,       # Warnings before ban for spam
        warning_timeout=300,  # Time (seconds) before warnings reset
        command_prefix="/",   # Prefix for commands (e.g., /hello)
        cogs_dir="cogs",      # Directory to load cogs from
        cogs_enabled=True,    # Enable/disable loading cogs
        permissions_enabled=False, # Enable/disable the role-based permission system
        storage_type="json",  # Storage backend ("json", "sqlite", "msgpack", or "memory")
        storage_path="data",  # Path for storage files/database
        first_message_enabled=True, # Enable special handling for first messages
        event_logging_enabled=True, # Log events to storage?
        max_logged_events=1000,   # Max events to keep in log
        event_middleware_enabled=True, # Enable event middleware?
        announce_enabled=True,   # Enable/disable network announces
        signature_verification_enabled=False, # Enable/disable cryptographic signature verification
        require_message_signatures=False     # Require all messages to be signed
    )

    # To add an admin, find your LXMF address hash and add it here:
    # bot.config.admins.add("your_lxmf_hash_here")
    # bot.admins = bot.config.admins # Ensure the running instance knows

    # Example of preparing an LXMF icon field (optional)
    # from lxmfy import IconAppearance, pack_icon_appearance_field
    # try:
    #     icon_data = IconAppearance(icon_name="emoji_objects", fg_color=b'\xFF\xA5\x00', bg_color=b'\x8B\x45\x13') # Orange on Brown
    #     bot.icon_field = pack_icon_appearance_field(icon_data) # Store for use in send/reply
    # except Exception as e:
    #     print(f"Could not prepare icon field: {e}")
    #     bot.icon_field = None

    if __name__ == "__main__":
        print(f"Starting bot: {bot.config.name}")
        print(f"Bot LXMF Address: {bot.local.hash}") # Prints the bot's address
        bot.run()
    ```

4.  **(Optional) Add Your Admin Hash:**

    - Find your LXMF address hash (e.g., from your Reticulum client like
      Sideband or NomadNet).
    - Uncomment and edit the `bot.config.admins.add(...)` line in
      `my_first_bot.py`, replacing `"your_lxmf_hash_here"` with your
      actual hash.

5.  **Run Your Bot:**

    ``` bash
    python my_first_bot.py
    ```

    Your bot will start, print its LXMF address, potentially send an
    announce message over the Reticulum network, and begin listening for
    messages.

## Interacting With Your Bot

1.  **Send a message** to the bot's LXMF address from your client.
2.  **Try the example command:** Send `/hello` to the bot. It should
    reply with "Hello `<your_hash>`!". If you uncommented the icon
    example above, this reply might also carry an icon.
3.  **Try the help command:** Send `/help`.

If nothing arrives, run `lxmfy debug` from the project directory. It
checks the Reticulum config, interfaces, identity, and send pipeline,
and saves a redacted report you can share when asking for help.

## What to configure next

**Message handlers**

- `@bot.on_first_message()` for the first message from each sender
- `@bot.on_message()` for all messages before command processing

**Delivery**

- `direct_delivery_retries` in `LXMFBot(...)` retries direct delivery
  before propagation fallback
- `propagation_node` (or `bot.set_propagation_node(...)`) selects a
  specific LXMF propagation node
- Outgoing queue persistence defaults on
  (`message_persistence_enabled=True`) with a bounded queue
  (`message_queue_size`)

**Reticulum Relay Chat (RRC)**

- Join hubs with `rrc_enabled=True` or the `rrc` template
- Use the same Reticulum config as MeshChatX or your hub
  (`reticulum_config_dir` or `LXMFY_RETICULUM_CONFIG_DIR`, typically
  `~/.reticulum`)
- See [Creating Bots](creating-bots.md#reticulum-relay-chat-rrc) for
  room bots and hub discovery

**Security**

- `signature_verification_enabled=True` checks LXMF signature validation
  results
- `require_message_signatures=True` rejects unsigned or invalid messages
- On Linux, `landlock_enabled=True` (default) applies a Landlock LSM
  filesystem sandbox. Override with `LXMFY_LANDLOCK=0` or
  `LXMFY_LANDLOCK=1`
- External script cogs can use Landlock, bubblewrap, or firejail via
  `external_cogs_sandbox_type`
- LXMF signs outbound messages. LXMFy enforces the verification policy
  and optional sandboxing

**Development**

- `make typecheck` runs `pyright lxmfy`
- `make ci` runs lint, typecheck, security check, tests, and build

See [Creating Bots](creating-bots.md) and [API
Reference](api-reference.md) for command registration, cogs, and API
details.
