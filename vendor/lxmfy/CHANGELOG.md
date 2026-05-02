# Changelog

## [1.6.2] - 2026-04-15

### Features
- **Reticulum config directory**: Added `reticulum_config_dir` to `BotConfig` (and `LXMFY_RETICULUM_CONFIG_DIR`). `LXMFBot` passes this path to `RNS.Reticulum` for shared instance and auth state; when unset, behavior matches the previous default of using the bot config directory.
- **Announce display name**: Before each delivery announce, the bot refreshes the LXMF destination display name from the current `LXMFBot.name` / `BotConfig.name`, an optional `announce_display_name_file` under the config directory, or `bot_display_name.txt` when present. This keeps announce app_data aligned when the title changes on disk without restarting the process.
- **Public announce API**: Added `LXMFBot.announce_now(force=False)` for library callers; use `force=True` to bypass the on-disk announce interval throttle. The `name` property reads and writes `BotConfig.name` and updates the delivery destination when the router is up.

### Updates
- **Dependencies**: Updated RNS requirement to 1.1.5 and regenerated poetry.lock

## [1.6.1] - 2026-03-11

### Other Changes
- **License**: Switched from MIT to BSD-0-Clause.

## [1.6.0] - 2026-02-27

Updated dependencies:
- RNS to 1.1.3
- Cryptography to 46.0.5

## [1.5.0] - 2026-01-15

### Features
- **In-Memory Storage**: Added `MemoryStorage` backend. Bots can now run entirely in RAM (excluding RNS/LXMF internal state) by setting `storage_type="memory"`.
- **Reliability Suite**: Added a comprehensive suite of mathematical and reliability tests:
    - **Manifold Testing**: NLP vector space orthogonality verification.
    - **Chaos Engineering**: Storage fault injection and bit-rot simulation.
    - **Temporal Drift**: Clock skew resilience testing (±1 year jumps).
    - **Leak Detection**: Resource tracking for FDs, threads, and memory over long runs.
- **Message Persistence**: Added `message_persistence_enabled` to `BotConfig`. Outgoing messages in the queue are now persisted to storage and restored on startup (in case of a crash or unexpected restart).
- **Identity Pinning**: Added `identity_pinning_enabled` to `BotConfig`. An extra paranoid measure that remembers the full public key of a sender to protect against theoretical hash collisions.
- **Dynamic Cog Management**: Added `remove_cog()` and `reload_extension()` methods to `LXMFBot`, allowing for runtime loading and unloading of extensions.
- **Cross-Language Script Cogs**: Added support for non-Python cogs. Any executable file in the `cogs/` directory is now automatically registered as a bot command. Includes optional sandboxing via `bubblewrap` or `firejail` and mandatory timeouts/threading for safety.
- **NLP**: Integrated a very basic, lightweight, local intent classification engine (Tiny-NLP). Bots can now understand "intents" using mathematical vector similarity (TF-IDF/Cosine) instead of just exact string matches, all processed locally and offline without external APIs or dependencies.
- **RNS Link Support**: Bots can now request and respond to direct RNS Links, enabling stateful, link-oriented communication alongside standard LXMF messages.
- **Type-hinted Argument Parsing**: Bot commands now automatically parse and convert arguments based on type hints in the callback function signature.
- **Property-based Testing**: Integrated Hypothesis for extensive property-based testing of middleware, parsing, permissions, signatures, storage, and validation modules.

### Fixes
- **Identity Persistence in Test Mode**: Improved identity handling to allow persistence and recall of identities even when `test_mode` is enabled.

## [1.4.0] - 2026-01-05

### Features
- **Inbound stamp enforcement toggle**: Added `require_stamps` to `BotConfig`, wiring enforcement through `LXMRouter` initialization and propagation enablement.
- **Optional identity fetch for unknown senders**: `SignatureManager` can request unknown identities (`request_unknown_identities`) by issuing `RNS.Transport.request_path` when a message arrives from an unknown source.
- **Performance and memory stress tests**: Added `tests/test_performance.py` with throughput, signature verification, storage load, middleware stack, and long-run memory stability benchmarks.

