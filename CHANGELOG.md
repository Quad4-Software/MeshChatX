# Changelog

All notable changes to this project will be documented in this file.

## [4.6.2] - 2026-05-06

### Fixed

- **Build backend**: Bytecode cleanup now only removes .pyc and .pyo files when a matching .py source file is present, so standalone compiled artifacts are not deleted accidentally.
- **Propagation sync**: Auto-select no longer lets a sync get stuck on an unreachable node. When `auto_propagation` is enabled and the current propagation node loses its path while syncing, the manager stops the stuck sync and evaluates candidates to find one with a working path. If no candidate works, the broken active node is removed rather than restored.

### Added

- **Android notifications**: JavaScript interfaces in MainActivity handle notifications and incoming calls from the web layer. NotificationUtils now covers incoming calls, missed calls, voicemails, and messages on Android, with comprehensive tests across Electron, Android, and browser fallback.
- **Telephony**: Voicemail session management and configuration updates.
- **Toasts**: Swipe-to-dismiss on touch devices. Horizontal swipes past 100px slide the toast out with opacity and transform feedback; shorter swipes snap back.
- **Mobile header**: Propagation node sync refresh icon (`refresh`) visible on small screens, mirroring the desktop button with the same loading spinner state and click handler.

### Changed

- **Dependencies**: RNS package updated to 1.2.3 and micron-parser dependency refreshed.
- **Vendored LXMFy**: Refreshed `vendor/lxmfy` from upstream [LXMFy/LXMFy](https://git.quad4.io/LXMFy/LXMFy) at `0a6ba8c9fd0f306be614d0edce44e4e805c025b0` (LXMF field helpers for structured bot commands, expanded docs, and new tests). Bundled package version remains **1.6.2**; `vendor/README.txt` lists the revision pointer.
- **CI**: Docker images publish the :latest tag on version tag pushes, main and master branch builds are enabled, and the Bunny Storage release folder is pruned before uploads.

## [4.6.1] - 2026-05-04

### Fixed

- **Micron pages (JavaScript renderer)**: Long lines on Micron pages now wrap more reliably instead of running off the edge awkwardly.
- **Nomad browser**: The Micron JavaScript / WebAssembly switch in the toolbar (and switching engines in general) works on every Micron page link, including ones with extra parameters in the address which caused issues.
- **macOS app (Intel + Apple Silicon in one download)**: Building the combined Mac app could fail with a merge error because some bundled audio pieces looked identical in both halves. The build now trims native add-ons to either Apple Silicon or Intel before they are merged, and install scripts on Mac CI rebuild the miniaudio piece from source when needed so the merge step succeeds.

## [4.6.0] - 2026-05-04

### TL;DR

- **Micron WASM parser**: Go-based **WASM** parser for Micron pages that falls back to JavaScript when WASM is unavailable or disabled. **Micron Parser JS stays the default renderer**. The **WASM engine** can stay enabled for updates while you choose **JavaScript or WebAssembly** as the default in settings or from the Nomad browser toolbar. The WASM binary is upgradable in settings (GitHub releases or local upload).
- **Security and integrity**: **SRI** checks for external scripts (Codec2, RNode Flasher) and Micron WASM with build-time manifests. Release workflows emit **SLSA provenance** for **Android APK** and **Flatpak**. **`SECURITY.md`** explains attestation alongside the SRI notes.
- **File downloads**: When you save or export things (including from archives), filenames are **cleaned up** so odd characters are less likely to break saves. You get **clearer feedback** when a download wraps up.
- **NomadNet favourites**: You can **import** and **export** your NomadNet favourites list on a new device without retyping everything. **Contact sharing** wording is clearer across several languages.
- **RNGit Explorer**: New in-app explorer for **RNGit**.
- **Android**: **Foreground sync** with notifications, **WebSocket** bridge hooks, **calls** and richer **audio** (including native attachments), **optional camera** manifest wiring, **APK sharing** via the system share sheet, plus **Lint** in CI and toolchain updates.
- **LibreTranslate**: Optional **API key** support for self-hosted or public instances with improved configuration persistence.
- **Bot management**: Subprocess **error tracking**, **log retrieval**, and better lifecycle handling for LXMFy bots.
- **Map improvements**: Removed **MapNoMapWarning** component, streamlined **offline mode** handling, and improved coordinate display with tabular formatting.
- **Telephony**: Call **metadata tracking** with **path hops** and **interface details**, plus **ringtone handling** for browser autoplay restrictions.
- **Reticulum and announces**: **Bootstrap-only** defaults for new **outbound TCP** and **backbone connector** interfaces (with discovery and add-interface options), **per-aspect announce storage** toggles in **`announce_manager`** and **`config_manager`**, and refreshed **community interface** presets (builder script and list cleanup).
- **Chat UI**: Clearer **outbound propagation** status in threads, **clipboard** helpers for secure and non-secure contexts, and **Tailwind CSS 4** with the **Vite** plugin and a slimmer frontend config footprint.
- **Settings and locales**: **Privacy**, **message auto-delete**, **community preset** strings, **bootstrap node search** copy, **LibreTranslate API key**, **migration** copy, **identity** and sending options, and **outbound propagation** status translations across supported languages.
- **Storage migration**: Reworked **legacy storage** migration with an **API**, **tutorial** choices, automatic **upstream folder** moves where needed, and aligned **Docker**, **Electron**, and test paths for old layouts.
- **Release CI**: Optional **Bunny Storage** uploads for release assets and clearer **tag resolution** in the main release workflow.

### Micron WASM parser (Micron-Parser-Go)

- **Micron-Parser-Go WASM**: Go-based WASM implementation for Micron page parsing with **word wrapping**, **space splitting**, and **ForceMonospace** CSS injection. **Micron Parser Go** is pinned to **v1.0.5**.
- **Configuration**: **Micron WASM engine** toggle (default **on**) allows loading and updating the WASM build. **`nomad_micron_default_engine`** (`js` or `wasm`, default **`js`**) sets the default Micron renderer separately from the toolbar. **`micron_parser_go_version`** pins the WASM binary version.
- **Dynamic loading**: WASM binary fetched and cached with **SRI verification** against **`integrity.json`** manifests.
- **Fallback behavior**: Graceful fallback to JavaScript parser when WASM is unavailable or fails to load.
- **Docker support**: Scripts fetch and resolve Micron WASM binaries during Docker builds with version pinning.

### Security and integrity

- **SRI verification**: Subresource Integrity verification for **Codec2** and **RNode Flasher** external scripts with **`integrity.json`** manifests. **Codec2** WASM loading uses **`locateFile`** so asset paths resolve reliably next to integrity checks.
- **Micron WASM integrity**: Generated **`integrity.json`** for Micron WASM assets with SHA-384 hashes verified at load time.
- **Security documentation**: Updated **`SECURITY.md`** with SRI details for external code and CI integrity tests plus **SLSA** notes for **APK** and **Flatpak** artifacts.
- **Community interfaces**: SSRF protection with URL validation and fetch handling for community directory requests.

### Bots and LXMFy

- **Bot error handling**: Subprocess **last error tracking** and **log retrieval** for bot instances via **`GET /api/v1/bots/{id}/logs`**.
- **LXMFy vendor integration**: Vendored **LXMFy** dependency for bot framework functionality.
- **Configuration**: Improved bot configuration persistence and validation in **`config_manager`**.

### LibreTranslate

- **API key support**: Optional **API key** field for LibreTranslate configuration in settings with secure storage.
- **URL validation**: **Loopback-only** URL normalization and validation for LibreTranslate service endpoints.
- **Configuration persistence**: Improved **`libretranslate_url`** and **`libretranslate_api_key`** handling with live probing.

### Map and visualization

- **Simplified offline handling**: Removed **MapNoMapWarning** component and streamlined offline mode logic.
- **Coordinate display**: Improved **tabular formatting** for coordinate readouts in the map UI.
- **Geolocation permissions**: Android **geolocation permissions** for map and LXMF telemetry functionality.

### Telephony and calls

- **Call metadata tracking**: Real-time display of **path hops**, **interface details**, and **RTT** during active calls.
- **Ringtone handling**: Improved **browser autoplay restriction** handling for ringtone playback with fallback strategies.
- **Telephone announcements**: Configurable **announcement enabling** for telephone functionality.

### Android platform

- **APK sharing**: **`shareApk`** method in **AndroidBridge** for sharing the installed APK via system share sheet.
- **File sharing utilities**: Native file sharing integration for mesh content.
- **Geolocation permissions**: Added **fine/coarse location** permissions for map and telemetry features.
- **Notification improvements**: Better **audio settings permission** handling and **back navigation** responsiveness.
- **Versioning**: Bumped to **4.6.0** with updated feature flags.

### Tools and path utilities

- **RN path trace**: Improved **error handling** and **validation** in path trace and probe handlers.
- **NomadNetwork pathfinding**: Integrated **reticulum pathfinding** into NomadNet downloads for better link establishment.
- **Failure detection**: Simplified **`isFailedPageContent`** method with dedicated tests for page load failure detection.

### Downloads, archives, and frontend utilities

- **Downloads**: File download flow adds **persistence**, **user notifications**, and **filename sanitization** so exports land predictably and bad names are rejected or normalized safely.
- **Refactors**: Download helpers and **time formatting** utilities consolidated. UI elements updated where downloads surface.
- **Tests**: **`DownloadUtils`** unit tests. **`Utils`** tests updated for formatting helpers. **`ArchivesPage`** test accounts for delayed **`downloadTextAsFile`** behaviour.

### NomadNet and locales

- **Favourites**: **Import/export** for NomadNet favourites from the app.
- **Locales**: **Contact sharing** options and related strings refreshed across supported languages. **RNGit Explorer** strings added and **localization tables** aligned for consistency.
- **Locales**: **Bootstrap node search** copy and settings strings for **privacy**, **message auto-delete**, and **community preset** management. **Outbound message propagation status** labels for the conversation UI.

### RNGit Explorer

- **Backend**: **`rngit_tool`** introduces the RNGit explorer capability.
- **Frontend**: **RNGit Explorer** page with **sidebar** and navigation integration plus a localized **experimental** footer notice.
- **Tests**: Coverage for **server behaviour** and **frequency conversion** paths used by the tool. Obsolete **RNGit database announcement conversion** test removed.

### Android

- **Gradle**: **Product flavors** removed. **Python sync** task simplified to match the single packaging path.
- **Paths**: **Taskfile** and CI workflows updated for the new **APK** and Python directory layout.
- **Docs**: Android README sections updated so they no longer talk about removed flavors.
- **Sync and notifications**: **Foreground service** for message synchronization with user-facing **notification** copy. **WebSocket** integration in **`meshchat_wrapper`** and an **Android push bridge** so the UI can react to backend events.
- **Reliability**: **Server loop control** and clearer **error handling** around the notification bridge.
- **Calls and media**: **Call handling**, **notification channels**, **permissions**, and **shortcuts**. **Native audio attachment** support with improved **message routing** and in-app **audio** navigation. **TelephoneNativeAudioSession** and **WavPcmAttachmentRecorder** encapsulate **record creation** and **permission** checks.
- **Manifest**: **Camera** added as an **optional** feature where appropriate. Duplicate optional **camera** and **microphone** feature declarations removed from **`AndroidManifest.xml`**.
- **Toolchain**: **Gradle** plugin and **SDK** bumps, dependency refresh, and **Lint** configuration.
- **CI**: **Android Lint** runs in the workflow with **report artifacts** uploaded for review.

### MeshChat UI, conversations, and microphone

- **Conversations**: **UUID**-based pending message hashing, **viewport resize** handling updates, **date divider** styling for accessibility, and list **previews** that prefer **display names** with small **telemetry** polish.
- **Getting started**: **Identity** screen added to the onboarding flow.
- **Audio**: Native **WAV** attachment availability checks and clearer **recording** source wiring.
- **Main shell**: **`App.vue`** uses a **polling guard** so refresh work cannot overlap.
- **Command palette and visualiser**: **Visualizer** entries trimmed from the command palette and **NetworkVisualiser** physics simplified.
- **Outbound status**: **`meshchat`** message updates accept a **method** parameter with **method-to-state** mapping so propagation outcomes read consistently. **`ConversationViewer`** shows clearer **propagation state** titles. Tests cover outbound propagation status behaviour.
- **Clipboard**: **`clipboardUtils.js`** improves **copy** / **read** for **secure** and **non-secure** contexts when **`navigator.clipboard`** is missing or rejects.
- **Layout**: Responsive **height** class tweaks on **`App.vue`** and **`AuthPage.vue`**.
- **Styling**: **z-index** values standardized and **class naming** cleaned up across multiple components.
- **Microphone**: **`microphoneRecorder`** can capture via **AudioWorklet** or **ScriptProcessor** for better **performance** and **compatibility** across environments.

### Desktop (Electron)

- **Storage and quit**: User data directory naming matches the migration layout. **Quit** handling is more predictable.

### Reticulum config, discovery, and display

- **Bootstrap-only interfaces**: Discovery and **Add Interface** flows can mark new **TCP client** and **backbone connector** interfaces **`bootstrap_only`** so Reticulum can detach them after **`autoconnect_discovered_interfaces`** is satisfied. Defaults stay configurable under **Interfaces**.
- **Announce storage**: **`announce_manager`** wires **per-aspect** persistence (**`announce_store_*`**) through **`config_manager`** so LXMF, telephony, NomadNet, propagation, and RNGit aspects can be stored or skipped independently.
- **Interface editor**: **`coerce_rnode_frequency_hz`** normalizes frequency values written into Reticulum config.
- **Discovery helpers**: **`parseRNodeFrequencyHz`** interprets frequency fields from API-style payloads.
- **Formatting**: **`formatFrequency`** in **`Utils`** rejects or handles **non-finite** values safely instead of producing garbage output.

### Community interface presets

- **`build_community_interfaces`**: JSON fetch uses a **dedicated interface builder** instead of a one-off fetch helper.
- **Preset list**: Removes **stale TCPClientInterface** bootstrap entries and adds **user-submitted** community interfaces.

### Version source and sync scripts

- **Single source of truth**: Runtime **version** is read from **`src/version.py`**, which is kept in lockstep with root **`package.json`** (including **`__init__.py`** where applicable).
- **`version:sync`**: Script updates **multiple files** in one pass. Follow-up fixes keep **README** version lines in translated docs **consistent** and easier to maintain.

### Repository server and bundled wheels

- **Bundling**: Logic to **stage a local MeshChatX wheel** into the bundled directory and refreshed **download** behaviour for repository assets.

### Database

- **Identifiers**: Sanitization for dynamic **PRAGMA** names and **WAL** checkpoint modes.
- **Startup**: Legacy inline migrator removed from default database init in favour of the dedicated migration flow.

### CI, release automation, and supply chain

- **GitHub Actions**: **Migrated** primary workflows from **Gitea**. Obsolete Gitea workflow files removed.
- **Workflow hygiene**: **Flatpak** CI cleaned up. Deprecated **Snap** build scripts removed from the tree.
- **Caching**: **Node.js** and **Poetry** caches added where workflows install tooling.
- **Docker publish**: Workflow gains **Docker Hub** integration, **tag generation**, and a **login** fix so credential detection output is used consistently.
- **Android release**: Workflow updates for **tag handling**, **signing secret** detection, **APK upload** behaviour, and **Lint** (see Android section for product impact). Tighter **APK** signing and build rules on **dev** and **master**.
- **macOS builds**: **Codec2** install path fixes for **x64** and improved **Homebrew** detection plus env setup for cross-arch jobs.
- **SLSA**: Release workflow generates **SLSA provenance** for **Android APK** and **Flatpak** artifacts (see **Security** section for docs).
- **Benchmarks**: **Taskfile** default **benchmark** task and workflow trigger alignment. Expanded benchmark suite covering **contacts**, **config**, **telemetry**, **debug logs**, **map drawings**, **voicemail**, and **access attempts** with JSON output and results caching.
- **Alert thresholds**: Updated benchmark alert and fail thresholds for improved variance handling in CI.
- **Draft releases**: Script sets **`GH_REPO`** from **`GITHUB_REPOSITORY`** when unset.
- **Asset attestations**: Workflow **excludes additional file types** from attestation and **disables tlog upload** where that was causing friction.
- **Trivy**: Build and **security scan** workflows include explicit **setup** and **update** steps. Install script gains **upstream verification** and **cosign** integration.
- **pip-audit**: **`CVE-2026-3219`** ignored temporarily with a documented rationale until an upstream fix lands.
- **Tests**: Minor **formatting** tidy-ups in the test tree. **`test_app_status_tracking`** uses **`4.6.0`** as the example **`changelog_seen_version`** stamp so it tracks the release. Added coverage for **`android_push_bridge`**, **`meshchat_wrapper`**, **`rngit_tool`**, and **Micron WASM** (including wrapper server loops, frequency conversion, and WASM loading). **`http_api_routes.json`** contract updated for new routes. **Transport** announce-handler registration test expectation fixed. **NomadNetwork** regression tests for WebSocket download status. **Telephone initiation** timeout increases for stability. **MarkdownRenderer** lxmf link detection tests. **WebSocketConnection** invalid JSON frame handling.

### Docker, compose, and documentation

- **Dockerfile**: Optional **reproducible native build** target wiring. **OCI**-style metadata and **image source** hints refined. **`docker-compose.yml`** image reference and **volume** layout aligned with README examples. Build context drops unnecessary **legacy Tailwind** config files.
- **Flatpak**: Custom **desktop** template, permission tweaks, and removal of the **Pipewire** socket from the Flatpak config.
- **Docs**: **README** and translated READMEs add **Docker Hub** and **GHCR** guidance plus **copy-paste `docker run` examples** where helpful. **Browser requirements** called out where relevant. **Official GitHub mirror** links refreshed. **GitHub Actions** references replace Gitea-era wording. **Security policy** and **SECURITY** formatting polish. **Raspberry Pi** install examples use **`bash`** fences consistently.

### Tailwind and Vite frontend

- **Tailwind CSS 4.2.4** with **`@tailwindcss/vite`**. Obsolete **Tailwind config** files removed and **`style.css`** updated for the new setup.

## [4.5.1] - 2026-04-24

### Identity switching

- **Hotswap API**: Identity switch responses now include **display name** and **identity hash** so the client can refresh state without guessing from partial payloads.
- **Event handling**: Identity switch events are **deduplicated** in **`App.vue`** and **`IdentitiesPage.vue`** so rapid or repeated signals do not stack duplicate work.
- **Locales**: Confirmation copy for switching identities no longer tells users to restart when that is not required (aligned strings across supported languages).
- **Tests**: New **HTTP** coverage for the identity switch API (success paths, validation, and error responses).

### Desktop (Electron)

- **Boot experience**: **Splash screen** on startup and **Codec2** loader scripts use **retry** logic so transient load failures are less likely to strand voice features.
- **Developer tools**: **F12** toggles **DevTools**; the menu bar **auto-hides** in main windows for a cleaner ui.
- **Content Security Policy**: CSP now allows **`wasm-unsafe-eval`** and **blob:** where needed so **WebAssembly** used by the stack (for example audio codec paths) can run under the hardened policy.

### Microphone and translations

- **Recording**: Microphone capture updates **error handling** and adjusts **AudioWorklet** import so failures surface more reliably instead of failing silently.
- **Locales**: New and updated strings for **microphone** errors so users get clearer guidance when capture or permissions go wrong.

## [4.5.0] - 2026-04-23

### TL;DR 

- **Android App!**: MeshChatX now has a native Android app you can install (not just for Termux users).
- **Linux Packaging**: Added **Snap** and **Flatpak** initial support.
- **Copy Messages**: Added right-click context menu item to copy a message.
- **Sync Messages**: When you tap **Sync Messages**, you’ll just see a simple "Syncing..." label instead of weird technical terms.
- **Dark Mode Improvements**: The dark theme’s accent colors now look more consistent and easier on the eyes.
- **Announcements**: The app now handles timed announcements and reminders in a way that's more predictable and easy to understand.
- **Hot Reload RNS**: You can now restart the Reticulum network stack directly from MeshChatX if there’s a problem.
- **Config Editor Tool**: Added config editor tool to edit within app.
- **Repository Server Tool**: New **Tool** for the optional local file shelf to redestribute reticulum and meshchatx python wheels locally or any file you upload. 
- **Dangerous Links**: The app can warn you before you open links from people you don’t know, if you happen to click on it by mistake.
- **Message Rules**: New sieve tool for simple patterns—matching stuff can land in the right folder, quiet the notification bell, or other actions you pick.
- **Chats, Images and Reactions**: Bigger chats load faster, images are grouped and sized better, styling improvements to reactions.
- **Looks and Effects**: You can make parts of the UI transparent or enable a "glass effect" look, with clear settings to control these options.
- **Simpler Internals**: The app’s settings and chat features were reorganized behind the scenes, making it easier to maintain and more stable.
- **Visualiser Improvements**: The visualiser now handles really big or complex networks much more smoothly. Also added better incremental hop slider and set default to 4 hops for faster and less laggy loading. The slider will also remember what you set.
- **Easier Device Connections**: Advanced users can now see special codes (IFAC) that help with connecting certain types of interfaces here and via the API. 
- **Better Reliability**: The desktop (Electron) app recovers better from connection problems and crashes.
- **Audio Without ffmpeg**: Voicemail, ringtones, and microphone capture use in-process encoding (**LXST** / **miniaudio**) so containers and minimal installs no longer need an **ffmpeg** binary for those paths.
- **Calls and Microphone**: Picking input and output devices is less fiddly, permission edge cases recover more gracefully, and the microphone path through the browser stack has improved.
- **Bundled Offline Docs**: In-app documentation can include the **Reticulum manual**, fetched at build time and bundled for offline reading; the docs page upload and sharing flow is smoother. Docs will also actually start on proper manual page.
- **More Languages**: Spanish, French, Dutch, and Chinese options were added to the app’s language selector.
- **Message Size Limits**: You can now set how big incoming messages can be (from 1MB up to 1GB) with easy presets or custom values. 
- **Interface Options**: The Add Interface page now exposes the full set of options the Reticulum stack supports.
- **Map**: Another free map style, improve tile caching to show offline, mbtiles take priority, and improved markers.
- **Nomad Browsing Path Finder**: Path finder tool that shows on failed links to pages, allowing you to manually try a bunch of path finding methods.

### Platform and backend

- **MeshChat utils**: **`convert_propagation_node_state_to_string`** maps **`LXMRouter.PR_PATH_TIMEOUT`** to **`path_timeout`** so the API can report path timeouts distinctly from other failures.
- **Propagation nodes / sync**: Local propagation node lifecycle (start/stop/restart), stats and sync APIs; sync path logic for **outbound propagation nodes**, **immediate completion** for **local** nodes, and peer/unpeered statistics; settings expose **transfer limits in MB** and related UI/API wiring.
- **LXMF incoming delivery limit**: **`PATCH /api/v1/config`** clamps **`lxmf_delivery_transfer_limit_in_bytes`** to at most **1 GiB** (was 100 MB); **`LXMRouter.delivery_per_transfer_limit`** updates live when the value changes.
- **Auto-announce / intervals**: Refactor around **`interval_action_due`** in **`meshchat.py`** to simplify when auto-announce and propagation sync checks run; add tests for auto-announce behaviour.
- **Reticulum**: User-triggered **RNS restart** with UI feedback; **reload** streamlines teardown, loading indicators, and cleanup of identity state during Reticulum reload.
- **Notifications**: Filters **silent or non-user-facing** LXMF payloads so the notification bell does not fire on control-only traffic.
- **LXMF sieve filters**: **`lxmf_sieve.py`** with **`GET`/`PUT /api/v1/lxmf/sieve-filters`**; **`normalize_lxmf_sieve_filters`** / **`parse_lxmf_sieve_filters_json`**; rules match peer/message text (**substring** or **regex**) and can **suppress notifications**, **hide** peers, **route to folders**, or **banish**; wired through ingest, sidebar, and notification paths; **`config.lxmf_sieve_filters_json`** persistence; tests **`test_lxmf_sieve.py`**, **`test_lxmf_sieve_fuzz.py`**.
- **Announce trimming**: **`trim_announces_for_aspect`** keeps **favourited** destinations and **saved contacts** when capping announce noise.
- **Map**: **Deduplication** helpers for **telemetry** markers and **discovered** map nodes; **geodesy** helpers, **tile network** management, **OpenFreeMap** support, and **MBTiles** export **tile limit** plus **unique tile** counting in **`map_manager`**; tile caching refactor.
- **AutoInterface / user guidance**: Detects **bind/listen failures** (e.g. address already in use) and emits clear **operator guidance**.
- **Interface discovery**: Connect logic honours **autoconnect** metadata from discovery responses when the stack provides it.
- **Translation (Argos)**: Refactored **Argos Translate** CLI detection; integration tests for **forwarding** behaviour.
- **Docs bundle**: **`scripts/build/fetch_reticulum_manual.py`** (via **`pnpm run build-docs`**) fetches the **Reticulum manual** for offline docs; backend wiring serves bundled manual content.
- **Bots**: **`bot_handler`** updates for LXMF address normalization, reading addresses from sidecar files, improved bot names and on-demand announce requests, and tests.
- **Telephony**: **`TelephoneManager`** improvements for path discovery, initiation, polling, and cancellation; integration tests for LXST classes and WebAudioBridge mocks.
- **WebAudioBridge**: Adds a client only when a **call** is actually active.
- **Codec2 microphone**: **`Codec2MicrophoneRecorder`** uses a **silent tap** for processing and resumes the **audio context** reliably.
- **Microphone (worklet)**: **AudioWorklet**-based mic processing and audio graph wiring; ESLint **`AudioWorklet`** globals for worklet modules.
- **Repository server**: **`RepositoryServerManager`** (**`repository_server_manager.py`**) with **`/api/v1/repository-server/`** status, **list**, **upload**, **delete**, **refresh-bundled**, and HTTP **start**/**stop**/**restart**; wheel fetch uses **urllib** only (no **pip** subprocess); file copy skips existing files only when **size** matches; **`fetch_repository_wheels.py`** and build wiring for **bundled** wheels; **`repository-server-bundled`** kept out of generic **package data** where appropriate.
- **App info / diagnostics**: **`/api/v1/app/info`** (and related handlers) with safer memory, network, and database stats; tests for missing runtime objects and version resolution without the packaging module.
- **Media conversion**: Voicemail, ringtones, and **MicrophoneRecorder** capture use **WAV/PCM** and **OGG/Opus** via **LXST** with **miniaudio** instead of shelling out to **ffmpeg** (Alpine Docker images drop the **ffmpeg** package accordingly). Browser-recorded **WebM**/**Opus** attachments decode through the same **`audio_codec`** path and re-encode to **OGG/Opus** for LXMF; if conversion fails the original bytes are passed through unchanged. Python **JIT** status surfaced where applicable; related tests updated.
- **Docs manager**: Safer forced directory removal (**`_remove_tree_force_writable`**) and writable-directory helpers when replacing tree content; clearer document **sourcing** and **rendering** for in-app docs.
- **Python / tooling**: **Poetry** lock updated (e.g. **2.3.4**); **rns** **>=1.1.9** and **lxmf** **>=0.9.6**; **lxmfy** pinned to a compatible commit; **Electron** **41.x** series; **Node** engine **>=24** with **pnpm** store **integrity** verification in **`.npmrc`** and CI install scripts; lockfile/git-URL dependency style updates; **`package.json`** metadata adds desktop entry, vendor, and synopsis where applicable.
- **Build / unify**: Script to align **per-architecture cx_Freeze** outputs so unified bundles stay consistent across arches; post-freeze **cleanup** strips redundant **`meshchatx`** public assets and trims Python bloat; **`electronLanguages`** lists packaged locales; **`cx_setup.py`** excludes extra modules and bumps **optimize**.
- **Android runtime integration**: Added Android app startup hardening for Chaquopy and WebView, including startup retries, in-app startup errors, runtime permission flow (audio/Bluetooth/notifications/microphone), battery optimization exemption, ABI splits, optional local wheel builds (bcrypt/psutil recipes, Rust for bcrypt, PyO3/OpenSSL-related patches), cryptography and WebView media tweaks, and release minification rules for APK builds; **Gradle** **slim** / **full** **product flavors** with **repository-bundled** wheels for the fuller variant; Chaquopy-synced Python trees ignored in **`.gitignore`** / **`.prettierignore`**; APK signing glob fix in **`sign-android-apks.sh`**.
- **Licensing**: Relicensed Quad4-owned portions under **0BSD** and kept upstream **Reticulum MeshChat** portions under their original **MIT** notice in **`LICENSE`**. **SPDX** identifiers added across the tree; **`license_scope_mapper`** assists SPDX recommendations; **`licenses_collector`** enriches frontend dependency notices (**package.json** parsing, workspace-root filtering, detailed **`THIRD_PARTY_NOTICES`** / **`licenses_frontend.json`** generation).
- **GIFs**: Schema and **`database.gifs`** DAO; **`gif_utils`** validation and naming; HTTP **`/api/v1/gifs`** CRUD, **`…/image`**, import/export, use-from-message, and **`DELETE /api/v1/maintenance/gifs`**; configurable limits via **`config_manager`** where applicable.
- **Sticker packs**: **`database.sticker_packs`** and **`sticker_pack_utils`**; **`/api/v1/sticker-packs`** (list, create, install, reorder, delete, export) complementing per-sticker routes; stickers DAO/schema updates for pack association and animated assets.
- **Reticulum config file**: **`GET`/`PUT /api/v1/reticulum/config/raw`**, **`POST …/reset`**, with editor-focused tests and safe merge behaviour against **`config_manager`**.
- **Media hardening**: Backend and frontend tests for **GIF**, sticker, and Lottie paths (**fuzzing**, HTTP media routes, size/type checks).
- **LXMF send path**: Clearer handling and diagnostics when **message sending** fails (timeouts, path errors); tests cover failure modes.
- **Interfaces API**: Discovery responses include **IFAC** fields where the stack provides them; tests for discovery behaviour.
- **Interfaces API (full options)**: **`POST /api/v1/reticulum/interfaces/add`** now accepts the full RNS option matrix per interface type. **AutoInterface** persists **`group_id`**, **`discovery_scope`** (validated against `link`/`admin`/`site`/`organisation`/`global`), **`discovery_port`**, **`data_port`**, **`multicast_address_type`** (`temporary`/`permanent`), **`devices`**, **`ignored_devices`**, and **`configured_bitrate`**. **TCPClientInterface** gains **`connect_timeout`**, **`max_reconnect_tries`**, and **`fixed_mtu`** alongside existing **`kiss_framing`**/**`i2p_tunneled`**. **TCPServerInterface** adds **`i2p_tunneled`**. **BackboneInterface** now supports a **listener mode** (**`listen_ip`**/**`listen_port`**/**`device`**/**`prefer_ipv6`**) in addition to the existing connector mode. **RNodeInterface** persists **`flow_control`** and **`id_callsign`**. **KISSInterface**/**`AX25KISSInterface`** persist **`flow_control`**, **`id_callsign`**, and **`id_interval`** in addition to the existing serial/framing knobs. **I2PInterface** exposes the **`connectable`** flag.
- **Interfaces port-in-use validation**: New **`meshchatx/src/backend/interface_port_check.py`** module probes the requested host/port before the configuration is written. **TCPServerInterface** and **BackboneInterface** (listener mode) listen-port collisions, **UDPInterface** listen-port collisions, and **AutoInterface** **`discovery_port`**/**`data_port`** collisions return **HTTP 409** with a translated message (host, port, and conflicting interface name) so the operator can pick a free port instead of restarting into a broken interface.
- **Wifi transport**: **`WifiTransport`** open paths use simplified signatures and stricter validation.

### Frontend and UX

- **Propagation sync (App header)**: After **`GET /api/v1/lxmf/propagation-node/sync`**, the client **polls** propagation status on an interval while the router is in a transfer state, updates a **keyed loading toast** (`propagation-sync-status`) with translated strings (**`app.propagation_sync_live`**, **`app.propagation_sync_state.*`**), dismisses it when the transfer ends, then shows the existing success or error summary. Stopping sync clears the poll timer and dismisses the live toast; **beforeUnmount** cleans up if you leave the page mid-sync. Removed the old toolbar pattern **`Syncing... ({state})`** in favour of **`app.syncing`** plus the toast.
- **Link detection**: Updated **Reticulum link detection** to support **`lxmf:`** prefix and prevent false positives for bare hashes. **`link-utils`** now validates URLs more strictly before rendering.
- **Propagation nodes UI**: Settings and tools surface propagation node controls, transfer limits (MB), sync, and Material icons for node state; locales updated.
- **Incoming message size (Settings / Propagation Nodes)**: Preset selector (**1 MB**, **10 MB**, **25 MB**, **50 MB**, **1 GB**) and **custom** amount with **MB** or **GB** unit; shared helpers in **`meshchatx/src/frontend/js/settings/incomingDeliveryLimit.js`**; **en** / **de** / **it** / **ru** strings (**`app.incoming_message_size*`**).
- **Stranger links and sidebar**: Config options for **warning on stranger-originated links** and **Messages sidebar position**; UI and **en** / **de** / **it** / **ru** strings.
- **Theme**: Dark theme accent palette updates for consistency; tests adjusted where they assert colors.
- **Appearance**: **UI transparency** and **glass effect** settings (with i18n) and related layout tweaks in **`ConversationViewer`** and scrolling behaviour.
- **Message list performance**: **`@tanstack/vue-virtual`**-based virtualization, image group display, and shared scroll utilities for long threads.
- **Links and Markdown**: **`link-utils`** hardening (anchor protection, trailing punctuation); **Markdown** fixes for underscores in links vs italics with expanded tests.
- **Modularity (settings and messages)**: Config fetch/merge, **`PATCH /api/v1/config`**, color normalization, transport enable/disable, maintenance HTTP calls, and visualiser **`localStorage`** prefs live in **`meshchatx/src/frontend/js/settings/`** (`settingsConfigService`, `settingsTransportService`, `settingsMaintenanceClient`, `settingsVisualiserPrefs`); **`SettingsPage`** delegates to those modules. Message renderability, telemetry-only detection, image-only detection, and drag/paste image extraction are in **`conversationMessageHelpers.js`** with thin **`ConversationViewer`** wrappers.
- **Shell and settings UI**: Emergency and WebSocket status banners extracted to **`AppShellBanners.vue`**; conversation peer chrome to **`ConversationPeerHeader.vue`**; reusable **`SettingsSectionBlock.vue`** (used for the stranger-protection section).
- **Pages polish**: **About**, **Call**, **Debug logs**, and **Settings** pages with clearer layout, app info, environment paths, log copy-to-clipboard, and error handling; related tests.
- **Call (audio devices)**: **`getUserMedia`** fallback and clearer error handling when inputs/outputs or permissions misbehave.
- **ConversationViewer**: File input clears after selection and improves image-type detection for uploads; **GIF** picker and drag/drop upload to the GIF library; animated stickers and GIFs can use **`InViewAnimatedImg`** so heavy animations run only when visible.
- **Stickers UI**: **`StickerPacksManager`**, **`StickerEditor`**, **`StickerView`**, and **`tgsDecode`** (`.tgs` / Lottie JSON) integrate with the composer and identities settings.
- **Tools**: **`ReticulumConfigEditorPage`** for editing Reticulum configuration from the app with validation feedback; **`RepositoryServerPage`** (**`/tools/repository-server`**) for **status**/**list**, **HTTP** server **start**/**stop**/**restart**, **upload**/**delete**, and **refresh-bundled** against **`/api/v1/repository-server/`** (command palette + **Tools** grid); **RNode** firmware tooling gains expanded **diagnostics**, **device management**, and **i18n** for flash and probe flows.
- **Docs page**: **`DocsPage`** upload and sharing behaviour polished alongside offline manual bundling; Reticulum manual links follow the **active locale** where applicable.
- **Sieve Filters page**: **`SieveFiltersPage`** with **`GET`/`PUT /api/v1/lxmf/sieve-filters`** wiring and notification-suppression behaviour in the UI; route and sidebar/tool entry points; i18n for rule copy.
- **NomadNetwork**: **Path finder** dropdown and improved **error** handling when a page load fails; translated strings.
- **Telemetry**: **Telemetry history** modal with **battery** sparkline/chart components for timeline review.
- **Map UI**: **OpenFreeMap** and tile URL config updates; **bearing** mode; **vector exchange** panel; improved **export** UX; **map link** utilities on **conversation** messages; query-param handling and clearer **error** toasts; marker **clustering** and **drawing** component refactors; **`willReadFrequently`** on read-heavy **canvas** paths; **`clampFloatingToViewport`** shared helper so **dropdowns** stay inside the viewport (**`DropDownMenu`** and other surfaces).
- **Electron shell**: **CSP** allows **OpenFreeMap** image/font/connect sources alongside existing tile providers.
- **Fonts and map deps**: **`@fontsource/noto-sans`**, **`jszip`**, and pinned/patched **`ol`** / **`ol-mapbox-style`** for vector map styling.
- **LXMF reactions**: **Reaction** controls and message row layout tuned for small screens and long emoji strips.
- **Add Interface page (full options)**: **`AddInterfacePage.vue`** renders type-specific sections for every option the backend now accepts. **AutoInterface** has a dedicated form (**Group ID**, **Discovery Scope**, **Multicast Address Type**, **Discovery Port**, **Data Port**, allowed and ignored devices, configured bitrate). **TCP Client** exposes **KISS framing**, **I2P tunneled**, **connect timeout**, **max reconnect tries**, and **fixed MTU** toggles/fields. **TCP Server** / **UDP** add **device** and **prefer IPv6** controls; **TCP Server** also exposes **I2P tunneled**. **BackboneInterface** has a **Listener mode** toggle that swaps between connector (remote/target/transport identity) and listener (listen IP/port/device/prefer IPv6) layouts. **RNode** sections add **spreading factor**, **coding rate**, **flow control**, **ID callsign**, **ID interval**, and **airtime limit long/short**. **Serial**/**KISS**/**AX.25 KISS** sections expose **baud rate**, **data bits**, **parity**, **stop bits**, **preamble**, **TX tail**, **persistence**, **slot time**, **flow control**, **beacon callsign/interval**, and **AX.25 callsign/SSID**. **I2P** gains a **connectable** toggle. Every new field round-trips through **`saveInterface`**, **`loadInterfaceToEdit`**, **`applyConfig`**, and **`buildPayloadFromImportedConfig`** so editing and quick-import flows keep parity with the form.
- **Network visualiser**: Chunk and icon rendering tuned for large node sets (see TL;DR); optional **max hops** filter with **`localStorage`** persistence alongside the hop slider prefs.

### CI and packaging

- **CI hygiene**: **pnpm** store caching removed from CI and security-scan workflows; **CodeQL** for GitHub with **`build-mode: none`** (no manual build block); install scripts run **`poetry check`** and verify **pnpm** store **integrity**; Linux runners install **libopus** / **libogg** so Opus encode tests pass.
- **Supply-chain monitoring**: **Rekor** monitoring workflow plus **`rekor-cli`** install helper script.
- **Release assets**: **GitHub** release notes generation includes **integrity** / **SBOM**-style detail; per-file **SHA256** sidecar checksums removed from the main build-test flow; **`SECURITY.md`** points readers at **cosign** / attestation-style verification instead.
- **Frontend CI**: Reusable **frontend build** workflow shared across Android, container, and packaging jobs; default **`pnpm test`** uses **`vitest run`** for the web suite plus **`vitest.electron.config.js`** for Electron helpers.
- **Docker**: **Git** installed for frontend build steps; **corepack** replaced with **npm**-based **pnpm** install; Python base image refresh (e.g. **3.14**-series Alpine), venv runtime tools, pip/setuptools updates; **`g++`** in build deps for **miniaudio** compile paths; **`.dockerignore`** / **`.gitignore`** tweaks; workflow git clone/fetch handling for reproducible image builds; **`README.md`** included in the **Dockerfile** copy context; container **entrypoint** path updated; **ffmpeg** removed from Alpine package lists now that audio encoding is in-process.
- **Electron / Linux**: AppImage pipeline builds **x64** and **arm64** artifacts; **Electron Forge** adds optional **Snap** and **Flatpak** makers (see **`forge.config.js`** and local packaging scripts); **Flatpak** **25.08** runtime/base alignment, **Flathub** remote bootstrap script, and packaging script tweaks; **Snap** **core22** base prep and multi-snap install for destructive-mode builds; Forge **temp-dir** helper for packaging; **`resetAdHocDarwinSignature`** on **Darwin**; platform-specific **resource** handling fix in the Electron packager path.
- **Desktop build scripts**: **macOS** and **Windows** scripts can consume **prebuilt frontend** output when present to shorten release builds.
- **Android CI**: Workflow runs **Node.js** setup and **frontend build** before APK packaging so Web assets stay in sync with the app bundle; **slim**/**full** flavor alignment with **bundled** repository wheels where applicable; **NDK** / **sdkmanager** steps tolerate preinstalled SDK tooling; **Taskfile** gains flavour/ABI/l10n-test polish and cleanup steps.
- **Docs**: Raspberry Pi install guide expanded with automated setup scripts and service-oriented instructions; root **README** and translated install docs note **Poetry** **2.3.4** and **pnpm** **v10+** lifecycle behaviour; **README** APK section calls out **slim** vs **full** / ABI packaging; **NomadNet** browser and **Mesh Server** page documentation added.
- **Container / compose**: **`docker-compose.yml`** and related Docker notes updated; optional **`Dockerfile.extra`** for layered builds where documented.

### Security

- **Android WebView**: **`MainActivity`** **`WebViewClient.shouldOverrideUrlLoading`** blocks top-level navigations except **`http`/`https`** to **loopback** hosts (**`127.0.0.1`**, **`localhost`**, **`::1`** / **`[::1]`**), plus **`about:blank`**, **`blob:`**, and **`data:`**, so external clearnet URLs cannot be opened inside the embedded browser.
- **Electron shell paths**: **`showPathInFolder`** and **`openPath`** IPC handlers validate paths against allowed roots (**default storage**, **Reticulum config**, **`userData`**, **temp**, **downloads**, **documents**, **portable** bundle dir when set, and **`--storage-dir`** / **`--reticulum-config-dir`** from argv) via **`electron/shellPathGuard.js`**; out-of-tree paths are rejected.
- **LibreTranslate / SSRF**: Client-supplied **`libretranslate_url`** (languages query and translate JSON) must target **loopback** only (**`http_url_guard.normalize_loopback_http_service_base`**); server default **`LIBRETRANSLATE_URL`** is unchanged. Outbound LibreTranslate **`aiohttp`** calls use **`allow_redirects=False`**. Invalid URLs return **HTTP 400** from the translator API routes.
- **CSP**: Removed **`'unsafe-eval'`** from default script policy; **main SPA** responses use **`script-src 'self'`** only, while **`/rnode-flasher/`** and **`/reticulum-docs/`** keep **`'unsafe-inline'`** for their inline scripts. **Service worker** registration moved from **`index.html`** into **`main.js`** so the shell does not rely on an inline script tag. Electron session **fallback CSP** drops **`'unsafe-eval'`** as well.
- **Electron external URLs**: **`electron/safeExternalUrl.js`** **`normalizeExternalUrlForOpen`** gates **`shell.openExternal`** in **`electron/main.js`** (**`setWindowOpenHandler`** fallback and context-menu **Open link**) and **`electron/main-legacy.js`**, allowing only **`http:`**, **`https:`**, and **`mailto:`**; **`javascript:`**, **`data:`**, **`file:`**, and other schemes are dropped. **`tests/electron/safeExternalUrl.test.js`** adds regression and light fuzz coverage.
- **Chat link rendering**: **`meshchatx/src/frontend/js/LinkUtils.js`** **`renderStandardLinks`** validates detected URLs with the **`URL`** constructor (with an **`&amp;` → `&`** retry for HTML-escaped query strings), omits linkification when parsing fails or the scheme is not **`http`/`https`**, excludes **`'`** and **`"`** from the autolink detector tail, HTML-escapes link labels, and HTML-escapes **`data-nomadnet-url`** attribute values. **`tests/frontend/LinkUtils.test.js`** / **`MarkdownRenderer.test.js`** updated for canonical **`href`** output.
- **Tests**: **`tests/backend/test_http_url_guard.py`** (loopback URL edge cases and rejections), **`tests/electron/shellPathGuard.test.js`**, and **`tests/electron/safeExternalUrl.test.js`** cover URL and path rules.
- **Repository uploads**: **`tests/backend/test_repository_server_manager.py`** parametrized rejects for **`save_upload`** filenames outside **`_safe_any_upload_filename`** (**`repository_server_manager.py`**).
- **Map deep links and map ping classification**: **`meshchatx/src/frontend/js/mapLinkUtils.js`** **`mapLinkKindFromMessage`** now requires the localized **MeshChatX map ping** prefix at the **start** of the message (after optional whitespace) with a **word boundary**, so a ping cannot be spoofed by embedding that phrase inside HTML or other text. Backend coverage in **`tests/backend/test_deep_links_security.py`** for **`lxm.ingest_uri`** **`meshchatx://map` / `meshchat://map`** (including XSS-shaped **`layers`** / **`label`** query values and Hypothesis fuzzing); frontend coverage in **`tests/frontend/mapLinkUtils.security.test.js`**, **`tests/frontend/deepLinks.protocol.security.test.js`**, and updates to **`tests/frontend/mapLinkUtils.test.js`**.
- **Interface discovery numerics**: **`meshchatx/src/frontend/js/interfaceDiscoveryUtils.js`** **`numOrNull`** only accepts **`string`** and **`number`** (no **`Number([])`**, **`Number({ valueOf })`**, or other object coercion). **`tests/frontend/interfaceDiscoveryUtils.security.test.js`** and **`tests/frontend/interfaceDiscoveryUtils.test.js`** cover edge cases.
- **Discovered interface list payloads (backend)**: **`tests/backend/test_discovered_interfaces_security.py`** fuzzes **`ReticulumMeshChat.discovery_filter_candidates`**, **`matches_discovery_pattern`**, **`sanitize_discovery_patterns`**, and **`filter_discovered_interfaces`** with very long names, HTML/script-like strings, and arbitrary extra keys, and asserts **`json.dumps`** on filtered results.
- **Stickers, GIFs, and LXMF reactions (backend + frontend)**: **`tests/backend/test_media_sticker_reaction_gif_security.py`** Hypothesis-fuzzes **`meshchatx/src/backend/sticker_utils.py`** (**`sanitize_sticker_name`**, **`sanitize_sticker_emoji`**, **`normalize_image_type`**), **`gif_utils`** (**`sanitize_gif_name`**, **`normalize_image_type`**, **`validate_gif_payload`** / export documents), **`sticker_pack_utils`** pack string sanitizers, and **`lxmf_utils.convert_lxmf_message_to_dict`** with hostile **`app_extensions`** reaction fields. **`tests/frontend/lxmfReactions.test.js`** and **`tests/frontend/inViewObserver.test.js`** add reaction-merge and raster-type edge cases.

### Testing and docs

- **Frontend**: **`AppPropagationSync.test.js`** covers immediate completion (no stray loading toast), polling with **`path_requested`** and live **`ToastUtils.loading`**, and **`no_path`** end states with translated error text; **`AppModals`** / **`ChangelogModal`** tests updated where changelog content or expectations shifted.
- **Frontend (incoming delivery limit)**: **`tests/frontend/incomingDeliveryLimit.test.js`** for clamp and preset/custom byte mapping; **`SettingsPage.config-persistence.test.js`** covers preset **`PATCH`** and debounced custom save.
- **Backend (config API)**: **`test_auto_propagation_api.py`** asserts delivery limit **`PATCH`** clamps above **1 GiB** to **1 GiB** and applies **`delivery_per_transfer_limit`** on the router.
- **Frontend (modularization)**: Shared **`tests/frontend/fixtures/settingsPageTestApi.js`** for **`buildFullServerConfig`** / **`window.api`** mocks; unit tests for **`settingsConfigService`** and **`conversationMessageHelpers`**; **`SettingsSectionBlock`** stubbed in settings-related tests; overlapping **IconButton** cases removed from **`UIComponents.test.js`** (covered by **`IconButton.test.js`**).
- **E2E**: Keyboard shortcut and conversation **scrolling** coverage; navigation assertions aligned with current marketing copy; onboarding tooltip dismissal hooks where applicable.
- **Integration**: **Loopback TCP** test fixture used by relevant integration tests.
- **Backend**: **`test_lxmf_propagation_full.py`** adds **`path_timeout`** in status mapping, **`test_convert_propagation_node_state_maps_all_lxmf_transfer_states`** for LXMF propagation transfer constants, and Hypothesis **`path_timeout`** in allowed propagation state strings; **`test_app_status_tracking`** expects **`changelog_seen_version`** **4.5.0** in app status tests; stamp validation test hardened against flaky random workblocks.
- **Bots / propagation / licenses**: Expanded tests for bot sidecar behaviour, propagation node UI/state, and license rendering collectors.
- **GIFs and stickers**: Backend tests **`test_gif_utils`**, **`test_gifs_dao`**, **`test_sticker_pack_utils`**, **`test_sticker_packs_dao`**; frontend **`Gifs.test.js`**, **`StickerView.test.js`**, **`InViewAnimatedImg.test.js`**, **`tgsDecode.test.js`**, **`inViewObserver.test.js`**, **`mediaLottieStickerGifs.fuzzing.test.js`**.
- **Reticulum config editor**: **`test_reticulum_config_editor.py`** (backend), **`ReticulumConfigEditorPage.test.js`** (frontend).
- **Interfaces**: **`test_interface_discovery_ifac.py`**, **`InterfacesDiscoveryIfac.test.js`**.
- **Interfaces (port-in-use and full options)**: **`tests/backend/test_interface_port_check.py`** covers the new socket probe (free port, busy TCP port, busy UDP port, invalid input, wildcard host, unresolvable host, conflict-message formatting). **`tests/backend/test_interface_options.py`** drives **`/api/v1/reticulum/interfaces/add`** for **AutoInterface** (full options + invalid `discovery_scope`/`multicast_address_type` + busy `data_port` returning 409), **TCPClient** (advanced options), **TCPServer** (optional options + busy listen-port 409), **UDP** (busy listen-port 409), **BackboneInterface** (listener-mode persistence + connector mode still requiring remote), **RNode** (flow control / ID callsign / airtime limits), **KISS** (full serial + framing + beacon options), **AX.25 KISS** (callsign/SSID), and **I2P** (`connectable=False`). **`tests/frontend/AddInterfaceOptions.test.js`** asserts each new field is sent through **`window.api.post('/api/v1/reticulum/interfaces/add', ...)`** and that backend **HTTP 409** "port already in use" responses are surfaced via **`ToastUtils.error`**.
- **Messaging**: **`test_message_sending_failures.py`**, **`MessageSendingFailures.test.js`**; **`CJKTextOverflow.test.js`** for composer/thread overflow.
- **Media API**: **`test_media_http_api.py`**, **`test_media_fuzzing.py`**, shared **`media_test_assets.py`** fixtures.
- **AutoInterface guidance**: **`tests/backend/test_user_guidance_autointerface.py`** exercises bind-failure detection and user-facing guidance strings.
- **Translator**: Integration tests for **Argos**-based forwarding after CLI detection refactor, including **network** checks for **Stanza** resource fetching.
- **LXMF sieve**: **`test_lxmf_sieve.py`** and **`test_lxmf_sieve_fuzz.py`**.
- **Repository server**: **`test_repository_server_manager.py`**.
- **Map / audio (frontend)**: Additional **Vitest** coverage for **map** components, **geodesy** utilities, and **audio** handling paths.
- **Electron**: Vitest **Electron** config plus loading/main helper coverage for the desktop shell.
- **CI stability**: Peering-key rejection integration test avoids flaky peer selection.

## [4.4.0] - 2026-04-15

### TL;DR

- **Chatting**: Pin important conversations, keep draft text when you switch chats (without them disappearing randomly), see clearer send status, paste images straight into the message box, and send one message at a time in order (outbound queue). Deleting a conversation also clears its read state, folder placement, and pins.
- **Reactions**: Emoji reactions over LXMF are finally here! (field 16: target message hash, emoji, sender identity hash); send from the message context menu (fixed picker); reactions render **below** the bubble, outside it, bottom-right; hover shows who reacted (you, the open peer, or a known conversation name).
- **Emoji and stickers**: One place in the composer opens emojis or your own sticker images (per identity); you can import/export sticker libraries in settings, add images by drag-and-drop or upload, and save an image from a message into stickers when it makes sense.
- **Nomad Network browsing**: Besides Micron pages, the built-in browser can show Markdown, plain text, and simple web-style pages; you can tune what gets rendered, pick a default page when a node has no path, and links are handled more safely so the app stays on the mesh (not opening clearnet or risky URLs). Loading shows clearer phase text and file size; announces and favourites have richer context menus (rename, banish, lift, sections). Sidebars can collapse on medium-and-up screens with quick previews of recent chats and favourites.
- **Map**: You can pop out the map in a separate window now.
- **Look and layout**: Cleaner, more consistent light and dark appearance; Tools is a single list with refreshed pages (Bots, paper message, RN path tools, RNode flasher, About, Interface, Settings, Contacts, App); third-party licenses sit under About with an API-backed list.
- **Network noise**: Caps on how many announces are fetched, searched, and shown per aspect (configurable in settings) so busy meshes stay usable.
- **Security and troubleshooting**: Stricter limits on failed logins from untrusted devices when auth enabled (since there are some exposed meshchatx instances out there); optional screens on debug tool to inspect login attempts and search or filter logs.
- **Working with other mesh apps**: Voice messages use a format that tends to play better elsewhere; outgoing messages can tell other clients to treat text as Markdown; messages to saved contacts can include a stamp ticket so they can reply without extra proof-of-work; file transfers and path tools expose clearer status, stop controls, and filters (including max hops and path table by destination).
- **Blocked peers**: Lift a banishment from the conversation header or sidebar when you want to hear from someone again.
- **Notifications**: Refined unread handling (finally no more getting tricked with fake notifications, hopefully) and a toggle for bell history.
- **Checking reachability**: Ping destination shows a clear working state while the request runs.
- **Archives**: Export saved snapshots as Micron (`.mu`) files; multi-export avoids filename clashes.
- **Large Nomad Micron pages**: Smoother scrolling and resizing on big `.mu` pages (including a faster path for ordinary Latin/Cyrillic monospace text).
- **Network visualizer**: Toolbar, legend, and loading state are clearer; path table and graph behaviour use shared helpers for trails, bounds, and layout constants.
- **Connections**: The app WebSocket client heartbeats, reconnects, and handles ping/pong more predictably when the link drops or stalls.
- **Theming**: Semantic design tokens feed Tailwind and Vuetify so light/dark surfaces and accents stay aligned across pages.
- **Desktop app (Electron)**: Right-click menus in text fields (cut/copy/paste, spellcheck, add to dictionary), sensible behaviour for links, and file/folder pickers wired through the desktop shell where applicable.

### Platform and backend

- Split **`meshchat.py`** startup into **`path_utils`**, **`ssl_self_signed`**, and **`env_utils`** (re-exported from **`meshchat.py`** for compatibility).
- **HTTP**: **`docs_manager`**, **`map_manager`**, and **`translator_handler`** use **`aiohttp`**; **`requests`** removed. Stricter request validation and clearer API errors; **`tests/backend/fixtures/http_api_routes.json`** kept in sync.
- **CLI**: Prefer **`meshchatx`** (`python -m meshchatx.meshchat`, Docker, Make, Taskfile); **`meshchat`** remains an alias. **`--rns-log-level`** / **`MESHCHAT_RNS_LOG_LEVEL`**; optional **`--ssl-cert`** / **`--ssl-key`** (both required if used).
- **Auth** (schema **42**): **`access_attempts`**, **`trusted_login_clients`**, rate limits and lockout for untrusted clients, **`GET /api/v1/debug/access-attempts`**. **`DELETE` conversation** clears read state, folder mapping, and pins.
- **AsyncUtils**: thread-safe scheduling; pending coroutines flushed when the main event loop is set.
- **NomadNet downloader**: thread-safe link cache, **`get_cached_active_link`**, phased WebSocket progress, faster polling, safer UTF-8 and cancel handling.
- **RNCP** (file transfer): receive-completed handling and error reporting; transfer start callbacks; **status** / **stop** API and websocket broadcast; listener destination setup/teardown and tests.
- **RNPath / RNStatus**: interface discovery; optional geo fields on interfaces. **Network visualizer**: **`lxmf.delivery`** / **`nomadnetwork.node`** only; **`POST /api/v1/path-table`** filters by destination hashes; **max hops** filter in the UI; refactored trail/bounds utilities and constants for the graph view.
- **Licenses**: collector for Python and Node dependencies; **`GET /api/v1/licenses`**; **`licenses_frontend.json`** included in package data.
- **CI / packaging**: Gitea shell-based jobs, optional **SLSA v1** cosign attestations; GitHub Actions for Windows/macOS; **`priv.sh`** / **`exec-priv.sh`**; macOS universal build avoids duplicate **`backend-manifest.json`**; stripped Python bytecode in backend bundle.
- **CI**: Node dependency scanning uses **Trivy** (`scripts/ci/trivy-fs-scan.sh`) instead of **pnpm audit**, after npm retired the legacy registry audit API used by pnpm.
- **Container**: non-root **`meshchat`**; **`HEALTHCHECK`** on **`/api/v1/status`** (TLS verify relaxed for default self-signed). Podman/OCI: no Docker-style **`HEALTHCHECK`** unless **`--format docker`**; **`/config`** bind mounts may need uid alignment.
- **Debug Logs**: **Logs** and **Access attempts** tabs (search, filters, pagination).
- **`scripts/ci/setup-python.sh`**: Sigstore verification and cosign download by architecture.
- **Stickers**: per-identity image library (schema, validation, DAO), **`/api/v1/stickers`** CRUD and **`GET …/image`**, settings **import/export**, **`DELETE /api/v1/maintenance/stickers`**; **`tests/backend/fixtures/http_api_routes.json`** updated when routes change.
- **Community packaging (`cx_setup.py`)**: Optional **`lxmfy`** and **`websockets`** dependencies; **`scripts/build_community_interfaces_json.py`**, **`scripts/move_wheels.py`**, and **`scripts/ci/slsa-predicate.py`** refinements for clearer outputs and metadata.

### Frontend and UX

- **Vite 8**, **`@vitejs/plugin-vue` 6**, Rolldown-oriented chunking; **`fetch`** via **`apiClient.js`** instead of axios.
- **Announce limits**: per-aspect cap with trim; configurable fetch/search/discovered caps; settings and locales.
- **Conversations**: serial **outbound send queue**; optional **detailed outbound status** (settings + i18n); **conversation pins**; **Lift banishment** from viewer/sidebar; **clipboard image paste** into compose; fix for **empty thread** when switching chats while a fetch is in flight; **compose drafts** persisted in **`localStorage`** (including on unmount); responsive **ConversationViewer** and dropdown actions.
- **Conversation ping**: **Ping Destination** shows a loading toast while the request runs; **`ToastUtils.dismiss(key)`** and a **`toast-dismiss`** event remove keyed toasts (e.g. dismiss after fetch).
- **Emoji and stickers (composer)**: single **emoticon** control at the end of the message field opens a **tabbed** popup (**Emojis** | **Stickers**). **Emojis** use **`emoji-picker-element`** with **`emoji-picker-element-data` bundled** via Vite (`?url`) so emoji metadata loads **same-origin** and satisfies strict **CSP** with no reliance on any CDNs. **Stickers** tab: library grid, drag/drop and file upload, **save image to stickers** from the message menu where applicable.
- **Notifications**: bell history toggle; refined unread handling.
- **NomadNet**: phase-based loading copy; duration/size in header; context menus on announces/favourites (rename, banish, lift, sections); **collapsible** Messages and Nomad list sidebars on **sm+** (chevron); when **collapsed**, **Messages** shows tab icons plus up to **five** conversation avatars (**Conversations** tab, pinned/recent order) and **no** extra strip on **Announces**; **Nomad** collapsed rail shows up to **five** favourites (section order) on **Favourites** and up to **five** nodes (latest announce order) on **Announces**.
- **NomadNet browser page formats**: In addition to Micron (`.mu`), the built-in browser renders **Markdown** (`.md`), **plain text** (`.txt`), and **static HTML with CSS** (`.html`). Markdown uses CommonMark-style headings (a **space** after `#` is required unless the viewer normalizes shorthand); HTML is sanitized (no script, no external URLs in CSS, no off-mesh links in `href`/`src` except safe patterns). **Mesh servers** register the same extensions under `/page/`; unknown extensions are rejected by the API.
- **NomadNet browser renderer settings**: Settings include a **NomadNet browser renderer** section (under Browsing): toggles to disable extra rendering for **Markdown**, **HTML**, and **plain text** (Micron is always rendered); **default page path** when opening a node without a path (`/page/index.mu`, `/page/index.html`, `/page/index.md`, or `/page/index.txt`), also used for hash-only Nomad links and the **Smart Crawler** homepage fetch.
- **NomadNet link isolation and Reticulum-only navigation**: Relative and mesh-style links in **HTML**, **Markdown**, and **Micron** output are rewritten to `href="#"` with `data-nomadnet-url` so the SPA does not navigate the browser to `/page/...` or off-app URLs. The Nomad browser and **Archives** viewer handle `.nomadnet-link` clicks in-app; in-page `#fragment` links scroll within the viewer. `href` sanitization explicitly rejects **http**, **https**, protocol-relative `//`, **mailto**, **ftp**, **file**, **data**, **javascript**, and similar schemes so clearnet and dangerous URLs are not preserved as navigable links.
- **Tools**: Removed the duplicate **Third-party licenses** entry from the Tools grid (licenses remain under **About**).
- **Shell chrome**: Opaque **white** / dark **zinc-950** surfaces aligned across the top bar, navigation drawer, Messages/Nomad sidebars, conversation header, message list, and composer (replacing mixed translucent, backdrop-blur, and gradient backgrounds for consistent light/dark appearance).
- **Theme (`designTokens.js`)**: Semantic tokens integrated with **Tailwind** (`tailwind.config.js`) and **Vuetify** theme overrides; optional theme-variable injection for integrators using **`cx_setup`**.
- **Network visualiser (UI)**: Dedicated **toolbar**, **legend**, and **loading overlay** components; internal modules for **trail** placement, **view bounds**, and shared **constants** (cleaner layout and future work).
- **NomadNetwork**: Separate **AbortController** instances for the node list and node detail fetches so navigation cancels the right request.
- **WebSocket (`WebSocketConnection.js`)**: Heartbeat, backoff/reconnect, and **ping/pong** handling with shared helpers in **`wsConnectionSupport.js`**.
- **Context menus (Vue)**: Shared **ContextMenuPanel**, **ContextMenuItem**, **ContextMenuDivider**, and **ContextMenuSectionLabel** (`components/contextmenu/`); styling tokens in **`style.css`**. Wired into **Contacts**, **Messages** sidebar, **ConversationViewer** message menu, **NomadNetwork** sidebar (favourites, sections, announces), and **Map** (optional **header** slot for the title row).
- **LXMF emoji reactions (UI)**: **React** section in the message context menu (Columba-aligned emoji set); inbound/outbound websocket paths merge reactions onto the target message instead of a separate row; **`mergeLxmfReactionRowsIntoMessages`** when loading history; chips below the bubble with **`title`** tooltips via **`reactionReactorLabel`** (self, selected peer, sidebar conversations, else short hash).
- **Vue lint**: **`vue/no-reserved-keys`** — internal **`data()`** fields renamed (peer header **ResizeObserver**, Nomad Micron partial scheduling **requestAnimationFrame** handle) so ESLint passes without reserved `_` prefixes.
- **Map**: pop-out window.
- **Tools**: list-style **ToolsPage**; refreshed **Bots**, **Paper message**, **RN path**, **RN path trace**, **RNode flasher**; **About**, **Interface**, **Settings**, **Contacts**, **App** polish (loading overlays, display names, license links). Many tool and settings pages use adjusted **backgrounds and padding** for alignment with the global shell.
- **Electron**: default **context menu** for editable fields (cut/copy/paste, **spellcheck** suggestions, add to dictionary), links, and related actions; **pick file** / **pick directory** / **open path** / notifications and related **preload** helpers; loading screen refresh; CSP and **backend HTTP-only** IPC where applicable.
- **`/robots.txt`** in **`public/`**; **`SECURITY.md`** crawler note.
- **Locales**: `import.meta.glob` discovery; new strings for outbound status, archives, NomadNet, RNCP (including browse/folder/web hints), max hops, stickers, emoji picker tabs, **message reactions** (react / you / send failed), and **backend connection status** copy in **en** / **de** / **it** / **ru**, etc.

### Micron and archives

- **MicronParser**: fault-tolerant line and document fallbacks; safer monospace and sanitization; **monospace fast path** for Latin and Cyrillic (and other non-CJK text) using grouped spans instead of one DOM node per character when the line does not need CJK or box-drawing cell alignment, improving scroll and **resize** performance on large **.mu** pages.
- **NomadNet Micron viewer**: **`v-memo`** on the rendered page HTML, **`contain: layout paint`** on the scroll container, and **early exit** in partial processing when the page source has no partial placeholders; **Messages** and **Nomad** sidebars use **`matchMedia(min-width: 640px)`** instead of **`window.resize`** so the **sm** breakpoint updates only when crossing the threshold (smoother responsive / DevTools resizing).
- **Archives**: export snapshots as **`.mu`** (multi-export avoids name collisions).

### Removed

- **axios** (replaced by **`fetch`**), legacy PR vulnerability workflow, **Nix** flakes, obsolete scripts.
- **LegacyMigrator**: Removed legacy database migration system from startup to streamline initialization.

### LXMF interoperability

- **Markdown renderer field**: Outbound messages now set **`FIELD_RENDERER`** to **`RENDERER_MARKDOWN`**, so receiving clients (Sideband, etc.) know to render content as Markdown.
- **Stamp tickets for contacts**: Outbound messages to saved contacts automatically include a **`FIELD_TICKET`** (`include_ticket`), allowing trusted peers to reply without generating a proof-of-work stamp.
- **Opus voice messages**: Browser-recorded Opus audio (WebM container) is converted to **OGG/Opus** via ffmpeg before sending, fixing playback on Sideband and reducing file size (~24 kbps VBR).
- **Emoji reactions (Columba-compatible)**: Reactions are separate LXMF messages with empty body and **field 16** (`reaction_to` message hash, **`emoji`**, **`sender`** as hex identity hash), **opportunistic** delivery, no markdown renderer / ticket / icon field on reaction-only sends. **`POST /api/v1/lxmf-messages/reactions`**; **`send_reaction`** / **`app_extensions`** on **`send_message`**; **`lxmf_fields_are_columba_reaction`** for delivery (spam keywords skipped for reaction frames; title/content decoded safely); alias forwarding passes field 16 through. **`convert_lxmf_message_to_dict`** / **`convert_db_lxmf_message_to_dict`** expose **`is_reaction`**, **`reaction_to`**, **`reaction_emoji`**, **`reaction_sender`**, and **`fields.app_extensions`** (field 16 with **`reply_to`** stays a normal message, not a reaction).

### Testing and docs

- **Frontend**: Vitest expanded for **ConversationViewer** (outbound bubble styling, clipboard images vs non-images, **paste** toolbar, file attachments, translation, conversation fetch ordering, compose drafts, **stickers** / emoji picker); **Toast** (`toast-dismiss`); **RNCP handler** listener/status tests; **HTTP route contract** (`tests/backend/fixtures/http_api_routes.json`); **`tests/frontend/setup.js`**: **`fake-indexeddb`**, **`fetch`** stub for bundled emoji JSON; console noise suppressed in CI; **MicronParser** tests for Cyrillic/CJK monospace paths; **NomadNetwork** sidebar/page tests aligned with collapse and Micron behavior; **i18n** parity for RNCP keys (**de** / **it** / **ru**); **SettingsPage** visibility test updated for **three** message bubble color pickers; **`contextMenuStyles.test.js`** asserts shared CSS classes and **ContextMenu** component usage across pages (sidebar/button tests updated for **`.context-menu-panel`** selectors); **`lxmfReactions.test.js`** for **`mergeLxmfReactionRowsIntoMessages`** (merge + dedupe); **WebSocket** unit tests for connection helpers. **Load-time / large-list sidebar** tests (`tests/frontend/LoadTimePerformance.test.js`) are **not** run in default **`pnpm test`** or CI; run **`pnpm run test:loadtime`** or **`task test:fe:loadtime`** locally when you need that check.
- **Backend**: access attempts, announce limits, downloader, Micron, SSL CLI, **memory-leak** regressions (message state updates, etc.), **sticker** utils/DAO/API tests, fuzzing where applicable; WebM-to-OGG conversion unit tests; **`test_lxmf_reactions.py`** (field 16 reaction shape, DB round-trip, **`reply_to`** in app extensions without treating as reaction); **incoming-call policy** tests (DND, contacts-only, blocking); conversation and announce **search** integration tests; JSON **API response** schema/contract coverage on selected handlers.
- **E2E**: **Playwright** (`tests/e2e/`, **`pnpm run test:e2e`**) smoke, navigation, shell chrome.
- **Docs**: **README** / **`docs/meshchatx.md`** and **`docs/nomadmesh_pages.md`** (Nomad/Mesh Server page formats); **README** section **Linux desktop: emoji fonts** (e.g. **`noto-fonts-emoji`** on Arch/Artix, Debian/Fedora equivalents) when glyphs show as tofu. Dependency bumps via **pnpm** / **Poetry** (Electron, Vue, Vuetify, Playwright, **emoji-picker-element**, **emoji-picker-element-data**, **fake-indexeddb**, **cryptography** 46.0.7, **hypothesis**, **pytest**, **ruff**, **rns** 1.1.5, Python **3.14** in CI, etc.).

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
