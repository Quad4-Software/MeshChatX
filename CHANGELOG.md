# Changelog

All notable changes to this project will be documented in this file.

## [4.4.0] - 2026-04-TBD

### On Hold

- MicronParser truecolor support - until NomadNet supports etc.

### Changed

- **Backend layout**: Startup helpers were moved out of **`meshchatx/meshchat.py`** into **`meshchatx/src/path_utils.py`** (`resolve_log_dir`, `get_file_path`, `request_client_ip`), **`meshchatx/src/ssl_self_signed.py`** (`generate_ssl_certificate`), and **`meshchatx/src/env_utils.py`** (`env_bool`). **`meshchat.py`** re-exports these names so existing imports and test patches keep working.
- **HTTP client stack**: **`docs_manager`**, **`map_manager`**, and **`translator_handler`** use **`aiohttp`** instead of **`requests`**; the **`requests`** dependency was removed from **`pyproject.toml`**.
- **CLI entry points**: The preferred headless command is **`meshchatx`**, matching the MeshChatX product name. The wheel and installs still expose **`meshchat`** as a **compatibility alias** to the same `meshchatx.meshchat:main` entry point, so existing scripts and automation using `meshchat` keep working. New documentation and examples use **`meshchatx`** first (Docker default command, `task run`, Make, README install examples). This is **not** a removal of `meshchat`; both names are installed side by side in 4.4.0.
- **Frontend HTTP**: Removed the **axios** dependency; API traffic uses native **`fetch`** through the shared client in **`meshchatx/src/frontend/js/apiClient.js`** (same call sites, no axios runtime).
- **Frontend build**: Upgraded to **Vite 8** with **`@vitejs/plugin-vue` 6**; production bundles use Rolldown (`build.rolldownOptions` and **`output.codeSplitting`** for vendor chunks). Dev and build scripts are unchanged (`vite dev`, `vite build`).
- **Announce storage and fetch limits**: Per-aspect stored announces are capped (default **1000**); after each upsert, excess rows are trimmed **oldest first** (`trim_announces_for_aspect`). Default client fetch size (**500**), search fetch cap (`announce_search_max_fetch`), and discovered-interface list cap (`discovered_interfaces_max_return`) are configurable. Legacy `announce_limit_*` migrates to **`announce_max_stored_*`**; new keys include `announce_fetch_limit_*` per aspect. Clearing a numeric setting restores the default (`IntConfig.set(None)` removes the key). Settings UI and locales (en, de, it, ru) expose the new options; telephony-related aspects share LXMF announce keys where applicable.

### New Features

- **RNS log level**: **`--rns-log-level`** and **`MESHCHAT_RNS_LOG_LEVEL`** set the Reticulum (RNS) stack log level using named levels (**`none`**, **`critical`**, **`error`**, **`warning`**, **`notice`**, **`verbose`**, **`debug`**, **`extreme`**) or a numeric level. When the flag is passed, it **overrides** the environment variable.
- **Custom TLS certificate paths**: Optional **`--ssl-cert`** and **`--ssl-key`** (and **`MESHCHAT_SSL_CERT`** / **`MESHCHAT_SSL_KEY`**) load PEM files for the web server; both must be set together. When unset, behaviour is unchanged (auto-generated or existing **`.../identities/<id>/ssl/cert.pem`** and **`key.pem`**).
- **Auth access control (login and setup)**: Failed attempts and outcomes are stored in **`access_attempts`** (IP, User-Agent, path, method, time, outcome). **Untrusted** clients are **rate limited** per IP and path and **locked out** after repeated wrong passwords from the same IP (fingerprints that have successfully logged in for the current identity are **trusted** and use higher per-window limits and are excluded from lockout counting for their own UA). **`trusted_login_clients`** stores IP plus User-Agent hash per identity after a successful login or setup, with pruning of the oldest entries when the cap is exceeded. **`GET /api/v1/debug/access-attempts`** lists attempts for the debug tools (search, outcome filter, pagination). Database schema version **42** adds these tables.
- **Debug Logs UI**: The debug logs page has tabs for **Logs** and **Access attempts**, with refresh, copy, search, outcome filter, and pagination for access attempts.
- **LXMF Lift Banishment from context menus**: Right-click on a message in the conversation viewer or on a row in the messages sidebar shows **Lift Banishment** when that peer is blocked, calling the blocked-destinations API and refreshing UI state (aligned with NomadNet banish/lift patterns).

### Fixes

- **Multi-context shutdown**: Application shutdown tears down **every** `IdentityContext` (not only the active one): `ForwardingManager.teardown` for alias LXMF routers and links, `BotHandler.stop_all` including orphan entries in `bots_state`, per-context databases and resources, then clears context maps and stops the health monitor before websockets and RNS teardown. Mesh Server / page node shutdown order preserved.
- **NomadNet favourites 3-dots**: Fixed 3-dots button on favourite cards not responding; added `flex-shrink-0` so the button is not squished in the flex layout. Wrapped announce tab dropdown in `flex-shrink-0` for consistency.
- **LXMF inbound stamps**: Settings could not disable proof-of-work stamps for direct inbound messages (UI enforced minimum 1; API coerced sub-1 values to `None` and broke `IntConfig`). Added a **Require inbound stamps** toggle, allowed stored cost `0`, and clamp validation to `0–254` so LXMF correctly clears the delivery stamp requirement.
- **Identity recall hex parsing**: UUID-style strings (hyphens in `bytes.fromhex`) no longer spam `Error recalling identity`; `recall_identity` and telephone identity resolution normalize separators. LXMF/telephony announce lookups compare normalized identity hashes so hyphenated inputs match stored hex.

### Improvements

