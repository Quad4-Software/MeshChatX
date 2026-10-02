# scripts/

Build, CI, packaging, and development tooling for MeshChatX.

## Layout

| Directory | Purpose |
|---|---|
| `android/` | Android APK build helpers, Chaquopy wheel fixes, keystore tooling |
| `build/` | Release build steps (frontend bundles, PyInstaller, docs fetch) |
| `ci/` | GitHub Actions helper scripts (installers, version pinning, priv helpers) |
| `docker/` | Docker image build steps (frontend stage, venv prep, musl bake) |
| `e2e/` | Playwright E2E helpers (server boot, route crawling, axe scans) |
| `mutation/` | mutmut mutation-test runners and scope config |
| `pip-rns/` | Reticulum pip dependency helpers |
| `rpi/` | Raspberry Pi image and install scripts |
| `soak/` | Multi-instance soak/stability test harness |
| `ui/` | UI selfcheck and screenshot tooling |
| `wireshark/` | LXMF packet dissector for Wireshark |

## Top-level scripts

| Script | Purpose |
|---|---|
| `build-backend.js` | Vite build for the backend static bundle |
| `build-geo-wasm.mjs` | Build geo.wasm (MGRS/OLC) via Go or TinyGo |
| `build-visualiser-wasm.mjs` | Build visualiser.wasm via Go or TinyGo |
| `build-lxst-filterlib.py` | Cross-compile LXST filterlib for Linux/macOS |
| `build-pyz.sh` | Package the app as a Python .pyz |
| `build_community_interfaces_json.py` | Generate community interfaces index JSON |
| `build-electron-shell-css.mjs` | Compile Electron shell CSS |
| `build-macos-universal.sh` | macOS universal binary packaging |
| `check-format-tokens.mjs` | Validate locale format tokens |
| `check-git-deps.mjs` | Check for git-sourced deps in lockfiles |
| `copy-bergamot-wasm.mjs` | Vendor the bergamot translation WASM artifacts |
| `create-offline-bundle.sh` | Build the offline install bundle |
| `dev-local.sh` | Run the local dev stack |
| `diagnostics-bundle.py` | Collect logs/config for bug reports |
| `docker-entrypoint.sh` | Container entrypoint |
| `docker_entrypoint_chainguard.py` | Chainguard image entrypoint |
| `docker-bake-lxst-filterlib-musl.py` | Build musl LXST filterlib wheels in Docker |
| `ensure-flatpak-flathub-remote.sh` | Configure Flathub remote for Flatpak builds |
| `ensure-micron-parser-package.js` | Fetch the micron parser package version |
| `fetch-micron-wasm.mjs` | Download micron-parser-go WASM artifacts |
| `fetch-starter-mbtiles.mjs` | Download the starter offline map tiles |
| `generate_locale_template.py` | Regenerate the en.json locale template |
| `install-offline.sh` | Install from an offline bundle |
| `micron-parser-go-version.mjs` | Resolve the micron-parser-go release tag |
| `micron-wasm-resolve-bundled.mjs` | Pick bundled vs downloaded micron WASM |
| `move_wheels.py` | Stage wheels into vendor/ for packaging |
| `patch_lxst_codec2_optional.py` | Make codec2 optional in vendored LXST |
| `patch_lxst_pyogg_ogg_ctypes.py` | Patch pyogg ctypes loading for PyInstaller |
| `patch-electron-builder-fs.cjs` | Patch electron-builder fs behavior |
| `patch-electron-installer-common.cjs` | Patch electron installer common module |
| `pip_rns_remotes.py` | Manage pip remotes for RNS deps |
| `setup_wine_env.sh` | Wine env for Windows Electron builds |
| `sign-android-apks.sh` | Sign Android APKs with release keystore |
| `sign-plugin.py` | Sign a MeshChatX plugin bundle |
| `sync-meshchatx-docs.js` | Sync docs into the frontend bundle |
| `sync_deps.py` | Sync dependency pins across manifests |
| `sync-issues.py` | Sync repo issues into a task board export |
| `sync_version.js` | Sync app version across files |
| `thin-backend-mach-o.sh` | Thin universal Mach-O backend binaries |
| `unify-backend-plain-files.sh` | Deduplicate backend plain files in builds |
| `bake_build_meta.js` | Write build metadata (commit, channel, time) |
| `license_scope_mapper.go` | Analyze file similarity vs upstream for license scoping |
| `rngit_release.py` | rngit release helper |
| `build-android-lxst-filterlib.py` | Build per-ABI LXST filterlib wheels for Chaquopy |
| `build-android-wheels-local.sh` | Build Android vendor wheels locally |
| `meshchatx_pyz_preamble.py` | Preamble injected into the .pyz bundle |

## Conventions

- New one-off helpers go under the closest category directory, not the top level.
- Scripts referenced by `Taskfile.yml`, Dockerfiles, or CI workflows must keep
  their path stable. Check `grep -rln <name>` before moving anything.
- WASM builds prefer TinyGo when available (`tinygo` on PATH or `$TINYGO`),
  falling back to stock Go. TinyGo produces ~4-5x smaller binaries.
