Core Components
================

LXMFBot
--------

The main bot class that handles message routing, command processing, and bot lifecycle management.

.. code-block:: python

    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="MyBot",
        announce=600,
        announce_immediately=True,
        admins=set(),
        hot_reloading=False,
        rate_limit=5,
        cooldown=60,
        max_warnings=3,
        warning_timeout=300,
        command_prefix="/",
        cogs_dir="cogs",
        cogs_enabled=True,
        permissions_enabled=False,
        storage_type="json", # "json", "sqlite", or "memory"
        storage_path="data",
        first_message_enabled=True,
        event_logging_enabled=True,
        max_logged_events=1000,
        event_middleware_enabled=True,
        announce_enabled=True,
        signature_verification_enabled=False,
        require_message_signatures=False,
        identity_pinning_enabled=False,
        message_persistence_enabled=False,
        dynamic_cogs_enabled=True,
        external_cogs_enabled=True,
        external_cogs_sandbox_enabled=True,
        external_cogs_sandbox_type="auto",
        external_cogs_timeout=30,
        nlp_enabled=False,
        nlp_threshold=0.5,
        link_support_enabled=False
    )

Key Methods
^^^^^^^^^^^

- :code:`run(delay=10)`: Start the bot's main loop
- :code:`send(destination, message, title="Reply", lxmf_fields=None, stamp_cost=None, opportunistic=None)`: Send a message to a destination, optionally with custom LXMF fields, stamp cost override, and opportunistic sending (tries direct, falls back to propagation immediately if configured).
- :code:`send_with_attachment(destination, message, attachment, title="Reply", stamp_cost=None, opportunistic=None)`: Send a message with an attachment
- :code:`command(name, description="No description provided", admin_only=False, threaded=False)`: Decorator for registering commands. Set :code:`threaded=True` to run the command's callback in a separate thread. Commands support type-hinted arguments for automatic conversion.
- :code:`intent(name, examples)`: Decorator for registering NLP intent handlers.
- :code:`nlp.export_model()`: Export trained NLP model data.
- :code:`nlp.import_model(model_data)`: Import previously exported NLP model data.
- :code:`request_link(destination_hash, callback=None, app_name="lxmf", *aspects)`: Request an RNS link to a destination. Allows custom :code:`app_name` and :code:`aspects` (defaults to "lxmf" and "delivery").
- :code:`on_link(callback)`: Register a handler for incoming RNS links.
- :code:`load_extension(name)`: Load a cog extension module by name (e.g., "cogs.utility").
- :code:`reload_extension(name)`: Reload a cog extension module.
- :code:`add_cog(cog_instance)`: Add a cog class instance to the bot.
- :code:`remove_cog(cog_name)`: Remove a cog from the bot by its class name.
- :code:`on_first_message()`: Decorator for handling first messages from users
- :code:`on_message()`: Decorator for handling all messages (called before command processing)
- :code:`validate()`: Run validation checks on the bot configuration

Storage
-------

The framework provides three storage backends:

JSONStorage
^^^^^^^^^^^

.. code-block:: python

    from lxmfy import JSONStorage

    storage = JSONStorage("data")

SQLiteStorage
^^^^^^^^^^^^^

.. code-block:: python

    from lxmfy import SQLiteStorage

    storage = SQLiteStorage("data/bot.db")

MemoryStorage
^^^^^^^^^^^^^

.. code-block:: python

    from lxmfy.storage import MemoryStorage

    storage = MemoryStorage() # Entirely in-memory

Commands
--------

Command registration and handling:

.. code-block:: python

    @bot.command(name="hello", description="Says hello")
    def hello(ctx):
        ctx.reply(f"Hello {ctx.sender}!")

Type-Hinted Arguments
^^^^^^^^^^^^^^^^^^^^^

Commands automatically parse and convert arguments based on type hints in the callback function.

.. code-block:: python

    @bot.command(name="add", description="Adds two numbers")
    def add(ctx, a: int, b: int):
        result = a + b
        ctx.reply(f"The result is {result}")

Help System
-----------

The framework includes an interactive help generator that provides beautiful, categorized help menus based on Cog and Command metadata.

.. code-block:: python

    # The help command is automatically registered.
    # Users can use '/help' or '/help <command>'