- **`/robots.txt`**: Served with **`User-agent: *`** / **`Disallow: /`** for deployments exposed to HTTP crawlers; a matching file ships under **`meshchatx/src/frontend/public/robots.txt`** in frontend builds.
- **`Makefile`** / **`Taskfile.yml`**: **`make run`** and **`task run`** invoke **`poetry run python -m meshchatx.meshchat`** so development runs work without relying on the **`meshchatx`** entry-point script being available to Poetry’s runner. README “from source” examples and **`docs/meshchatx_linux_sandbox.md`** (and the in-app copy) use the same form; wheels and installs still provide the **`meshchatx`** / **`meshchat`** CLI names.
- **Container image (Docker/Podman)**: Final stage runs as non-root **`meshchat`** (`USER meshchat`). **`HEALTHCHECK`** probes **`https://127.0.0.1:8000/api/v1/status`** with TLS verification disabled for the self-signed default cert. **`podman build`** defaults to OCI layout, which omits **`HEALTHCHECK`**; use **`podman build --format docker`** when you rely on the embedded health check. Bind mounts for **`/config`** under rootless Podman may need **`:U`**, **`podman unshare chown`**, or host permissions so uid **1000** can write (same class of issue as Docker **`chown 1000:1000`** on a volume).
- **Conversation image paste**: Pasting image data into the message field (e.g. screenshot or copied image) now attaches it like the image picker, without using the separate text-only paste button.
- **Page Archives export**: Archives tool can download the current snapshot or all selected snapshots as `.mu` files (raw page body; multi-export uses path plus a short hash in the filename to avoid collisions).
- **Network visualizer data loading**: Fetches only `lxmf.delivery` and `nomadnetwork.node` announces instead of all; path table filtered by those destination hashes via new `POST /api/v1/path-table` endpoint. Dramatically reduces load time on large networks.
- **NomadNet context menus**: Right-click context menu on announces and favourites (like conversation viewer): Rename, Banish, Lift Banishment, Remove, Add to Favourites, Move to Section. Menus use Teleport to body and `justOpened` delay to avoid immediate close on click.
- **Dynamic locale discovery**: Locales are now discovered automatically from `meshchatx/src/frontend/locales/*.json` via `import.meta.glob`. Adding a new language only requires a single JSON file with a `_languageName` key; no code changes to `main.js`, `LanguageSelector.vue`, or tests needed.
- **CI supply chain hardening**: Replaced all third-party Gitea Actions with POSIX-compliant shell scripts in `scripts/ci/`. Checkout is inlined as plain git commands; Node.js, go-task, and Java binaries are SHA256-verified against upstream checksums; Python is built from official python.org source with GPG signature verification. Only `gitea-release-action` and `upload-artifact` remain as external actions.
- **SLSA v1 release provenance**: Release workflow (`build.yml`) can attach cosign **SLSA v1** blob attestations (`*.cosign.bundle`) beside each release artifact when `COSIGN_PRIVATE_KEY` is configured; `scripts/ci/slsa-predicate.py`, `attest-release-assets.sh`, and `verify-release-attestation.sh` support signing and verification with Rekor transparency-log upload. Documented in `SECURITY.md` with `cosign.pub` at the repo root for downstream verification.
- **Nomad Network downloader** (`nomadnet_downloader.py`): Thread-safe link cache (lock-protected); **`get_cached_active_link()`** returns only **ACTIVE** links and drops stale entries; faster path/link polling (~**20 ms**); cache re-checked after path resolution and before opening a new link to reduce redundant link setup; **cancel** removes the matching cache entry before link teardown; UTF-8 decode with replacement and safer handling for empty page bodies, file metadata, and list-shaped file payloads. **`GET /api/v1/nomadnetwork/{hash}/identify`** uses **`get_cached_active_link`** instead of reading the raw cache dict.
- **NomadNet browser UI** (`NomadNetworkPage.vue`): Loading state shows **phase-based** copy (finding path, establishing link, requesting page, transferring) instead of a generic **“Loading 0%”**, with optional **(N%)** when transfer progress applies; header next to hop distance shows **last load duration** and **page body size** (human-readable bytes). New i18n keys **`nomadnet.load_phase_*`**, **`load_phase_default`**, and **`path_away_suffix`** (en, de, it, ru).
- **WebSocket (NomadNet page/file downloads)**: Backend emits **`nomadnet.page.download`** / **`nomadnet.file.download`** messages with **`status: "phase"`** and **`load_phase`** so the UI can track **`finding_path`**, **`establishing_link`**, **`requesting_page`**, and **`transferring`** (phases emitted from **`NomadnetDownloader._emit_phase`**).
- **MicronParser** (NomadNet `.mu` rendering): Parsing is **fault-tolerant**—a bad line yields an escaped fallback segment instead of failing the whole page; full-document fallback if conversion throws; **`Intl.Segmenter`** fallback in **`forceMonospace`**; DOMPurify sanitization and overlay stripping wrapped for robustness.

### Removed

- **axios**: Dropped as a frontend dependency in favour of native **`fetch`** (see **Changed**).
- **Legacy PR vulnerability scanner**: Removed the old PR-oriented workflow and its helper script in favour of Trivy.
- **Nix flakes**: Removed due to no longer used and maintained.

### Testing

