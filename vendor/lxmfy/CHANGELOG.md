# Changelog

## [2.1.1] - 2026-09-22

### Features
- Async def command callbacks and message handlers now run instead of silently returning coroutines
- Outbound messages to unknown destinations are held and retried on the peer's next announce instead of dropped
- LXMFBot accepts the bot name positionally: LXMFBot("mybot")
- Configurable lxmfy log_level and RNS loglevel passthrough
- Sender controls: ignore_destination, unignore_destination, is_ignored, allow_destination, disallow_destination, prioritise_destination, unprioritise_destination
- Inbound stamp controls: set_inbound_stamp_cost, enforce_stamps, ignore_stamps
- LXMF tickets: generate_ticket, get_inbound_tickets, get_outbound_ticket, get_outbound_ticket_expiry, get_outbound_stamp_cost
- Outbound delivery control: outbound_queue, get_outbound_progress, cancel_outbound, delivery_link_available
- Propagation sync: sync_propagation_node, cancel_propagation_sync, get_propagation_stats, set_retain_on_node, announce_propagation_node, allow_control_identity, disallow_control_identity
- ingest_lxm_uri imports an LXM from an lxm:// URI
- LXMF reactions: bot.react(destination, message_hash, reaction) sends a FIELD_REACTION delivery, on_reaction registers inbound handlers, msg.reaction exposes parsed reaction metadata
- pack_reaction and unpack_reaction build and parse FIELD_REACTION dicts
- Landlock sandbox now uses the landlockpy package instead of in-module syscall bindings
- Documentation moved from Sphinx/RST to Zensical/Markdown, deployed to GitHub Pages on every docs change; PDF, EPUB, and text bundles are built at release time and attached to the GitHub release
- Docs translated into German, Spanish, French, Portuguese, Ukrainian, Russian, and Simplified Chinese with release bundles per language
- Docs use a dark-first quad4 "void" theme with a light "paper" scheme, system-preference detection, and a palette toggle
- Docs are an installable PWA: service worker precaches the core pages, caches visited pages offline, and refreshes content when the browser comes back online
- Docs header gains a language picker and hreflang links for all eight languages
- Docs ship llms.txt and a generated llms-full.txt for LLM consumers
- Docs emit Open Graph, Twitter card, theme-color, and JSON-LD (WebSite plus SoftwareSourceCode) metadata with a social card image, plus robots.txt
- Delivery observability: bot.delivery records outbound lifecycle events (queued, deferred, dispatched, delivered, failed, cancelled, dropped) with subscribers via on_delivery_event and a persisted tail
- Built-in admin commands: /queue, /cancel, /delivery, /loadext, /reloadext
- Per-command rate limits via @bot.command(rate_limit=N), sharing the global cooldown window and persisted counters
- lxmfy init scaffolds a project interactively (name, template, storage, prefix, admins, cogs) with --yes/--force/--here for scripts
- Debugger reports a delivery timeline summary in send pipeline checks
- Docs are versioned with mike: master deploys as dev, releases deploy their tag and the latest alias
- Monthly dependency freshness workflow reports outdated packages to a tracking issue
- Security workflow audits dependencies with pip-audit and uploads a CycloneDX SBOM
- Docs tooling pins live in docs/requirements-docs.txt shared by the docs and release workflows
- All pip installs in workflows and Dockerfiles are hash-pinned (--require-hashes)
- Docker base images are pinned by digest and Poetry installs from a hashed requirements file
- CodeQL workflow provides GitHub-native SAST on pushes, PRs, and a weekly schedule
- master branch protection blocks force pushes and branch deletion
- Reply threading: send(reply_to=, quote=, thread=) sets FIELD_REPLY_TO/FIELD_REPLY_QUOTE/FIELD_THREAD, msg.reply() threads automatically, inbound replies parse onto msg.reply_to/msg.reply_quote/msg.thread
- Conversations: msg.ask() blocks a handler for the sender's next message, msg.ask_async() awaits it in async handlers, and on_answer/on_timeout callbacks handle long waits. Sending a command cancels a pending question. Validators re-prompt on bad answers
- lxmfy.testing: TestBot runs the real inbound pipeline without a Reticulum instance and captures outbound sends. receive, receive_later, drain, wait_sent, last_sent, and outbox cover sync and threaded handlers
- Peer discovery: get_peer_app_data, get_peer_lxmf_data, get_peer_announce, and list_peer_announces read announce metadata from the RNS transport
- Inbound introspection: has_message, inbound_count, inbound_transfers, cancel_inbound, cancel_all_inbound, plus the /inbox admin command
- pack_reply and unpack_reply build and parse reply threading fields

