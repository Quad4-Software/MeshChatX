Creating Bots
=============

Basic Structure
---------------

A minimal LXMFy bot involves:

1.  Importing :code:`LXMFBot`.
2.  Instantiating :code:`LXMFBot` with desired configuration.
3.  Defining commands or event handlers.
4.  Running the bot using :code:`bot.run()`.

.. code-block:: python

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

Using Templates
---------------

LXMFy provides several templates for common bot types. You can use the CLI to generate a bot file based on a template.

.. code-block:: bash

    # Create an echo bot
    lxmfy create --template echo my_echo_bot

    # Create a reminder bot (uses SQLite storage)
    lxmfy create --template reminder my_reminder_bot

    # Create a note-taking bot (uses JSON storage)
    lxmfy create --template note my_note_bot

    # Create a cog test bot (tests cog loading features)
    lxmfy create --template cogtest my_cog_test_bot

Running these commands creates a Python file (e.g., :code:`my_echo_bot.py`) that imports and runs the chosen template. You can then modify the generated file or the template code itself (:code:`lxmfy/templates/...`).

**Example generated file (:code:`my_cog_test_bot.py`):**

.. code-block:: python

    from lxmfy.templates import CogTestBot

    if __name__ == "__main__":
        bot = CogTestBot() # Creates an instance of the CogTestBot template
        # You can optionally override the default name:
        # bot.bot.name = "My Cog Test Bot"
        bot.run()

Bot Configuration
-----------------

When creating an :code:`LXMFBot` instance, you can pass various keyword arguments to configure its behavior. See the :code:`BotConfig` section in the `API Reference <api-reference.html>`_ or the `Quick Start Guide <quick-start.html>`_ for a list of common options.

.. code-block:: python

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

Setting a Bot Icon (LXMF Field)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can give your bot a custom icon that appears in compatible LXMF clients. This uses the :code:`LXMF.FIELD_ICON_APPEARANCE` and can be set when sending messages.

First, ensure you have the necessary imports:

.. code-block:: python

    from lxmfy import IconAppearance, pack_icon_appearance_field

Then, you can define and use the icon:

.. code-block:: python

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

This :code:`self.bot_icon_field` can be pre-calculated and reused for all messages sent by the bot.

Using Cogs (Extensions)
-----------------------

Cogs allow you to organize your commands and event listeners into separate files (modules), keeping your main bot file cleaner.

1.  **Create a :code:`cogs` directory** (or whatever you set :code:`cogs_dir` to in :code:`BotConfig`).
2.  **Create Python files** inside the :code:`cogs` directory (e.g., :code:`utility.py`).
3.  **Define a class** that inherits from :code:`lxmfy.Cog` (optional but good practice) or is just a standard class.
4.  **Define commands** as methods within the class using the :code:`@Command` decorator.
5.  **Create a :code:`setup(bot)` function** in the cog file, which LXMFy will call to register the cog.

**Example (:code:`cogs/utility.py`):**

.. code-block:: python

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

**Main Bot File (:code:`my_bot.py`):**

.. code-block:: python

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

When the bot starts, it will automatically find :code:`utility.py`, call its :code:`setup` function, which creates an instance of :code:`UtilityCog` and registers it using :code:`bot.add_cog()`. The commands defined in the cog (:code:`uptime`, :code:`info`) will then be available.

External Script Cogs (Multi-Language Support)
---------------------------------------------

You can also write bot extensions in languages other than Python (e.g., Bash, Ruby, Perl, Go, C) using External Script Cogs.

1.  **Create an executable script** in your :code:`cogs` directory.
2.  **Add a shebang** at the top of the script (e.g., :code:`#!/bin/bash`).
3.  **Ensure the script is executable** (:code:`chmod +x your_script`).