- **End-to-end (Playwright)**: Added `tests/e2e/` with `pnpm run test:e2e` and `scripts/e2e/start-e2e-stack.sh` (isolated backend storage, headless MeshChat HTTP server, Vite dev server). CI installs Chromium and runs the suite against the proxied app. `tests/e2e/smoke.spec.js` checks `/api/v1/status` via the Vite proxy, direct `app/info`, document shell, and key routes. `tests/e2e/navigation.spec.js` covers the standalone tutorial route, command palette (Ctrl+K, jump to Settings, Escape, Getting Started modal), sidebar navigation across main sections (with `prepareE2eSession` calling `POST /api/v1/app/tutorial/seen` and changelog seen so tutorial/changelog overlays do not block pointer clicks), Alt+1 / Alt+S shortcuts, and the tools hub including a paper-message deep link. `tests/e2e/shell.spec.js` covers desktop sidebar collapse and expand, header theme toggle (config-backed dark class on the root shell), notifications bell dropdown open and close, the Call page Phone tab, Messages Announces tab peer search input, and NomadNet favourites plus announces search inputs. Shell tests scope the top bar via the sticky chrome strip (the app does not use a `<header>` landmark). Related UI fixes for reliable palette tests: `KeyboardShortcuts` skips handling when the action is `command_palette` so Ctrl+K reaches the palette; `CommandPalette` listens for keydown in the capture phase and stops propagation on the palette shortcut.
- **Announce limits**: DAO trim, manager upsert/limits, fuzzing, flood-load, smoke expectations, meshchat coverage mocks, and benchmark scripts updated for capped storage and fetch behaviour.
- **ForwardingManager**: Teardown coverage for alias deregistration and cleanup.
- **NomadNetworkSidebar**: Tests for 3-dots on favourite cards, context menu options, rename/remove/banish from context, announce right-click menu, add favourite and block from announce context.
- **ConversationViewer**: Clipboard image paste on the compose field; context menu / banishment-related coverage as applicable.
- **ArchivesPage**: Tests for `.mu` export filename helpers and download helper.
- **i18n**: Dynamic locale file discovery in tests; added `_languageName` presence check for all locales.
- **ConfigManager**: Inbound stamp cost may be set to `0`.
- **meshchat_utils**: Tests for `normalize_hex_identifier` / `hex_identifier_to_bytes`.
- **Nomad Network downloader**: `tests/backend/test_nomadnet_downloader_boost.py` covers cache eviction, cancel/cache removal, UTF-8 replacement for page bodies, path-wait cache hit, short list-shaped file payloads, and lock-safe cache access; `test_nomadnet_downloader.py` for cancel behaviour.
- **MicronParser**: Resilience tests (forced **`parseLine`** failure, fragment fallback); existing Micron coverage retained.
- **NomadNetworkPage**: **`formatShortDuration`** unit tests.
- **Custom TLS CLI**: `tests/backend/test_ssl_custom_args.py` asserts **`--ssl-cert`** without **`--ssl-key`** (and the reverse) exits with code **2**.
- **Auth access attempts**: `tests/backend/test_access_attempts_dao.py` (DAO behaviour, trusted pruning, cleanup, lockout counting, Hypothesis invariants for `user_agent_hash` and insert/list). `tests/backend/test_access_attempts_enforcement.py` (`_request_client_ip`, `_enforce_login_access` for untrusted rate limit and lockout, trusted bypass and trusted rate limit, Hypothesis monotone check, HTTP smoke for login logging, lockout and rate-limit **429** responses, debug access-attempts JSON shape). **Vitest**: `DebugLogsPage` access tab loads `/api/v1/debug/access-attempts`. **Playwright**: `smoke.spec.js` asserts **Logs** and **Access attempts** on `#/debug/logs`.

### Updates

- **README** (en + `lang/`): Headless CLI examples use **`meshchatx`**. **`docs/meshchatx_linux_sandbox.md`** and in-app **`meshchatx-docs`** copy updated the same way; **Android (Termux)** run instructions use **`meshchatx`** with an alias note.
- **README** (en + `lang/`): Configuration table documents **`--rns-log-level`** / **`MESHCHAT_RNS_LOG_LEVEL`**.
- **README**: Configuration table documents **`--ssl-cert` / `--ssl-key`** and **`MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY`**.
- **`docs/meshchatx.md`**: Notes **`path_utils`**, **`ssl_self_signed`**, and **`env_utils`** as split-out modules; **`meshchat.py`** remains the orchestration entry.
- **CI**: Gitea workflow **`.gitea/workflows/sync-github-release-assets.yml`** can mirror selected release assets to the GitHub mirror for Windows and macOS when configured.
- **pnpm-lock.yaml**: Updated Vue, Vue-i18n, **Vite 8**, and **`@vitejs/plugin-vue`**.
- **Locales**: Added `nomadnet.lift_banishment` to en, de, ru, it. Added `_languageName` to all locale files. Added `archives.export_mu` and `archives.export_selected_mu` for the archives export buttons. Strings for announce and discovered-interface limits were added for this release. NomadNet browser: **`nomadnet.load_phase_*`**, **`load_phase_default`**, **`path_away_suffix`**; corrected **`nomadnet.no_search_results_peers`** placement for de/ru where duplicated.
- **Python dependencies**: `websockets` >= 16.0, `aiohttp` >= 3.13.3, `psutil` >= 7.2.2, `jaraco.context` >= 6.1.1, `hypothesis` >= 6.151.9.

## [4.3.1] - 2026-03-10

### Fixes

- **Message retry**: Added per-message retry button to the context menu and inline on failed/cancelled outbound messages, allowing individual message resend without bulk retry.
- **Sender display name**: Fixed outgoing messages showing "Unknown Peer" by resolving display names from conversations and announces when composing to a new peer.
- **Conversation refresh on send**: Added `lxmf_message_created` and `lxmf_message_state_updated` websocket handlers to `MessagesPage` so the sidebar updates after sending without requiring an incoming message to trigger a refresh.
- **No-flash sidebar updates**: Outbound message state transitions (outbound, sending, sent, delivered) now update the sidebar in-place without API calls. New messages trigger a background merge that patches existing conversation objects rather than replacing the array, preventing full sidebar re-renders.
- **Received message outbound flag**: Incoming messages now explicitly set `is_outbound: false` instead of relying on an undefined default.

### Testing

- **Frontend**: New tests for message retry context menu visibility, retry click behavior, `is_outbound` on received messages, in-place conversation updates on send, display name merge from API, failed message count tracking, and zero API calls during state transitions.
- **Backend**: New tests for `MessageHandler` covering `failed_count` in conversations, `filter_failed` query, `search_messages`, and `after_id`/`before_id` pagination.