### Fixes
- **Reticulum cleanup**: Ensure `LXMFBot.cleanup()` invokes `router.exit_handler()` and `RNS.Reticulum.exit_handler()` to prevent hanging background threads between tests.
- **Propagation config robustness**: Adjusted propagation tests to use test-mode/mocked routers and ensured storage limits are set correctly, stabilizing propagation-node coverage.
- **Signature path requests**: Corrected patch target for path requests on unknown identities in tests, aligning with `lxmfy.signatures` usage.

## [1.3.0] - 2026-01-04

### Features
- **Added version to lxmfy help output**

### Other Changes
- **Updated publish workflow to use twine for Gitea PyPI package registry**
- **Updated install commands in README with Gitea PyPI registry instructions**
- **Added SHA256 checksums for release assets (SHA256SUMS file and in release notes)**
- **Updated RNS to 1.1.0**

## [1.2.1] - 2025-11-30

### Fixes
- **Fix Gitea actions setting on project repo (forced pinned SHA actions broke stuff, oops)**

## [1.2.0] - 2025-11-30

### Features
- **Created dedicated colors module for CLI**

### Fixes
- **Fix interactive cli color support for Windows 10/11**

### Other Changes
- **Updated dependencies in poetry.lock (rns 1.0.4 and ruff 0.14.7)**
- **Moved from safety to bearer for security scanning (safety was no longer working)**
- **Updated rest of Gitea actions to use full-length commit SHAs for better supply chain security**

## [1.1.0] - 2025-11-21

### Features
- **Direct Delivery with retries & Propagation Net Fallback**
- **Configurable Stamp Cost for bots**

### Codebase Changes
- **Simplied codebase to just use poetry.** 
- **Numerous codebase cleanup and improvements.**

### Updates
- **Update LXMF to 0.9.3**
- **Update RNS to 1.0.3**

## [1.0.3] - 2025-11-03
### Patch
- **Updated dependencies**
  - Updated lxmf to 0.9.1 due to bug.

## [1.0.2] - 2025-11-03

### Patch
- **Updated dependencies**
  - Updated lxmf to 0.9.0
  - Updated rns to 1.0.1
  - Updated dependencies in poetry.lock

- **Project Structure Cleanup**
  - Moved docker files to docker directory
  - Updated Makefile and README with new paths.

## [1.0.1] - 2025-09-28

### Patch
- **Fixed Signature Canonicalization**
  - Fixed signature canonicalization to use the correct format
  - updated signature test to use the correct format

## [1.0.0] - 2025-09-27

### Major Features
- **Stable Release**: LXMFy reaches version 1.0.0 with full feature stability
- **Comprehensive Test Suite**: Added extensive test coverage
- **Code Quality Improvements**: Enhanced type hints, removed unused imports, and improved code consistency

### Testing & CI/CD
- Added pytest framework with comprehensive test suite
- Implemented Gitea Actions CI/CD pipeline with automated testing
- Updated DeepSource configuration to exclude test files from analysis
- Added pytest-related development dependencies

### Code Quality
- Refactored type hints across multiple files for better consistency
- Improved help text formatting in HelpFormatter class
- Removed unused imports and cleaned up code
- Updated staticmethod usage for better performance

### Dependencies & Configuration
- Updated project dependencies and configuration

## [0.8.0] - 2025-09-27

### Major Features
- **Cryptographic Message Signing & Verification**
  - Added `signature_verification_enabled` configuration option
  - Added `require_message_signatures` configuration option
  - Implemented `SignatureManager` class for cryptographic operations
  - Added automatic signing of outgoing messages when verification is enabled
  - Added verification of incoming message signatures
  - Custom LXMF field `FIELD_SIGNATURE = 0xFA` for storing signatures
  - CLI commands: `lxmfy signatures test/enable/disable`
  - Integration with permission system (bypass for privileged users)
  - Comprehensive validation and best practices checking