### Fixes
- Delivery destination keeps LXMF's inbound link callbacks, so link-based delivery completes
- Scheduler no longer crashes on sub-minute announce intervals or malformed cron fields
- cleanup() only exits Reticulum when this bot started it, so shared instances survive
- Command POST_COMMAND middleware runs even when a command raises
- Outbound queue persistence snapshots under the queue lock
- Closed links are removed from the link table instead of leaking
- request_link validates destination hashes and reports typed errors
- Generated template bots accept a name argument instead of a dead attribute write
- cogs directory is only created when cogs are enabled
- CLI signatures test verifies against the identity it signed with instead of an unrecallable lookup
- disallow_destination, unprioritise_destination, and disallow_control_identity edit router lists directly because the matching LXMF 1.1.1 methods pop by index or reference unbound names
- Identity files that fail to load raise a clear RuntimeError instead of passing None to LXMRouter
- connect_rrc and disconnect_rrc guard against an uninitialized RRC manager
- Configured admins now receive the admin role when permissions are enabled, so admin-only commands and spam bypasses apply to them

### Tests
- Localhost UDP pair live test with two subprocess routers (LXMFY_LIVE_UDP=1)
- Propagation tests run against a real isolated router instead of no-op asserts
- Subprocess tests pass PYTHONPATH so they work outside editable installs
- Removed permanently skipped and tautological tests
- Router control tests cover ignore/allow/prioritise lists, stamp costs, tickets, outbound queue and cancel, propagation sync, and URI ingestion against a real router
- Benchmark suite for hot paths: field packing, command unpacking, hash parsing, permission checks, canonicalization, signatures, storage
- Delivery tests cover tracker persistence and filters, outbound queued events, the /delivery command, per-command rate limits, admin permission wiring, and the init scaffold

### CI/CD
- GitHub Actions for lint, typecheck, tests, live-local Alice/Bob, live UDP pair, and build
- Security workflow: zizmor workflow audit, bandit SAST, gitleaks secret scan
- Coverage XML artifact on the 3.13 test leg with a 65% coverage gate
- Releases build a self-contained .pyz zipapp (shiv) alongside the wheel and attach it to the GitHub release
- Publish workflow triggers on tag pushes and creates the GitHub release as a draft, attaches assets, then publishes, which immutable releases require
- SLSA build provenance attestations on the wheel, sdist, and pyz via GitHub artifact attestations (Sigstore)
- Test matrix covers Python 3.11 through 3.14
- Benchmark job archives results per run
- Secure defaults: SHA-pinned actions, least-privilege token, Dependabot, dependency review, Scorecard, CODEOWNERS
- OIDC publish to PyPI on GitHub release (or confirmed manual run)

### Updates
- Dropped former self-hosted package registry publish targets
- Project links point at GitHub
- Pyright runs in strict mode with the untyped-dependency noise rules disabled
- Ruff lint expanded to the modern ruleset (bugbear, bandit, refactor, perf, try-except, datetime, logging, and friends)

## [2.0.4] - 2026-09-02

### Fixes
- Always drop inbound LXMF messages with an invalid signature

### Tests
- Alice/Bob local live LXMF test over TCP loopback (LXMFY_LIVE_LOCAL=1)

## [2.0.3] - 2026-09-01

### Fixes
- Outbound stamp cost comes from the peer announce or an explicit send override
- Config stamp_cost is inbound-only again
- Outbound messages include reply tickets by default

### Updates
- RNS >=1.5.4, LXMF >=1.1.1, cbor2 >=6.1.0
- Dev tooling updated: pytest 9.1, ruff 0.16, hypothesis 6.168, pyright 1.1.414, twine 7, psutil 7.2.2
- Debugger covers stamp, ticket, and ratchet send blockers more clearly

## [2.0.2] - 2026-07-23

### Features
- Debugger CLI and helpers for send/receive diagnosis
- Privacy-redacted shareable reports and blocker lists