## [4.3.0] - 2026-03-09

### New Features

- **Mesh Server**: Serve Micron pages and files directly over Reticulum. Each server gets its own RNS identity and destination address with the `nomadnetwork.node` aspect, making it compatible with the standard NomadNet page browsing protocol. Supports dynamic per-page and per-file request handler registration, announce broadcasting, and full lifecycle management (create, start, stop, delete, rename).
- **Mesh Server management UI**: New tool page for creating and managing Mesh Servers with start/stop controls, announce button, page CRUD (add, edit, delete), file upload/delete, and a "View" button that opens the server's content in the built-in NomadNet browser.
- **Micron Editor publish integration**: "Publish to Mesh Server" button in the Micron Editor allows publishing the current tab or all tabs directly to a selected Mesh Server.
- **Local page serving**: Pages and files hosted on local Mesh Servers are served directly from disk when browsed locally, bypassing RNS link establishment. This provides instant page loads for your own content.
- **Local announce injection**: Mesh Server announces are injected directly into the MeshChat announce database on startup, node start, and manual announce, ensuring they appear in the NomadNet announces list without depending on RNS loopback processing.
- **Stranger protection**: Settings to block attachments and messages from non-contacts. Message handling strips attachments from strangers when configured; database schema extended to track stripped attachments. Localization and UI for stranger protection options.

### Improvements

- **NomadNet downloader**: Added identity recall validation before link establishment to provide clearer error messages when a destination identity cannot be resolved.
- **NomadNet partials**: Fixed partial page loading when partials include field data; PARTIAL_LINE_REGEX captures optional fields, WebSocket allows partial responses when callback registered, partial DOM updates via innerHTML. Auto-refresh behavior improved.
- **PageNodesPage**: Refactored error handling.
- **MessagesSidebar**: Time-ago functionality for message timestamps.
- **InterfacesPage**: Removed bounce and disconnected animation logic and related properties.
- **Status indication**: Removed redundant status indication from UI.

### Testing

- **Mesh Server tests**: 66 new tests covering PageNode (setup, teardown, announce, page/file CRUD, responder closures, config persistence, status, link callbacks, path traversal protection, edge cases) and PageNodeManager (create, delete, start/stop, announce, rename, get/list, disk persistence, teardown).
- **Notification and LXMF**: Extensive tests for notification reliability and LXMF field hardening.
- **Frontend**: Comprehensive tests for MicronParser and NotificationBell.
- **Performance**: Updated performance tests and expectations for rendering times.

### Developer / Docs

- **CONTRIBUTING** and **CONTRIBUTORS** added for contribution guidelines and credits.
- **Makefile** added for common build/run targets.
- **README** updates.

## [4.2.1] - 2026-03-06

### New Features

- **DOMPurify for NomadNet**: Added `dompurify` dependency and global `DOMPurify` in frontend entry so MicronParser sanitizes content when browsing Nomad Network nodes; removes "DOMPurify is not installed" warning in AppImage and packaged builds.
- **Identities page**: Import and Export all identities in header (next to New Identity). Per-identity key actions: export key file and copy Base32 shown on hover for the current identity card only. Import modal with upload key file and paste Base32. Backend `GET /api/v1/identities/export-all` returns a ZIP of all identity key files.
- **Contacts page**: Contacts management UI with routing, localization (en, de, it, ru), and LXMA contact handling. Public key retrieval and tests for LXMA URI handling.

### Security

- **SQL injection hardening**: All raw SQL queries audited and confirmed parameterized. Added `_validate_identifier()` for dynamic table/column names in schema migrations. Legacy migrator `ATTACH DATABASE` path properly escaped; column names from untrusted legacy DBs filtered with regex whitelist.

### Diagnostics

- **Adaptive Diagnostics Engine**: Crash recovery upgraded from static heuristics to a lightweight adaptive system that learns from crash history.
  - **Crash history persistence**: New `crash_history` table (migration 40) stores crash events with error type, diagnosed cause, symptoms (JSON), probability, entropy, and divergence. Capped at 200 entries.
  - **Bayesian weight learning**: Root-cause probabilities refined over time using a conjugate Beta-Binomial model. After 3+ crashes, learned priors replace hardcoded defaults and are persisted in config. Weights clamped to [0.01, 0.99] to prevent degenerate priors.
  - **Log entropy**: Shannon entropy computed over log-level distribution in a 60-second sliding window from in-memory deques (zero DB queries). Error rate tracking exposed as `current_error_rate` property.
  - **Predictive health monitor**: New `HealthMonitor` daemon thread checks every 5 minutes for entropy climbing (3 consecutive rising readings above threshold), elevated error rate, and low available memory. Warnings broadcast via WebSocket. No DB queries in the monitor loop.
- **Integrity & crash recovery hardening**: Fixed `platform.release()` regex safety in legacy kernel detection. Fixed `IntegrityManager` path handling when database is outside storage directory. Added latitude clamping in map tile calculations to prevent division by zero at geographic poles.

### Performance

- **Database indexes**: Added 8 new indexes in schema migration 39 covering contacts JOIN columns (`lxmf_address`, `lxst_address`), notification filters (`is_viewed`), map drawings (`identity_hash`), voicemails (`is_read`), archived pages (`created_at`), and a composite index on `lxmf_messages(state, peer_hash)` for the failed-count subquery.
- **SQLite PRAGMAs at startup**: `journal_mode=WAL`, `synchronous=NORMAL`, `cache_size=8MB`, `mmap_size=64MB`, `temp_store=MEMORY`, `busy_timeout=5s` applied on every database initialization.
- **Bounded queries**: `search_messages()`, `get_conversations()`, and `get_filtered_announces()` now enforce default LIMIT (500) to prevent unbounded result sets. `get_all_lxmf_messages()` paginated (5000 per page); export endpoint iterates pages.
- **Slim conversation list queries**: Conversation list queries (`MessageDAO.get_conversations`, `MessageHandler.get_conversations`) now select only the columns needed for the list view, skipping large `content` and `fields` blobs.
- **Bulk database operations**: Batch methods (`mark_conversations_as_read`, `mark_all_notifications_as_viewed`, `move_conversations_to_folder`) converted from per-row `execute` loops to single `executemany` calls inside transactions. `delete_all_lxmf_messages` wrapped in a transaction for atomicity. Added `DatabaseProvider.executemany()`.