## [0.7.8] - 2025-09-13
- **Update Dependencies in poetry.lock**
- **Add Makefile**

## [0.7.7] - 2025-07-14

- **Docker Enhancements**
  - Added Arm64 docker support.
  - Updated docker build test and parameterized Python version in Dockerfile for easier updates.

- **Dependency Updates**
  - Updated RNS to `1.0.0` and LXMF to `0.8.0`.
  - Regenerated poetry.lock.

- **Codebase Cleanup**
  - General code cleanup and maintenance.

## [0.7.6] - 2025-07-05

- **New Feature: Threaded Commands**
  - Introduced `threaded=True` option for `@command` decorator.
  - Allows long-running command callbacks to execute in a separate thread, improving bot responsiveness.
  - Implemented `ThreadPoolExecutor` in `LXMFBot` for managing threaded tasks.
  - Updated `Command` class to support `threaded` attribute.
  - Updated `docs/api.md` and `docs/creating-bots.md` with usage and safety guidelines.

- **Dependency Updates**
  - dependency updates for general maintenance.
## [0.7.5] - 2025-06-22

- **Enhanced cog command loading system**
  - Improved add_cog method with robust error handling and command binding
  - Added proper filtering to skip private methods and non-command attributes
  - Enhanced command descriptor detection and binding logic
  - Better fallback handling for edge cases in command registration

- **New CogTest template**
  - Added comprehensive cog testing template for regression prevention
  - Includes test commands with various decorator types (@Command, admin-only)
  - Features status reporting command to verify cog loading success
  - Available via CLI: `lxmfy create --template cogtest` and `lxmfy run cogtest`
  - Can be used as both standalone template and loadable cog module

## [0.7.4] - 2025-06-22

- **Fix cog command loading issue**
  - Fixed Command.__get__ method to properly pass all parameters when binding instance methods
  - Resolves "'method' object has no attribute 'callback'" error when loading cog extensions
  - Commands in cogs now load correctly with all metadata preserved

## [0.7.3] - 2025-05-15

- **Update LXMF to 0.7.1**
- **Update RNS to 0.9.6**

## [0.7.2] - 2025-05-13

- **Update LXMF to 0.7.0**
- **Update dependencies**
- **Python 3.13 now required**

## [0.7.1] - 2025-05-09

- **Fixed workflow**

## [0.7.0] - 2025-05-09

- **Add LXMF fields support**
- **Update dependencies**
- **Update docs**

## [0.6.9] - 2025-05-07

- **Add opencontainers metadata**
- **Remove bot Scan (AST)**
- **Remove bot verification**
- **Update dependencies**
- **Performance fixes (Ruff PERF)**
- **cog loading validation and error handling**

## [0.6.8] - 2025-04-29

- **Update setup.py package name**
- **Add Dockerfile.Build**
- **CLI: Colors and Interactive**

## [0.6.7] - 2025-04-29

- **Fix Workflow**

## [0.6.6] - 2025-04-29

- **Fix Basic Tests**
- **Docstrings**
- **Code Cleanup**
- **Meme Bot Template**
- **Update dependencies**
- **Add ARMv7 and ARM64 Builds**
- **Remove Bandit**
- **Remove Meme Bot (Meme API no longer working)**
- **Remove Requests (Meme Bot dependency)**

## [0.6.5] - 2025-04-07

- **Fix Attachment System**
- **Add more storage error handling**

## [0.6.4] - 2025-04-06

- **Code refactoring for security and performance**

## [0.6.3] - 2025-04-06

- **Fix syntax errors**
- **Manual publish workflow**
- **Update Poetry.lock**

## [0.6.0] - 2025-04-06