### Fixes
- Delivery hash no longer registers lxmf/delivery on Transport

### Updates
- Color output respects NO_COLOR / FORCE_COLOR and adds --no-color

## [2.0.1] - 2026-07-21

### Fixes
- Prefer existing user/system Reticulum config over the bot config path
- Isolated bots force share_instance = No to avoid shared-instance digest rejection
- opportunistic_sending now selects LXMF OPPORTUNISTIC delivery

### Tests
- Config discovery and isolated share_instance coverage
- Opt-in live LXMF ping/pong (LXMFY_LIVE_LXMF=1)

### Updates
- RNS >=1.3.9

## [2.0.0] - 2026-07-10

Final feature release of LXMFy.

### Features
- RRC client support for hub chat ([RRC spec](https://rrc.kc1awv.net/))
- RRCBot template and session persistence options

### Fixes
- Crash-safe outgoing queue restore and flush
- Corrupt persisted destinations dropped on restore

### Updates
- RNS >=1.3.8, LXMF >=1.0.1, cbor2 >=5.4.0
- Message persistence enabled by default
- Bounded queues and RRC resource caps

### Tests
- RRC/CBOR unit and integration tests
- Opt-in live rrcd smoke test (LXMFY_LIVE_RRC=1)

## [1.6.5] - 2026-07-04

### Features
- Optional Landlock filesystem sandbox on Linux
- External cog sandbox prefers Landlock, then bwrap, then firejail
- Static type checking with pyright

### Fixes
- Removed invalid enforce_stamps from enable_propagation()
- Cog permission checks delegate to bot.permissions

### Updates
- LXMF 1.0.1+, RNS 1.3.5+
- Docs and README updated for sandboxing

## [1.6.4] - 2026-05-30

### Updates
- LXMF 1.0.0, RNS 1.3.4

## [1.6.3] - 2026-05-08

### Features
- Structured LXMF field commands and results (FIELD_COMMANDS / FIELD_RESULTS)
- Field commands use the same registry, permissions, and middleware as text commands
- lxmf_commands_enabled config option (default on)

## [1.6.2] - 2026-04-15

### Features
- reticulum_config_dir / LXMFY_RETICULUM_CONFIG_DIR for shared Reticulum config
- Announce display name refreshed from bot name or config files
- announce_now() for library callers

### Updates
- RNS 1.1.5

## [1.6.1] - 2026-03-11

### Updates
- License switched from MIT to BSD-0-Clause

## [1.6.0] - 2026-02-27

### Updates
- RNS 1.1.3
- Cryptography 46.0.5

## [1.5.0] - 2026-01-15

### Features
- In-memory storage backend
- Reliability suite: chaos, temporal drift, leak detection, manifold NLP tests
- Optional outgoing message persistence across restarts
- Optional identity pinning against hash collisions
- Runtime cog remove/reload
- Cross-language script cogs with optional sandboxing
- Local offline Tiny-NLP intent classification
- RNS link support
- Type-hinted command argument parsing
- Hypothesis property-based tests

### Fixes
- Identity persistence works in test mode

## [1.4.0] - 2026-01-05

### Features
- require_stamps inbound stamp enforcement toggle
- Optional identity fetch for unknown senders
- Performance and memory stress tests

### Fixes
- Cleanup stops hanging Reticulum background threads between tests
- More stable propagation and signature path-request tests

## [1.3.0] - 2026-01-04

### Features
- Version shown in lxmfy help

### Updates
- Twine-based publish flow and README install notes
- SHA256 checksums for release assets
- RNS 1.1.0

## [1.2.1] - 2025-11-30

### Fixes
- Actions pinning settings on the project repo

## [1.2.0] - 2025-11-30

### Features
- Dedicated colors module for CLI

### Fixes
- Interactive CLI color support on Windows 10/11

### Updates
- RNS 1.0.4, ruff 0.14.7
- Moved from safety to bearer for security scanning
- Actions pinned to full-length commit SHAs

## [1.1.0] - 2025-11-21

### Features
- Direct delivery with retries and propagation fallback
- Configurable stamp cost for bots

### Updates
- Poetry-only tooling and codebase cleanup
- LXMF 0.9.3, RNS 1.0.3

## [1.0.3] - 2025-11-03

### Updates
- LXMF 0.9.1

## [1.0.2] - 2025-11-03

### Updates
- LXMF 0.9.0, RNS 1.0.1
- Docker files moved under docker/

## [1.0.1] - 2025-09-28

### Fixes
- Signature canonicalization format and matching tests

## [1.0.0] - 2025-09-27

### Features
- Stable 1.0 release
- Broad pytest coverage and Actions CI
- Type hint and code quality cleanup

## [0.8.0] - 2025-09-27

### Features
- Cryptographic message signing and verification
- Optional require_message_signatures
- CLI helpers for signature testing and toggling

## [0.7.8] - 2025-09-13

### Updates
- Dependency refresh and Makefile added

## [0.7.7] - 2025-07-14

### Updates
- Arm64 Docker support
- RNS 1.0.0, LXMF 0.8.0
- General cleanup

## [0.7.6] - 2025-07-05

### Features
- Threaded command option for long-running callbacks

### Updates
- Dependency maintenance

## [0.7.5] - 2025-06-22

### Features
- More robust cog command loading
- CogTest template for regression checks

## [0.7.4] - 2025-06-22

### Fixes
- Cog command binding preserved metadata correctly

## [0.7.3] - 2025-05-15

### Updates
- LXMF 0.7.1, RNS 0.9.6

## [0.7.2] - 2025-05-13

### Updates
- LXMF 0.7.0
- Python 3.13 required

## [0.7.1] - 2025-05-09

### Fixes
- Workflow fix

## [0.7.0] - 2025-05-09

### Features
- LXMF fields support

### Updates
- Dependencies and docs

## [0.6.9] - 2025-05-07

### Updates
- Opencontainers metadata
- Removed bot scan/verification paths
- Performance and cog loading hardening

## [0.6.8] - 2025-04-29

### Features
- CLI colors and interactive mode
- Dockerfile.Build added

## [0.6.7] - 2025-04-29

### Fixes
- Workflow fix

## [0.6.6] - 2025-04-29

### Updates
- Basic tests, docs, cleanup
- ARMv7 and ARM64 builds
- Removed Bandit, meme bot, and requests

## [0.6.5] - 2025-04-07

### Fixes
- Attachment system
- Storage error handling

## [0.6.4] - 2025-04-06

### Updates
- Security and performance refactoring

## [0.6.3] - 2025-04-06

### Fixes
- Syntax errors
- Manual publish workflow

## [0.6.0] - 2025-04-06

### Features
- Run bot templates directly (lxmfy run echo)
- LXMF attachment support
- Basic tests and docker-compose

### Updates
- LXMF 0.6.3, RNS 0.9.3

## [0.5.1] - 2025-02-14

### Fixes
- Unused variables and version bump

## [0.5.0] - 2025-02-14

### Fixes
- Config, CLI, core, and announce system

## [0.4.9] - 2025-02-14

### Features
- Disable announces on start and configure announce interval

### Fixes
- Duplicate responses
- LXMF 0.6.2

## [0.4.8] - 2025-01-25

### Fixes
- Storage serialization
- SQLite storage backend

## [0.4.7] - 2025-01-25

### Fixes
- Storage serialization
- Event attribute handling

## [0.4.6] - 2025-01-25

### Features
- Middleware system
- Task scheduler

### Updates
- LXMF 0.6.1

## [0.4.5] - 2025-01-20

### Features
- Event system with priorities and middleware

### Updates
- RNS and LXMF bumps

## [0.4.4] - 2025-01-17

### Features
- Bot analysis CLI (lxmfy analyze)

### Updates
- RNS 0.9.0

## [0.4.3] - 2025-01-04

### Features
- First-message handler
- SQLite storage backend
- EchoBot, ReminderBot, NoteBot templates (FullBot removed)

## [0.4.2] - 2025-01-01

### Features
- Role-based permission system with persistent roles and command checks

## [0.4.1] - 2024-12-31

### Features
- Auto-generated help command

## [0.4.0] - 2024-12-29

### Features
- CLI templates (basic and full)
- Wheel verification via lxmfy verify
- Stronger rate limiting and spam protection for banned senders

## [0.3.3] - 2024-12-28

### Features
- Simplified lxmfy create CLI
- Transport layer path discovery and link caching
- JSON storage system
- Initial docs and website polish

### Fixes
- Mobile navigation and docs link accessibility