### Improvements

- **Micron editor**: Button label changed from "Download" to "Save" on the micron editor page (en: Save; de: Speichern; it: Salva; ru: Сохранить).
- **MicronParser**: Overlay style stripping and improved event handling in NomadNetworkPage.
- **Release workflow**: Include `meshchatx-frontend.zip` in release assets (was generated and checksummed but not uploaded). Add Linux arm64 build step (AppImage + deb) via `dist:linux-arm64`. Release `files` list now includes `*.zip`.
- **Community interfaces**: Replaced RNS Testnet Amsterdam and BetweenTheBorders with Quad4 hub (62.151.179.77:45657 TCP). Removed outbound health checks: suggested community interfaces are now a static list with no TCP probes to the internet.
- **Identities**: Removed top key-control card; key actions moved to per-card hover. Message count and LXMF/LXST addresses on identity list; backend message_count for current identity.
- **About page**: Security & Integrity section: signed (shield-check) icon and "No integrity violations" badge use green styling in dark mode; status pill has dark-mode emerald variants.
- **Version management**: Single source of truth is `package.json`; run `pnpm run version:sync` to update `meshchatx/src/version.py`. Build runs sync automatically.

### Testing

- **SQL injection tests**: Unit tests for `_validate_identifier`, integration tests for `_ensure_column` with malicious identifiers, property-based tests for `ATTACH DATABASE` path escaping and identifier regex.
- **DAO fuzzing**: Hypothesis property-based fuzzing across ContactsDAO, ConfigDAO, MiscDAO, TelephoneDAO, VoicemailDAO, DebugLogsDAO, RingtoneDAO, MapDrawingsDAO, MessageDAO folders, MessageHandler search, `_safe_href`, and utility functions.
- **Performance regression benchmarks**: Latency (p50/p95/p99) and throughput (ops/sec) benchmarks for announce loading/search, message loading/search/upsert, favourites, and conversation operations. EXPLAIN QUERY PLAN assertions verify index usage. Concurrent read/write contention tests. LIKE search scaling tests across data sizes. Index existence and PRAGMA verification tests.
- **Diagnostics tests**: CrashHistoryDAO CRUD and cleanup tests. Bayesian weight learning correctness (prior defaults, learned priors, clamping, minimum crash threshold, config persistence). HealthMonitor detection logic (entropy climb, error rate, memory pressure, edge cases). Log entropy math (zero/uniform/single-level distributions, sliding window expiry). Hypothesis property tests for Beta-Binomial posterior bounds.
- **Integrity & recovery tests**: Corrupt/empty/missing-key manifest handling. Direct hash-file and DB integrity checks. Entropy threshold boundary tests. Database-outside-storage-dir handling. CrashRecovery system entropy edge cases, legacy kernel regex safety, Reticulum diagnosis isolation, and keyboard interrupt passthrough.

## [4.2.0] - 2026-03-05

### New Features

- **Micron partials**: Support for partial content in Nomad Network pages; partial handling in NomadNetworkPage with processing/clearing, dynamic page updates, and MicronParser integration. Tests for partial handling, regex matching, content injection, and state management.
- **LXMF quoted replies**: Full support for `reply_quoted_content` in message parsing, sending, and rendering; reply flow in ReticulumMeshChat with quoted content in LXMF message construction.
- **Reply in messages**: Reply functionality for messages in ReticulumMeshChat.
- **Discovery filters and quick actions**: Added discovery whitelist/blacklist configuration and per-announce quick actions in Recently Heard Announces (three-dots menu) to allowlist or blacklist announces directly from each card.
- **Security tooling**: Added `eslint-plugin-security`; `pip-audit` and `pnpm audit` steps in CI; ESLint disable comments for regex patterns in MarkdownRenderer, DocsPage, and ConversationViewer where required.
- **Vitest UI**: Vitest UI support and configuration updates for frontend testing.
- **Lint task**: Central `lint` task in Taskfile to run all linters.
- **Translations**: Added translations for `ingest_paper_message` in German, English, Italian, and Russian.
- **Build and CI**: cx_Freeze build dependencies in build-test workflow; Wine environment setup for Windows builds; multi-architecture build support (e.g. arm64 on Linux/Windows).

### Improvements