Threaded Commands
^^^^^^^^^^^^^^^^^

For long-running or blocking operations that do not interact with the Reticulum Network Stack directly, you can run commands in a separate thread to keep the bot responsive.

.. code-block:: python

    import time

    @bot.command(name="long_task", description="Performs a long-running task in a separate thread", threaded=True)
    def long_task_command(ctx):
        ctx.reply("Starting a long task... please wait.")
        time.sleep(10) # This runs in a separate thread
        ctx.reply("Long task completed!")

**Important:** Functions marked as :code:`threaded=True` **must not** directly interact with the Reticulum Network Stack (RNS) or any components that rely on :code:`lxmfy.transport.py`, as these are generally not thread-safe. Use :code:`ctx.reply()` for sending messages back to the user from within a threaded command.

Events
------

Event system for handling various bot events:

.. code-block:: python

    @bot.events.on("message_received", EventPriority.HIGHEST)
    def handle_message(event):
        # Handle message event
        pass

Testing
-------

Project tests include reliability and stress scenarios in the repository test suite.
Use the repository's test runner to execute them.

Advanced Reliability Suite
^^^^^^^^^^^^^^^^^^^^^^^^^^

The framework includes an extensive suite of automated tests for harsh environments:

- **Manifold Testing**: Validates the mathematical topology of NLP intent vector space.
- **Chaos Engineering**: Simulates bit-rot, SD card failure, and storage corruption.
- **Temporal Drift**: Verifies resilience against system clock jumps (±1 year).
- **Leak Detection**: Long-term tracking of memory, file descriptors, and threads.

Permissions
-----------

Permission system for controlling access to bot features:

.. code-block:: python

    from lxmfy import DefaultPerms

    @bot.command(name="admin", description="Admin command", admin_only=True)
    def admin_command(ctx):
        if ctx.is_admin:
            ctx.reply("Admin command executed")

Middleware
----------

Middleware system for processing messages and events:

.. code-block:: python

    @bot.middleware.register(MiddlewareType.PRE_COMMAND)
    def pre_command_middleware(ctx):
        # Process before command execution
        pass

Attachments
-----------

Support for sending files, images, and audio:

.. code-block:: python

    from lxmfy import Attachment, AttachmentType

    attachment = Attachment(
        type=AttachmentType.IMAGE,
        name="image.jpg",
        data=image_data,
        format="jpg"
    )
    bot.send_with_attachment(destination, "Here's an image", attachment)

Icon Appearance (LXMF Field)
-----------------------------

You can set a custom icon for your bot that compliant LXMF clients can display. This uses the :code:`LXMF.FIELD_ICON_APPEARANCE`.

.. code-block:: python

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

Scheduler
---------

Task scheduling system:

.. code-block:: python

    @bot.scheduler.schedule(name="daily_task", cron_expr="0 0 * * *")
    def daily_task():
        # Run daily at midnight
        pass

Signatures
----------

LXMFy provides configuration options for LXMF's built-in cryptographic message signing and verification:

.. code-block:: python

    from lxmfy import LXMFBot

    bot = LXMFBot(
        name="SecureBot",
        signature_verification_enabled=True,  # Enable signature checks
        require_message_signatures=False      # Set to True to reject unsigned messages
    )

**Important:** LXMF automatically handles all cryptographic signing and verification using RNS identities. LXMFy's :code:`SignatureManager` is a configuration layer that:

- Controls whether to enforce signature verification
- Determines policy for unsigned messages (accept or reject)
- Integrates with the permission system (e.g., bypass verification for trusted users)

The actual cryptographic operations are performed by LXMF/RNS, not by LXMFy.

Identity Pinning
^^^^^^^^^^^^^^^^

LXMFy supports optional identity pinning to prevent impersonation if an identity is rotated or compromised. When enabled, the bot "pins" an LXMF address to its first-seen public key.

.. code-block:: python

    bot = LXMFBot(
        identity_pinning_enabled=True
    )

SignatureManager Methods
^^^^^^^^^^^^^^^^^^^^^^^^

The :code:`SignatureManager` is available as :code:`bot.signature_manager` when :code:`signature_verification_enabled=True`:

- :code:`should_verify_message(sender)`: Determine if a message from the given sender should be verified
- :code:`handle_unsigned_message(sender, message_hash)`: Handle messages that lack valid signatures based on policy

