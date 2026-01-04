# Changelog

All notable changes to this project will be documented in this file.

## [4.0.0] - 2026-01-03

Season 1 Episode 1 - A MASSIVE REFACTOR

### New Features

- **Banishment System (formerly Blocked):** 
    - Renamed all instances of "Blocked" to **"Banished"**, you can now banish people to the shadow realm.
    - **Blackhole Integration:** Automatically blackholes identities at the RNS transport layer when they are banished in MeshChatX. This prevents their traffic from being relayed through your node and publishes the update to your interfaces (trusted interfaces will pull and enforce the banishment).
    - Integrated RNS 1.1.0 Blackhole to display publishing status, sources, and current blackhole counts in the RNStatus page.
- **RNPath Management Tool:** New UI tool to manage the Reticulum path table, monitor announce rates (with rate-limit detection), and perform manual path requests or purges directly from the app.
- **Maps:** You can now draw and doodle directly on the map to mark locations or plan routes.
- **Calls & Audio:**
    - Added support for custom ringtones and a brand-new ringtone editor.
    - New **Audio Waveform Visualization** for voice messages, providing interactive playback with a visual waveform representation.
- **Paper Messages:** Introduced a tool for generating and scanning paper-based messages with built-in QR code generation for easy sharing.
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

### Improvements

- **Blazingly Fast Performance:**
    - **Network Rendering:** The Network Visualizer now uses intelligent batching to handle hundreds of nodes without freezing your screen.
    - **Memory Optimization:** Added a smart icon cache that automatically clears itself to keep the app's memory footprint low.
    - **Parallel Loading:** The app now fetches network data in parallel, cutting down startup and refresh times significantly.
    - **Lazy Loading:** Documentation and other heavy components now load only when you need them, making the initial app launch much faster.
    - **Smoother Settings:** Changing settings now uses "smart saving" (debouncing) to prevent unnecessary disk work and keep the interface responsive.
    - **Backend Efficiency:** A massive core refactor and new database optimizations make message handling and search nearly instantaneous. Added pagination to announce and discovery lists to improve performance in large networks.
- **Calling:** The call screen and overlays have been completely redesigned to look better and work more smoothly.
- **Messaging:** We've polished the message lists and archive views to make them easier to navigate.
- **Network View:** The visualizer that shows your network connections is now much clearer and easier to understand.
- **Languages:** Updated translations for English, German, and Russian. Added a toggle to easily enable or disable translation services.
- **Search:** The command palette (quick search) and notification bell are now more useful.

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
    - Expanded test coverage with 40+ new unit and integration tests across `tests/backend/` and `tests/frontend/`.
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