- **MicronParser**: DOMPurify integration and general improvements; DOMPurify initialization in frontend test setup.
- **NetworkVisualiser**: Level of Detail (LOD) management and icon cache optimization.
- **AudioWaveformPlayer**: Adjusted height, improved waveform rendering for dark mode, MutationObserver for responsive updates.
- **Interface discovery UX**: Discovery settings now include whitelist and blacklist fields in interface pages, and discovered announce overlays now show **Blacklisted** when matching blacklist patterns.
- **ConversationViewer**: `unknown` state for message delivery checks; animation direction control for syncing indicator.
- **Interface and MessagesSidebar**: Component improvements.
- **Propagation sync and markdown**: Improved propagation sync and markdown rendering.
- **Integrity management**: Advanced checks and metadata support; identity manager metadata loading and legacy migrator column handling.
- **Database backup and health**: Backup data-loss guards: baseline file (message count and total bytes) after each successful backup; detection of suspicious state (e.g. DB was non-empty and now empty, or size collapsed); when suspicious, backups written as `backup-SUSPICIOUS-*.zip` without overwriting good backups, rotation and baseline update skipped; rotation only applies to normal `backup-*.zip`. Database health checks at app start and close (integrity plus baseline comparison) with logging; issues exposed as `database_health_issues` on app and in `/api/v1/app/info`; toast notification when issues are present; websocket message type `database_health_warning` for real-time alert. Integrity result handling fixed for provider returning dict rows.
- **Vite**: API and WebSocket proxy configuration; sourcemaps disabled in build.
- **Node and tooling**: Node.js engine requirement set to >=24; Node 24 in Raspberry Pi install guide; pnpm 10.32.1; Node and pnpm version updates in Dockerfile and workflows; pip 26.0 in Dockerfile; pip install with `--no-cache-dir`.
- **Dependencies**: rns 1.1.3, Vuetify 3.12.1, Electron 39.7.0, autoprefixer 10.4.27, axios 1.13.6, Vue 3.5.29, serialize-javascript; ajv removed in favour of fast-json-stable-stringify and json-schema-traverse; various package and lockfile updates.
- **CI**: pnpm installation step in CI and test workflows; pnpm cache removed from CI/test workflows; ESLint security rule tuning.
- **Docs and legal**: README and TODO updates; LICENSE copyright holder updated from Sudo-Ivan to Quad4; Docker arch builder removed.

### Testing

- **Frontend**: Unit tests for multiple frontend components; AppPropagationSync and ConfirmDialog tests; accessibility tests for keyboard navigation and ARIA labels; MicronParser and NomadNetworkPage tests for partial handling.
- **Backend**: Backend test refactor. Database backup and health: unit tests for backup baseline, suspicious detection, rotation skip, and health checks (open/close, no baseline, baseline suspicious, integrity fail); property-based test for `_is_backup_suspicious`; mock test that `database_health_issues` is set on identity context setup when health check returns issues; tests to ensure health checks do not mistrigger (empty baseline, legitimate empty DB, small DB). Added discovery tests for whitelist/blacklist persistence, filtering behavior, and sanitization.
- **Security and fuzzing**: Extended fuzzing and security tests for messages and NomadNet browser: WebSocket handlers (nomadnet.download.cancel, nomadnet.page.archives.get, nomadnet.page.archive.load/add, nomadnet.file.download, nomadnet.page.download, lxmf.forwarding.rule add/delete/toggle, keyboard_shortcuts.set), NomadNet path variable parsing (convert_nomadnet_string_data_to_map), archived page lookup, and message get/delete by hash (single and bulk). Ensures robustness against malformed or adversarial input from the mesh.
- **Discovery fuzzing/security**: Added property-based and security fuzzing tests to validate discovery pattern sanitization and robustness of interface filtering under malformed or adversarial inputs.
- **HTTPS/WSS side-sniffing**: New tests in `test_https_wss_side_sniffing.py` to verify that when HTTPS is enabled, the server speaks TLS only on the API/WS port; plain HTTP connections receive no plaintext HTTP response so other local apps cannot sniff MeshChatX traffic; WSS over the same port is verified.
- **Scan workflow**: Trivy integration moved to unified scan.yml; Docker workflow Trivy exit code adjusted for successful builds; ZIP artifact build step removed from Gitea release flow.

## [4.1.0] - 2026-01-16

### New Features

- **Advanced Diagnostic Engine**: 
    - Mathematically grounded crash recovery system using **Probabilistic Active Inference**, **Shannon Entropy**, and **KL-Divergence**.
    - **Deterministic Manifold Constraints**: Actively monitors structural system laws (V1: Version Integrity, V4: Resource Capacity).
    - **Failure Manifold Mapping**: Identifies "Failure Manifolds" across the vertical stack, including RNS identity failures, LXMF storage issues, and interface offline states.
    - **Intelligent Integrity Monitoring**: 
        - Implemented **Shannon Entropy Analysis** for critical files and databases to detect non-linear content shifts (e.g., unauthorized encryption or random data injection).
        - Integrated **SQLite Structural Verification** via `PRAGMA integrity_check` to distinguish between binary hash changes (dirty shutdowns) and actual database corruption.
        - Refined ignore logic for volatile LXMF/RNS files to eliminate false positives in tampering detection.
        - Added advanced security alerts for content anomalies, signature mismatches, and critical component compromises.
- **RNS Auto-Configuration**: 
    - Automatic creation and repair of the Reticulum configuration file (`~/.reticulum/config`) if it is missing, invalid, or corrupt.
- **Expanded Security Pipeline**:
    - Integrated **Trivy** for both filesystem (codebase) and container image scanning.
    - Consolidated security scans into a unified `scan.yml` workflow for better visibility.
    - Updated container workflows to include fail-fast filesystem checks.
- **Network Visualiser Optimization**: 
    - Implemented **AbortController** support to cancel pending API requests on component unmount.
    - Added high-performance batch fetching for path tables and announces (up to 1000 items per request).
- **Announce Pagination**: 
    - Added backend and database-level pagination for announces to improve UI responsiveness in large networks.
- **Improved Installation**: 
    - Added support and documentation for installing via **Pre-built Wheels (.whl)** from releases, which bundle the built frontend for a simpler setup experience.

### Improvements

- **Reliability & Memory Management**: 
    - Fixed a major concurrency issue where in-memory SQLite databases (`:memory:`) were not shared across background threads, causing "no such table" errors.
    - Resolved `asyncio` event loop race conditions in `WebAudioBridge` using a lazy-loading loop property with fallback.
    - Refactored `IdentityContext` teardown to ensure all managers are properly nullified and callbacks cleared, preventing memory leaks and reference cycles.
    - Added client list cleanup in `WebAudioBridge` when calls end.