- **Update lxmf to 0.6.3**
- **Update rns to 0.9.3**
- **Add docker-compose.yml file**
- **Run bot templates directly: lxmfy run echo**
- **Add basic tests**
- Fix linting errors
- **Add LXMF Attachment Support**

## [0.5.1] - 2025-02-14

- **Remove unused variables**
- **Fix version**

## [0.5.0] - 2025-02-14

- **Update config, cli and core**
  - Add missing values
  - Fix announce system

## [0.4.9] - 2025-02-14
- **Fix Announce System**
  - Add ability to disable announces on start.
  - Fix announcing interval

Bot configuration:

```python
    announce=600,  # Set the announce interval in seconds, set to 0 to disable periodic announces
    announce_enabled=True,  # Set to False to disable all announces (both initial and periodic)
```

- **Fix Duplicate Responses**

- **Update Dependencies**
  - Update LXMF from `0.6.1` to `0.6.2`
  - Regenerate poetry.lock

## [0.4.8] - 2025-01-25
- **Fix Storage System**
  - Serialization errors
  - SQLite3 Storage Backend

## [0.4.7] - 2025-01-25
- **Fix Storage System**
  - Serialization errors
  
- **Fix Event System**
  - Event handling of some attributes

## [0.4.6] - 2025-01-25

### Major Features
- **Middleware System**
  - Middleware system for processing messages and events
  - MiddlewareManager class for managing middleware
  - MiddlewareType enum for middleware types
  - MiddlewareContext class for passing data through middleware

- **Task Scheduler**
  - Task scheduler for scheduling tasks
  - TaskScheduler class for managing tasks
  - ScheduledTask class for representing scheduled tasks

- **Update lxmf to 0.6.1**

```python
from lxmfy import LXMFBot, MiddlewareType, TaskScheduler

bot = LXMFBot(name="MyBot")

# Add middleware
@bot.middleware.register(MiddlewareType.PRE_COMMAND)
def log_commands(ctx):
    print(f"Command received: {ctx.data}")
    return ctx.data

# Schedule task
@bot.scheduler.schedule("cleanup", "0 */2 * * *")  # Every 2 hours
def cleanup_task():
    print("Running cleanup...")
```

## [0.4.5] - 2025-01-20

### Major Features
- **Event System**
  - Event system for handling events and middleware
  - EventManager class for managing events and handlers
  - Event class for representing events
  - EventPriority enum for event priority levels
  - EventMiddleware for handling event middleware

```python
@bot.events.on("custom_event")
async def handle_custom_event(event):
    print(f"Custom event received: {event.data}")

# Dispatch custom event
await bot.events.dispatch(Event("custom_event", {"foo": "bar"}))
```

- **Update rns and lxmf**

## [0.4.4] - 2025-01-17

### Major Features
- **Bot Analysis**
  - Validate bot configuration and best practices
  - Analyze bot file and provide recommendations
  - Validate bot file syntax and structure
  - Check for common issues and suggest improvements

- **Update rns to 0.9.0**

  cli command: `lxmfy analyze bot.py`


## [0.4.3] - 2025-01-04

### Major Features
- **First Message Handler**
- **SQLite3 Storage Backend**
- **Simpler and Better Bot Templates**

Templates Added: EchoBot, ReminderBot, NoteBot
Templates Removed: FullBot

On First Message Handler:

```python

@bot.on_first_message()
def welcome_message(sender, message):
    # Custom welcome message handler
    bot.send(sender, "Welcome to the bot! Type /help to see available commands.")
    return True  # Return True to indicate message was handled
```

SQLite3 Storage Backend:

```python
bot = LXMFBot(
    name="mybot",
    announce=600,  # Announce every 600 seconds (10 minutes)
    admins=[],  # Add your LXMF hashes here
    hot_reloading=True,
    command_prefix="/",
    first_message_enabled=True,
    storage_type="sqlite",
    storage_path="mybot.db",
)
```

## [0.4.2] - 2025-01-01

