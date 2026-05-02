Quick Start
===========

Prerequisites
-------------

*   Python 3.11+
*   Reticulum Network Stack (:code:`pip install rns`)
*   LXMFy (:code:`pip install lxmfy` or install from source)

Creating Your First Bot (Using the CLI)
----------------------------------------

The easiest way to start is using the LXMFy command-line tool.

1.  **Open your terminal** in the directory where you want to create your bot project.
2.  **Run the create command:**

    .. code-block:: bash

        lxmfy create my_first_bot

    This command will generate the following files:
    *   :code:`my_first_bot.py`: Your main bot file, configured with sensible defaults.
    *   :code:`cogs/`: A directory for bot extensions (cogs).
    *   :code:`cogs/__init__.py`: Makes the :code:`cogs` directory a Python package.
    *   :code:`cogs/basic.py`: An example cog with simple "hello" and "about" commands.
    *   :code:`data/`: A directory where the bot will store its data (using JSON by default).
    *   :code:`config/`: A directory where the bot stores its identity and announce status.

3.  **Review the :code:`my_first_bot.py` file:**

    .. code-block:: python

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
            storage_type="json",  # Storage backend ("json", "sqlite", or "memory")
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

4.  **(Optional) Add Your Admin Hash:**
    *   Find your LXMF address hash (e.g., from your Reticulum client like Sideband or NomadNet).
    *   Uncomment and edit the :code:`bot.config.admins.add(...)` line in :code:`my_first_bot.py`, replacing :code:`"your_lxmf_hash_here"` with your actual hash.

5.  **Run Your Bot:**

    .. code-block:: bash

        python my_first_bot.py

    Your bot will start, print its LXMF address, potentially send an announce message over the Reticulum network, and begin listening for messages.

Interacting With Your Bot
-------------------------

1.  **Send a message** to the bot's LXMF address from your client.
2.  **Try the example command:** Send :code:`/hello` to the bot. It should reply with "Hello :code:`<your_hash>`!".
    If you uncommented the icon example above, this reply might also carry an icon.
3.  **Try the help command:** Send :code:`/help`.

Advanced Features
-----------------

Once you're comfortable with the basics, explore these advanced features:

**Message Handlers:**

*   Use :code:`@bot.on_first_message()` to welcome new users
*   Use :code:`@bot.on_message()` to handle all messages before command processing

**Reliable Delivery:**

*   Configure :code:`direct_delivery_retries` in :code:`LXMFBot(...)` for automatic retry before propagation fallback
*   Configure :code:`propagation_node` in bot config (or use :code:`bot.set_propagation_node(...)`) to route through a specific LXMF propagation node

**Security:**

*   Enable :code:`signature_verification_enabled=True` to enforce LXMF's built-in signature verification
*   Set :code:`require_message_signatures=True` to reject unsigned or invalid messages
*   Note: LXMF automatically signs all messages; LXMFy just enforces verification policy

See the `Creating Bots <creating-bots.html>`_ guide and `API Reference <api-reference.html>`_ for detailed information on these features.

Next Steps
----------

*   Explore the `Creating Bots <creating-bots.html>`_ guide for more details on adding commands, using cogs, and different bot types.
*   Check the `API Reference <api-reference.html>`_ for detailed information on framework components.