- **UI/UX**: 
    - Enhanced **LXMF link handling** with better rendering logic for `lxmf://` and `rns://` URIs.
    - Fixed a critical hang in the **Startup Wizard** where "Finish" or "Skip" buttons could become unresponsive.
    - Improved UI navigation safety by automatically closing the tutorial modal when navigating away.
    - Refined `MarkdownRenderer` regex patterns to prevent empty bold/italic tags and improved matching for single delimiters.
- **Infrastructure & CI**:
    - Added dedicated build scripts for **Arch Linux** packaging to handle permissions and `makepkg` execution.
    - Updated Docker dev-image workflows to trigger on master branch pushes.
    - Refactored telemetry data packing for more efficient location transmission.
    - Updated dependencies including **Electron Forge (7.11.1)**, **Prettier (3.8.0)**, and ESLint plugins for better stability and formatting.
- **Testing**: 
    - **Frontend UI Test Suite Expansion**: Added comprehensive Vitest suites for all diagnostic and utility tools (Ping, Trace, Probe, RNode Flasher, Micron Editor, etc.).
    - **Property-Based Testing**: Significant expansion with `hypothesis` to ensure robustness of the diagnostic engine, identity restoration, and markdown renderer.
    - **Integrity Validation Suite**: Added extensive property-based tests for entropy mathematical bounds and simulated corruption scenarios (SQLite b-tree breakage, content type shifts).
    - Added automated verification for Python version and legacy kernel compatibility diagnostics.
    - Configured temporary log directory management for tests to improve portability.

### [4.0.0] - 2026-01-03

Season 1 Episode 1 - A MASSIVE REFACTOR

### New Features

- **Banishment System (formerly Blocked):** 
    - Renamed all instances of "Blocked" to **"Banished"**, you can now banish really annoying people to the shadow realm.
    - **Blackhole Integration:** Automatically blackholes identities at the RNS transport layer when they are banished in MeshChatX. This prevents their traffic from being relayed through your node and publishes the update to your interfaces (trusted interfaces will pull and enforce the banishment).
    - Integrated RNS 1.1.0 Blackhole to display publishing status, sources, and current blackhole counts in the RNStatus page.
- **RNPath Management Tool:** New UI tool to manage the Reticulum path table, monitor announce rates (with rate-limit detection), and perform manual path requests or purges directly from the app.
- **Maps:** You can now draw and doodle directly on the map to mark locations or plan routes.
- **Calls & Audio:**
    - Added support for custom ringtones and a brand-new ringtone editor.
    - New **Audio Waveform Visualization** for voice messages, providing interactive playback with a visual waveform representation.
- **Paper Messages:** Introduced a tool for generating and scanning paper-based messages with built-in QR code generation for easy sharing.
- **LXMF Telemetry & Live Tracking**: 
    - Full implementation of Sideband-compatible (Still need to test Columba) telemetry (FIELD_TELEMETRY & FIELD_TELEMETRY_STREAM).
    - Live tracking with real-time map updates, distinct blue pulsing animations, and historical path tracing (breadcrumb trails).
    - Mini-chat integrated into map markers for quick communication with telemetry peers.
    - Privacy controls with global telemetry toggle and per-peer "Trust for Telemetry" settings.
    - Detailed telemetry history timeline with interactive battery voltage/percentage sparkline charts.
- **Documentation:** You can now read all the project guides and help docs directly inside the app.
- **Reliability:**
    - If the app ever crashes, it's now much better at picking up right where it left off without losing your data.
    - Added **Identity Switch Recovery**: mechanism to restore previous identities or create emergency failsafes if a switch fails.
    - Multi-Identity "Keep-Alive": Identities can now be kept active in the background when switching, ensuring you still receive messages and calls across all your personas.
    - Added **Database Snapshotting & Auto-Backups**: You can now create named snapshots of your database and the app will perform automatic backups every 12 hours.
    - Added **Emergency Comms Mode**: A lightweight mode that bypasses database storage and non-essential managers, useful for recovering from corrupted data or running in restricted environments. Can be engaged via UI, CLI flag (`--emergency`), or environment variable (`MESHCHAT_EMERGENCY=1`).
    - Added **Snapshot Restoration**: Ability to restore from a specific snapshot on startup via `--restore-from-snapshot` or `MESHCHAT_RESTORE_SNAPSHOT` environment variable.
- **Diagnostics:**
    - New **Debug Logs Screen**: View and export internal system logs directly from the UI for easier troubleshooting.
- **Community:** Better support for community-run network interfaces and checking TCP ping status of suggested interfaces.
- **UI Tweaks:** Added a new confirmation box for important actions and a better sidebar for browsing your archived messages.
- **Micron Editor:** Added multi-tab support with IndexedDB persistence, tab renaming, and a full editor reset button.
- **Desktop Enhancements (Electron):**
    *   **Multi-Window Calls:** Optional support for popping active calls into a focused 2nd window.
    *   **System Tray Integration:** The app now minimizes to the system tray, keeping you connected to the mesh in the background.
    *   **Native Notifications:** Switched to system-native notifications with deep-linking (click to focus conversation).
    *   **Protocol Handling:** Register as default handler for `lxmf://` and `rns://` links for seamless cross-app navigation.
    *   **Hardware Acceleration Toggle:** Power-user setting to disable GPU acceleration if flickering or glitches occur.
    *   **Power Management:** Automatically prevents system sleep during active audio calls to maintain RNS path stability.
- **Added Web Audio Bridge** which allows web/electron to hook into LXST backend for passing microphone and audio streams to active telephone calls.
- **Added LXMFy** for running bots.
- **Added RNS Discoverable Interfaces** https://markqvist.github.io/Reticulum/manual/interfaces.html#discoverable-interfaces and ability to map them (ones with a location).

### Improvements