When the bot starts, it will automatically register any executable file in the :code:`cogs` directory (that doesn't end in :code:`.py`) as a bot command.

**Argument Protocol:**

-   :code:`$1`: Sender's LXMF hash.
-   :code:`$2`: Full message content.
-   :code:`$3`, :code:`$4`, ...: Individual command arguments.

**Environment Variables:**

-   :code:`LXMFY_SENDER`: The sender's identity hash.
-   :code:`LXMFY_CONTENT`: The full message content.
-   :code:`LXMFY_HAS_ADMIN`: :code:`true` or :code:`false` depending on the sender's admin status.

**Example Bash Cog (:code:`cogs/greet.sh`):**

.. code-block:: bash

    #!/bin/bash
    echo "Hello from Bash! You sent: $2"

When a user sends :code:`/greet hello`, the bot will execute this script and reply with its stdout: :code:`Hello from Bash! You sent: /greet hello`.

Sovereign NLP (Local Intent Classification)
-------------------------------------------

LXMFy includes a built-in, lightweight NLP engine for intent classification. This allows your bot to understand the "intent" of a message even if it doesn't match a command exactly.

1.  **Enable NLP** in your bot configuration: :code:`nlp_enabled=True`.
2.  **Define intents** using the :code:`@bot.intent` decorator.

.. code-block:: python

    @bot.intent("help", examples=["how do I use this?", "show me commands", "help me please"])
    def help_intent(msg):
        msg.reply("I can help! Try typing /help to see a list of commands.")

The NLP engine uses mathematical vector similarity (TF-IDF and Cosine Similarity) to match incoming text against your example phrases. This processing happens entirely locally on your machine, ensuring full privacy.

**Persistence and Extensibility:**

For larger bots, you can export and import the trained intent model to avoid retraining on every startup:

.. code-block:: python

    # Export the model
    model_data = bot.nlp.export_model()
    # Save model_data to a file or database
    
    # Later, import it back
    bot.nlp.import_model(model_data)

RNS Link Support
----------------

Bots can now establish and respond to direct RNS Links. This is useful for stateful, streaming, or high-bandwidth communication that goes beyond simple message packets.

1.  **Enable Link Support** in configuration: :code:`link_support_enabled=True`.
2.  **Request a link**: :code:`bot.request_link(destination_hash)`. You can also specify a custom app name and aspects: :code:`bot.request_link(dest, callback, "my_app", "aspect1")`.
3.  **Handle incoming links**: Register a callback with :code:`bot.on_link(handler)`.

.. code-block:: python

    def handle_link(link):
        print(f"Link established with {RNS.hexrep(link.destination.hash)}")
        # You can now use the link for direct RNS communication

    bot.on_link(handle_link)

**Safety & Sandboxing:**

-   **Timeouts:** External cogs have a default timeout (30s) to prevent hanging. This is configurable via :code:`external_cogs_timeout`.
-   **Threading:** All external cogs run in separate threads and do not block the bot.
-   **Sandboxing (Linux only):** If :code:`bubblewrap` (:code:`bwrap`) or :code:`firejail` is installed, the bot can automatically run scripts in a restricted, read-only sandbox. This is enabled by default via :code:`external_cogs_sandbox_enabled`.

Handling Messages
-----------------

LXMFy provides several ways to handle incoming messages at different stages of processing.

First Message Handler
^^^^^^^^^^^^^^^^^^^^^

Handle the first message from each new user (useful for welcome messages):

.. code-block:: python

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

General Message Handler
^^^^^^^^^^^^^^^^^^^^^^^

Handle all incoming messages before command processing:

.. code-block:: python

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

Message Handler Processing Order:

1. **First Message Handler** (if :code:`first_message_enabled=True` and this is first message from sender)
2. **General Message Handlers** (registered with :code:`@bot.on_message()`)
3. **Command Processing** (if message matches a registered command)

Handlers can return :code:`True` to stop further processing or :code:`False` to continue to the next stage.

Handling Events
---------------

You can register handlers for various bot events using the :code:`@bot.events.on()` decorator.

.. code-block:: python

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

See :code:`lxmfy/events.py` for more details on the :code:`Event` structure and priorities.

Storage
-------

LXMFy provides JSON, SQLite, and In-Memory storage backends.

*   **JSON:** Simple, human-readable. Good for small datasets. Configure with :code:`storage_type="json"` and :code:`storage_path="your_data_dir"`.
*   **SQLite:** More efficient for larger datasets or frequent writes. Configure with :code:`storage_type="sqlite"` and :code:`storage_path="your_db_file.db"`.
*   **Memory:** Entirely in-RAM storage. State is lost on shutdown. Configure with :code:`storage_type="memory"`.

You can access the storage interface via :code:`bot.storage`:

.. code-block:: python

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

See :code:`lxmfy/storage.py` and the API reference for more details.

Permissions
-----------

LXMFy includes an optional role-based permission system. Enable it with :code:`permissions_enabled=True` during :code:`LXMFBot` initialization.

*   **Roles:** Define roles with specific permissions (e.g., :code:`DefaultPerms.MANAGE_USERS`).
*   **Permissions:** Granular flags defined in :code:`DefaultPerms` (e.g., :code:`USE_COMMANDS`, :code:`BYPASS_SPAM`).
*   **Assignment:** Assign roles to user hashes.

See :code:`lxmfy/permissions.py`, the API reference, and potentially example cogs (if any are created) for usage details.

Signature Verification
----------------------

LXMFy provides configuration for LXMF's built-in cryptographic message signing and verification. All LXMF messages are automatically signed by the LXMF/RNS stack - LXMFy simply allows you to enforce signature verification policies.

**Configuration:**

Enable signature verification in your bot configuration:

.. code-block:: python

    bot = LXMFBot(
        name="SecureBot",
        signature_verification_enabled=True,  # Enable signature checking
        require_message_signatures=False      # Set to True to reject unsigned messages
    )

**How It Works:**

LXMF automatically handles all cryptographic operations:

1. **Outgoing Messages:** LXMF automatically signs all messages using the sender's RNS identity during message packing.

2. **Incoming Messages:** LXMF automatically validates signatures using the sender's RNS identity and provides validation results.

3. **LXMFy's Role:** LXMFy checks LXMF's validation results and enforces your policy:

   - If :code:`signature_verification_enabled=False`: All messages are accepted (default)
   - If :code:`signature_verification_enabled=True` and :code:`require_message_signatures=False`: Messages are accepted but unsigned/invalid signatures are logged
   - If :code:`signature_verification_enabled=True` and :code:`require_message_signatures=True`: Unsigned or invalid messages are rejected

4. **Permission Integration:** Users with :code:`BYPASS_SPAM` permission can bypass signature verification requirements.

**CLI Management:**

You can manage signature verification settings using the CLI:

.. code-block:: bash

    # Test signature verification
    lxmfy signatures test

    # Enable signature verification
    lxmfy signatures enable

    # Disable signature verification
    lxmfy signatures disable

**Technical Details:**

LXMF uses Ed25519 signatures provided by the RNS cryptography system. Every LXMF message includes the sender's signature, which is validated against their known RNS identity. LXMFy simply reads LXMF's :code:`message.signature_validated` property and :code:`message.unverified_reason` to enforce your bot's security policy.

Advanced Message Delivery
--------------------------

LXMFy supports advanced message delivery options for improved reliability.

Using Propagation Nodes
^^^^^^^^^^^^^^^^^^^^^^^^

Send messages through specific LXMF propagation nodes:

.. code-block:: python

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

Propagation nodes are useful when direct delivery is not possible or when you want to ensure message delivery through the Reticulum mesh network.

Configuring Retries
^^^^^^^^^^^^^^^^^^^

Configure automatic retry attempts for failed message deliveries via bot config:

.. code-block:: python

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

The retry system:

- Automatically tracks delivery attempts per destination
- Retries failed direct deliveries up to :code:`direct_delivery_retries`
- Resets the retry counter on successful delivery
- Logs retry attempts and failures for debugging