How LXMF Signatures Work
^^^^^^^^^^^^^^^^^^^^^^^^^

LXMF automatically signs all outgoing messages using the sender's RNS identity during the :code:`pack()` operation. When messages are received, LXMF validates signatures and provides:

- :code:`message.signature_validated`: Boolean indicating if the signature is valid
- :code:`message.unverified_reason`: Reason code if validation failed (e.g., :code:`SIGNATURE_INVALID`, :code:`SOURCE_UNKNOWN`)

LXMFy uses these built-in LXMF properties to enforce your bot's signature policy.

Message Delivery
----------------

LXMFy provides advanced message delivery features including propagation nodes and automatic retries:

Propagation Nodes
^^^^^^^^^^^^^^^^^

Send messages through specific propagation nodes for improved reliability on the Reticulum network:

.. code-block:: python

    # Configure the propagation node once at config/runtime level
    bot.set_propagation_node("<propagation_node_hash>")

    # Send using configured delivery behavior
    bot.send(
        destination_hash,
        "Message content"
    )

    # The propagation node hash should be a valid LXMF propagation node
    # on the Reticulum network

Automatic Retries
^^^^^^^^^^^^^^^^^

Configure automatic retry attempts for failed direct deliveries:

.. code-block:: python

    bot = LXMFBot(
        name="ReliableBot",
        direct_delivery_retries=5,  # Retry direct delivery up to 5 times
        propagation_fallback_enabled=True
    )

    bot.send(destination_hash, "Important message")

    # Default direct_delivery_retries is 3
    # Retry logic automatically handles delivery callbacks

The retry system tracks delivery attempts per destination and automatically retries failed deliveries. Successful deliveries reset the retry counter for that destination.

Message Persistence
^^^^^^^^^^^^^^^^^^^

Outgoing messages can be persisted to disk to ensure they are delivered even after a bot restart.

.. code-block:: python

    bot = LXMFBot(
        message_persistence_enabled=True
    )

Message Handlers
----------------

LXMFy provides decorators for handling different types of incoming messages:

First Message Handler
^^^^^^^^^^^^^^^^^^^^^

Handle the first message from each user:

.. code-block:: python

    @bot.on_first_message()
    def welcome_user(sender, message):
        content = message.content.decode("utf-8")
        bot.send(sender, f"Welcome! You said: {content}")
        return True  # Return True to stop further processing

General Message Handler
^^^^^^^^^^^^^^^^^^^^^^^

Handle all incoming messages before command processing:

.. code-block:: python

    @bot.on_message()
    def handle_all_messages(sender, message):
        content = message.content.decode("utf-8").strip()
        
        # Custom logic here
        if content.startswith("echo:"):
            bot.send(sender, content[5:])
            return True  # Stop further processing
        
        return False  # Continue to command processing

Message handlers are called in this order:
1. First message handler (if this is the first message from this sender)
2. General message handlers (registered with :code:`on_message()`)
3. Command processing (if message starts with command prefix)

Templates
=========

The framework includes several ready-to-use bot templates:

EchoBot
-------

Simple echo bot that repeats messages:

.. code-block:: python

    from lxmfy.templates import EchoBot

    bot = EchoBot()
    bot.run()

NoteBot
-------

Note-taking bot with JSON storage:

.. code-block:: python

    from lxmfy.templates import NoteBot

    bot = NoteBot()
    bot.run()

ReminderBot
-----------

Reminder bot with SQLite storage:

.. code-block:: python

    from lxmfy.templates import ReminderBot

    bot = ReminderBot()
    bot.run()

CLI Tools
=========

The framework provides command-line tools for bot management:

.. code-block:: bash

    # Create a new bot
    lxmfy create mybot

    # Create a bot from template
    lxmfy create --template echo mybot

    # Run a template bot
    lxmfy run echo

    # Test signature verification with a message
    lxmfy signatures test

    # Enable signature verification
    lxmfy signatures enable

    # Disable signature verification
    lxmfy signatures disable

Error Handling
==============

The framework provides comprehensive error handling:

.. code-block:: python

    try:
        bot.run()
    except KeyboardInterrupt:
        bot.cleanup()
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