### Major Features - Non-Breaking to existing bots
- **Permission System**
  - Role-based access control with hierarchical permissions
  - Default and admin role system
  - Custom role creation and management
  - Persistent permission storage
  - Command-specific permission requirements
  - Permission flags: READ, WRITE, EXECUTE, MANAGE
  - Built-in permission sets: USE_BOT, SEND_MESSAGES, USE_COMMANDS, etc.
  - Permission inheritance through roles
  - Permission priority system
  - Integration with existing admin system
  - Permission system can be disabled/enabled

### Code Quality
- **Enhanced Command System**
  - Permission-aware command decorator
  - Improved command metadata
  - Better permission validation
  - Integration with help system for permission display

### Core Features
- **Permission Management**
  - `PermissionManager` class for centralized permission handling
  - Role assignment and removal
  - Permission checking utilities
  - User permission calculation
  - Role persistence and storage

## [0.4.1] - 2024-31-12

### Major Features
- **Help Commands**
  - Detection of existing commands and creates a help command.

## [0.4.0] - 2024-12-29

### Major Features
- **CLI Templates Command**
  - Basic bot template with example cogs
  - Full-featured bot template with storage and admin commands
  - Template selection via CLI: `lxmfy create --template full mybot`

- **CLI Verification Command**
  - Using `lxmfy verify` to verify a .whl file using a sigstore hash.

- **Fix Rate Limiting and Spam Protection**
  - Dont process recieved messages at all if banned.


## [0.3.3] - 2024-12-28

### Major Features
- **Simplified CLI Interface**
  - New streamlined command: `lxmfy create mybot ./mybot`
  - Removed complex flag requirements (`--name`, `--output`)
  - Intuitive directory structure creation

### Code Quality
- **Enhanced Code Quality**
  - Full Pylint compliance
  - Improved type hints
  - Better error handling
  - Consistent code style

### Core Features
- **Transport Layer**
  - Automatic path discovery
  - Link caching and management
  - Request handling system
  - Configurable timeouts
  - Path persistence

- **Storage System**
  - JSON file-based persistence
  - In-memory caching
  - Key-value operations
  - Prefix scanning
  - Custom backend support

### Documentation
- **Comprehensive Documentation**
  - Quick start guide
  - Command creation examples
  - Storage system usage
  - Transport layer integration
  - Moderation tools overview
  - Cog system tutorials
- **Website Updates**
  - Mobile-responsive design (some more improvements to come)
  - Improved code block readability
  - Better navigation structure

### Bug Fixes
- Fixed mobile navigation menu positioning
- Improved code block scrolling on mobile devices
- Enhanced responsive layout for feature cards
- Fixed documentation link accessibility

[0.3.3]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.3.3
[0.4.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.0
[0.4.1]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.1
[0.4.2]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.2
[0.4.3]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.3
[0.4.4]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.4
[0.4.5]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.5
[0.4.6]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.6
[0.4.7]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.7
[0.4.8]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.8
[0.4.9]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.4.9
[0.5.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.5.0
[0.5.1]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.5.1
[0.6.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.0
[0.6.3]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.3
[0.6.4]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.4
[0.6.5]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.5
[0.6.6]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.6
[0.6.7]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.7
[0.6.8]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.8
[0.6.9]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.6.9
[0.7.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.0
[0.7.1]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.1
[0.7.2]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.2
[0.7.3]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.3
[0.7.4]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.4
[0.7.5]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.5
[0.7.6]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.6
[0.7.7]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.7
[0.7.8]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v0.7.8
[1.0.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.0.0
[1.0.1]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.0.1
[1.0.2]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.0.2
[1.0.3]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.0.3
[1.1.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.1.0
[1.2.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.2.0
[1.2.1]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.2.1
[1.3.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.3.0
[1.4.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.4.0
[1.5.0]: https://git.quad4.io/LXMFy/LXMFy/releases/tag/v1.5.0