- **Blazingly Fast Performance:**
    - **Network Rendering:** The Network Visualizer now uses intelligent batching to handle hundreds of nodes without freezing your screen.
    - **Memory Optimization:** Added a smart icon cache that automatically clears itself to keep the app's memory footprint low.
    - **Parallel Loading:** The app now fetches network data in parallel, cutting down startup and refresh times significantly.
    - **Lazy Loading:** Documentation and other heavy components now load only when you need them, making the initial app launch much faster.
    - **Smoother Settings:** Changing settings now uses "smart saving" (debouncing) to prevent unnecessary disk work and keep the interface responsive.
    - **Backend Efficiency:** A massive core refactor and new database optimizations make message handling and search nearly instantaneous. Added pagination to announce and discovery lists to improve performance in large networks.
- **Calling:** The call screen and overlays have been completely redesigned to look better and work more smoothly.
- **Messaging:** 
    - Polished the message lists and archive views to make them easier to navigate.
    - Added "Retry All" functionality for failed or cancelled messages in conversation views.
    - Improved handling of `lxm.ingest_uri.result` with detailed notifications for success/error/warning states.
- **Maintenance Tools:** Added new maintenance utilities to clear LXMF user icon caches and manage backup configurations.
- **Network View:** The visualizer that shows your network connections is now much clearer and easier to understand.
- **Languages:** Updated translations for English, German, and Russian. Added **Italian (it-IT)** localization. Added a toggle to easily enable or disable translation services.
- **Search:** The command palette (quick search) and notification bell are now more useful.
- **CartoDB Tiles** - some more styles if OSM is not enough for you, MBtiles will export tiles from the selected one.
- **Basic Markdown in Messages** - Support for basic markdown in messages

### Bug Fixes

- Fixed issues where switching between different identities could sometimes cause glitches.
- Fixed several small bugs that could cause messages to get stuck or out of order.
- Lots of small UI fixes to make buttons and menus look right on different screens.
- Fixed glitchy message page

### Technical

    - **Backend Architecture:**
    - Decoupled logic into new specialized managers: `community_interfaces.py`, `docs_manager.py`, `identity_manager.py`, `voicemail_manager.py`, and `nomadnet_utils.py`.
    - Added specialized utility modules: `meshchat_utils.py`, `lxmf_utils.py`, `async_utils.py`, and `identity_context.py`.
    - Implemented a robust state-based crash recovery system in `src/backend/recovery/`.
    - **Self-Healing Database Schema**: Enhanced `DatabaseSchema` with automatic column synchronization to prevent crashes when upgrading from older versions with missing columns.
    - Enhanced database layer with `map_drawings.py` and improved `telephone.py` schema for call logging.
    - Standardized markdown processing with a new `markdown_renderer.py`.
        - Added pagination support for announce queries in `AnnounceManager`.
    - **Performance Engineering & Memory Profiling:**
        - Integrated a comprehensive backend benchmarking suite (`tests/backend/run_comprehensive_benchmarks.py`) with high-precision timing and memory delta tracking.
        - Added an **EXTREME Stress Mode** to simulate ultra-high load scenarios (100,000+ messages and 50,000+ announces).
        - Implemented automated memory leak detection and profiling tests using `psutil` and custom `MemoryTracker` utilities.
    - **Full-Stack Integrity & Anti-Tampering:**
        - Implemented **Backend Binary Verification**: The app now generates a SHA-256 manifest of the unpacked Python backend during build and verifies it on every startup in Electron.
        - Added **Data-at-Rest Integrity Monitoring**: The backend now snapshots the state of identities and database files on clean shutdown and warns if they were modified while the app was closed.
        - New **Security Integrity Modal**: Notifies the user via a persistent modal if any tampering is detected, with a version-specific "do not show again" option.
- **Frontend Refactor:**
    - Migrated complex call logic into `CallOverlay.vue` and `CallPage.vue` with improved state management.
    - Implemented modular UI components: `ArchiveSidebar.vue`, `RingtoneEditor.vue`, `ConfirmDialog.vue`, and `AudioWaveformPlayer.vue`.
    - Integrated a new documentation browsing system in `src/frontend/components/docs/`.
    - Added custom Leaflet integration for map drawing persistence in `MapPage.vue`.
- **Infrastructure:**
    - Added `Dockerfile.build` for multi-stage container builds.
    - Introduced `gen_checksums.sh` for release artifact integrity.
    - **Comprehensive Testing Suite:**
        - Added 80+ new unit, integration, and fuzz tests across `tests/backend/` and `tests/frontend/`.
        - Implemented property-based fuzzing for LXMF message parsing and telemetry packing using `hypothesis`.
        - Updated CI coverage for telemetry and network interface logic.
    - Updated core dependencies: `rns`, `lxmf`, `aiohttp`, and `websockets`.
    - **Developer Tools & CI:**
        - New `task` commands: `bench-backend` (Standard suite), `bench-extreme` (Breaking Time and Space), `profile-memory` (Leak testing), and `bench` (Full run).
        - Added Gitea Actions workflow (`bench.yml`) for automated performance regression tracking on every push.
- **Utilize Electron 39 features:**
    - Enabled **ASAR Integrity Validation** (Stable in E39) to protect the application against tampering.
    - Hardened security by disabling `runAsNode` and `nodeOptions` environment variables via Electron Fuses.
    - Implemented **3-Layer CSP Hardening**: Multi-layered Content Security Policy protection across the entire application stack:
        1. **Backend Server CSP** (`meshchatx/meshchat.py`): Applied via `security_middleware` to all HTTP responses, allowing localhost connections, websockets, and required external resources (OpenStreetMap tiles, etc.).
        2. **Electron Session CSP** (`electron/main.js`): Shell-level fallback CSP applied via `webRequest.onHeadersReceived` handler to ensure coverage before the backend starts and for all Electron-rendered content.
        3. **Loading Screen CSP** (`electron/loading.html`): Bootloader CSP defined in HTML meta tag to protect the initial loading screen while waiting for the backend API to come online.
    - Added hardware acceleration monitoring to ensure the Network Visualiser and UI are performing optimally.
