# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

A extensively modified and feature-rich fork of [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) by Liam Cottle.

This project is independent from the original Reticulum MeshChat project and is not affiliated with it.

- Website: [meshchatx.com](https://meshchatx.com)
- Source: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Official GitHub Mirror: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Releases: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- Donate: [`donate.md`](donate.md) ([Donation](#donation))
- Umbrel App Store: [apps.umbrel.com/app/meshchatx](https://apps.umbrel.com/app/meshchatx)

<a href="https://apps.obtainium.imranr.dev/redirect.html?r=obtainium://add/https://github.com/Quad4-Software/MeshChatX"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" height="60" alt="Get it on Obtainium"></a>

rngit NomadNet Node: `5399f5a0212477618821e91e88ce053b:/page/index.mu`

rngit: `git clone rns://926baefe13daf5178c174f158dae1b45/quad4/MeshChatX`

MeshChatX NomadNet Node: `c10d80b1a42fa958c37a6cc30dc04f53:/page/index.mu`

## Important Changes from Reticulum MeshChat

- Uses LXST for calls
- Replaced Peewee ORM with raw SQL.
- Replaced Axios with native fetch.
- Uses Electron 41.x (bundled Node 24 runtime).
- .whls ships with webserver and built-in frontend assets for more deployment options.
- i18n
- PNPM and UV for dependency management.

## Requirements

- Python `>=3.11` (from `pyproject.toml`)
- Node.js `>=24` (from `package.json` `engines`)
- pnpm `11.1.2` (from `package.json` `packageManager`)
- UV (used by `Taskfile.yml` and CI workflows)

**Browser Versions Required:**

Safari 16.4 or later, Chrome 111 or later, Firefox 128 or later (bundled web UI).

```bash
task install
task lint:all
task test:all
task build:all
```

## Install Methods

Use the method that matches your environment and packaging preference.

| Method                  | Includes frontend assets | Architectures                              | Best for                                       |
| ----------------------- | ------------------------ | ------------------------------------------ | ---------------------------------------------- |
| Docker image            | Yes                      | `linux/amd64`, `linux/arm64`               | Fastest setup on Linux servers/hosts           |
| Python wheel (`.whl`)   | Yes                      | Any Python-supported architecture          | Headless/web-server install without Node build |
| Linux AppImage          | Yes                      | `x64`, `arm64`                             | Portable desktop use                           |
| Debian package (`.deb`) | Yes                      | `x64`, `arm64`                             | Debian/Ubuntu installs                         |
| RPM package (`.rpm`)    | Yes                      | CI-runner dependent for published artifact | Fedora/RHEL/openSUSE style systems             |
| From source             | Built locally            | Host architecture                          | Development and custom builds                  |

Notes:

- GitHub Actions builds tagged releases (Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, Android APKs when the tag is on `dev` or `master`, SLSA, draft release) in one run via `.github/workflows/build-release.yml`; the container image via `.github/workflows/docker.yml`. Branch and PR Android CI stays in `.github/workflows/android-build.yml`.
- Linux `x64` and `arm64` AppImage + DEB are built on GitHub; RPM is attempted and uploaded when produced.

## Docker

- **Docker Hub:** `quad4io/meshchatx`
- **GHCR:** `ghcr.io/quad4-software/meshchatx`

```bash
docker compose up -d
```

```bash
docker run -d --name reticulum-meshchatx \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

You can substitute `quad4io/meshchatx:latest` for the image if you prefer Docker Hub.

Default compose file maps:

- `127.0.0.1:8000` on host -> container port `8000`
- Docker **named volume** `meshchatx-config` -> `/config` for persistence (works with the image `meshchat` user, UID 1000, without bind-mount permission fixes)

**Optional: bind mount a host directory instead**

If you want data under a host path (for example `./meshchat-config`), replace the volume line with `-v "$(pwd)/meshchat-config:/config"` (Compose: change the service `volumes` entry to that bind path). The container runs as **UID 1000**; the host directory must be writable by that uid (typical fix: `sudo chown -R 1000:1000 ./meshchat-config`). If the directory is empty on first run, create it first so Docker does not create it as root-only.

**Inspect or reset the named volume**

```bash
docker volume inspect meshchatx-config
# remove container and delete persisted data (destructive)
docker rm -f reticulum-meshchatx
docker volume rm meshchatx-config
```

## Install from Release Artifacts

### 1) Linux AppImage (x64/arm64)

1. Download `ReticulumMeshChatX-v<version>-linux-<arch>.AppImage` from releases.
2. Make it executable and run:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### 2) Debian/Ubuntu `.deb` (x64/arm64)

1. Download `ReticulumMeshChatX-v<version>-linux-<arch>.deb`.
2. Install:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### 3) RPM-based systems

1. Download `ReticulumMeshChatX-v<version>-linux-<arch>.rpm` if present in the release.
2. Install with your distro tool:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### 4) Python wheel (`.whl`)

Release wheels include the built web assets.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

`pipx` is also supported:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Run from Source (Web Server Mode)

Use this when developing or when you need a local custom build.

```bash
git clone https://git.quad4.io/RNS-Things/MeshChatX.git
cd MeshChatX
corepack enable
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "uv==0.11.12"
uv lock --check
uv sync --group dev
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Notes on the install commands above:

- `pnpm install --frozen-lockfile` refuses to update `pnpm-lock.yaml` and fails if the lockfile does not match `package.json`. This is what blocks an unexpected upstream version from being silently pulled in.
- `verify-store-integrity=true` is also set in the project `pnpm-workspace.yaml`; the explicit `pnpm config set` line above just hardens the user-level config too.
- Lifecycle scripts (`preinstall`/`postinstall`) are blocked by default in pnpm v11+. Only the packages listed under `allowBuilds` in `pnpm-workspace.yaml` are allowed to run install scripts (currently `electron`, `electron-winstaller`, `esbuild`).
- `uv lock --check` fails fast if `uv.lock` is out of sync with `pyproject.toml`; `uv sync` then resolves only from the lockfile.
- For a strict lockfile-only UV install (no implicit lockfile refresh), pin UV with `pip install "uv==0.11.12"` to match what CI uses.

If you intentionally want to update dependencies, run `pnpm update` / `uv lock` in a dedicated commit and review the resulting lockfile diff before pushing.

## Run sandboxed (Linux)

To run the native `meshchatx` binary (alias: `meshchat`) with extra filesystem isolation, you can use **Firejail** or **Bubblewrap** (`bwrap`) while keeping normal network access for Reticulum and the web UI. Full examples (pip/pipx, Poetry, USB serial notes) are in:

- [`docs/meshchatx_linux_sandbox.md`](docs/meshchatx_linux_sandbox.md)

The same page appears in the in-app **Documentation** list (MeshChatX docs) when served from the bundled or synced `meshchatx-docs` files.

## Linux desktop: emoji fonts

The emoji picker renders standard Unicode emoji using your system fonts (Electron/Chromium). If emoji show as empty squares (“tofu”), install a color emoji package and restart the app.

| Family (examples)          | Package                                                              |
| -------------------------- | -------------------------------------------------------------------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`)               |
| Debian, Ubuntu             | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`) |
| Fedora                     | `google-noto-emoji-color-fonts`                                      |

After installing, run `fc-cache -fv` if glyphs still fail until the next login. Optional: `noto-fonts` for broader symbol coverage on minimal installs.

## Windows desktop: microphone (Electron, Windows 10 / 11)

Calls and voice attachments use the microphone through Chromium inside the desktop app. If the UI shows no access or **getUserMedia** fails, check **Windows privacy** first (this is a frequent cause for “classic” Win32 apps, including Electron):

1. Press **Win + R**, paste **`ms-settings:privacy-microphone`**, press Enter.
2. Turn **Microphone access** on.
3. Enable **Let desktop apps access your microphone** (wording may vary slightly by Windows version).
4. Ensure MeshChatX is not denied under **Choose which apps can access your microphone** if that list appears.

Also confirm the app is not muted in **Settings → System → Sound** and that a working input device is selected.

## Offline Builds

MeshChatX supports two levels of offline building:

1. **Cached offline builds** — you already ran `make install` once and have `node_modules/`, `.venv/`, and local caches.
2. **Air-gapped (zero-network) builds** — the machine has _never_ had internet. You create an offline bundle on a networked machine and transfer it.

### Cached Offline Builds

Set `MESHCHATX_OFFLINE_BUILD=1` before running any build command. This skips all network fetches (micron-parser-go WASM, Reticulum manual, repository wheels) and runs package managers in offline mode. If a required cached asset is missing, the build fails with a clear error instead of hanging.

```bash
# Install dependencies offline (requires populated pnpm store and uv cache)
MESHCHATX_OFFLINE_BUILD=1 make install

# Build frontend + backend offline
MESHCHATX_OFFLINE_BUILD=1 pnpm run build:offline

# Build Linux desktop packages offline
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux:offline

# Android Gradle also respects the flag
MESHCHATX_OFFLINE_BUILD=1 ./gradlew :app:assembleRelease
```

> **Note:** Cached offline mode only skips _build-time_ network access. The first `make install` must be run online (or with pre-populated caches) so that `pnpm` and `uv` have the packages available locally.

### Air-Gapped Builds (No Cache)

For machines with no internet access at all, create an offline bundle on a networked machine and transfer it.

**On the online machine:**

```bash
# Create the bundle (includes node_modules, Python wheels, and tooling caches)
pnpm run bundle:offline

# Optional: also pre-download packaging tools (appimagetool, etc.)
bash scripts/create-offline-bundle.sh --warm-packaging

# Transfer the bundle to your air-gapped machine
tar czf meshchatx-offline-linux-x64.tar.gz -C vendor/offline meshchatx-offline-bundle-*/
```

**On the air-gapped machine:**

```bash
# Extract the bundle into the project
tar xzf meshchatx-offline-linux-x64.tar.gz

# Install from the bundle (extracts node_modules and sets up caches)
bash scripts/install-offline.sh

# Build completely offline
MESHCHATX_OFFLINE_BUILD=1 make build

# Or package offline
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux
```

The bundle is platform-specific because it contains native binaries (Electron, esbuild, etc.). Create it on the same OS/architecture as the air-gapped build host.

Prerequisites on the air-gapped machine: `node`, `pnpm`, `uv`, and `python3` must be installed (the bundle provides all dependencies and caches, not the toolchain itself).

> **Android builds:** The offline bundle does **not** include Android Chaquopy wheels. Build those separately on an online machine (`bash scripts/build-android-wheels-local.sh`) and copy `android/vendor/` to the air-gapped host alongside the project. Then run Gradle with `MESHCHATX_OFFLINE_BUILD=1`.

## Build Desktop Packages from Source

These scripts are defined in `package.json` and `Taskfile.yml`.

### Linux x64 AppImage + DEB

```bash
pnpm run dist:linux-x64
```

### Linux arm64 AppImage + DEB

```bash
pnpm run dist:linux-arm64
```

### RPM

```bash
pnpm run dist:rpm
```

Or through Task:

```bash
task dist:fe:rpm
```

## Container build (wheel, AppImage, deb, rpm)

`Dockerfile.build` runs the same shell-driven steps CI uses (Poetry, pnpm, `task`, packaging APT deps). It is oriented toward **linux/amd64** (NodeSource amd64 tarball, Task amd64 binary). Default target is everything; override with a build arg.

Targets for `MESHCHATX_BUILD_TARGETS`: `all` (default), `wheel`, or `electron` (AppImage + deb for x64 and arm64, best-effort RPM, no wheel).

Build:

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
```

Build only a wheel:

```bash
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

Copy `/artifacts` from the finished image to the host:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Architecture Support Summary

- Docker image: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (build scripts available)
- macOS: build scripts available (`arm64`, `universal`) for local build environments
- Android: universal APK only (see [`android/README.md`](android/README.md))

## Android

MeshChatX supports native Android APK builds (not only Termux).

### Build APKs from source

From repo root:

```bash
# 1) Build Chaquopy wheels used by android/app/build.gradle
bash scripts/build-android-wheels-local.sh

# 2) Build universal APKs (one debug + one release per run; see android/README.md)
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

Offline Android builds are supported by setting `MESHCHATX_OFFLINE_BUILD=1`:

```bash
MESHCHATX_OFFLINE_BUILD=1 ./gradlew --no-daemon :app:assembleRelease
```

This skips the repository wheels fetch step. The `android/vendor/` wheels and `meshchatx/public/repository-server-bundled/bundled/` must already be present.

There is a **single** Android variant. Gradle syncs the full `meshchatx/` tree into `app/src/main/python/meshchatx/`, including the offline repository wheel bundle. Published and documented builds use **universal** packaging only: one debug APK and one release APK per run, each containing the native ABIs configured in `android/app/build.gradle`.

- Debug: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

Notes:

- Release outputs are unsigned by default unless you configure signing (`scripts/sign-android-apks.sh`).
- Native ABIs embedded in the universal APK follow `android/app/build.gradle` (including `armeabi-v7a` when enabled). Building wheels for `armeabi-v7a` needs an Android SDK on `ANDROID_HOME` (see `android/README.md`).
- If repo root `dist/reticulum_meshchatx-*.whl` exists (for example from `python -m build --wheel -o dist .`), bundled repository refresh prefers that wheel over PyPI for the MeshChatX package. CI builds that wheel before the Android Gradle step.

Additional docs:

- [`docs/meshchatx_on_android_with_termux.md`](docs/meshchatx_on_android_with_termux.md)
- [`android/README.md`](android/README.md)

## Configuration

MeshChatX supports both CLI args and env vars.

| Argument                   | Environment Variable                     | Default      | Description                                                                                                                                                                |
| -------------------------- | ---------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Web server bind address                                                                                                                                                    |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Web server port                                                                                                                                                            |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | Disable HTTPS                                                                                                                                                              |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (none)       | PEM certificate and private key paths; both must be set together. Overrides auto-generated certs under the identity `ssl/` directory.                                      |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (none)       | Reticulum (RNS) stack log level: `none`, `critical`, `error`, `warning`, `notice`, `verbose`, `debug`, `extreme`, or a numeric level. CLI overrides env when both are set. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Do not auto-launch browser                                                                                                                                                 |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Enable basic auth                                                                                                                                                          |
| `--reset-password`         | `MESHCHAT_RESET_PASSWORD`                | `false`      | Clear the stored password hash so a new password can be set via the web UI                                                                                                 |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Data directory                                                                                                                                                             |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundled | Frontend files directory (needed for source installs without bundled assets)                                                                                               |

## Branches

| Branch   | Purpose                                                         |
| -------- | --------------------------------------------------------------- |
| `master` | Stable releases. Production-ready code only.                    |
| `dev`    | Active development. May contain breaking or incomplete changes. |

## Development

Common tasks from `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

`Makefile` shortcuts are also available:

| Command        | Description                             |
| -------------- | --------------------------------------- |
| `make install` | Install pnpm and UV dependencies        |
| `make run`     | Run MeshChatX via UV                    |
| `make build`   | Build frontend                          |
| `make lint`    | Run eslint and ruff                     |
| `make test`    | Run frontend and backend tests          |
| `make clean`   | Remove build artifacts and node_modules |

## Versioning

Current version in this repo is `4.6.3`.

- **`package.json`** `version` is the only value you edit for a release bump.
- Run **`pnpm run version:sync`** (also run at the start of **`pnpm run build`**) to propagate that version into **`pyproject.toml`**, **`meshchatx/src/version.py`**, **`THIRD_PARTY_NOTICES.txt`** (product line), **README** / **lang/README.\*** “current version” lines, **`docs/meshchatx_on_raspberry_pi.md`** pipx example, and **`packaging/arch/PKGBUILD`** helpers.
- **`meshchatx.__version__`** is read from **`meshchatx/src/version.py`** without importing **`meshchatx.src`**, so a plain `import meshchatx` stays lightweight.
- **Changelog** entries stay manual when you cut a release.

## Security

Security and integrity details:

- [`SECURITY.md`](SECURITY.md)
- [`LEGAL.md`](LEGAL.md)
- Built-in integrity checks and HTTPS/WSS defaults in app runtime.
- CI and release builds on GitHub Actions.

## Adding a Language

My workflow: ArgosTranslate -> Local LLM (Qwen 3 + Gemma 4)

People are then welcome to submit fixes to me via LXMF or wherever you can contact me.

Locale discovery is automatic. Add a new file under `meshchatx/src/frontend/locales/` (for example `xx.json`) with the same keys as `en.json` and a top-level `_languageName` string for the label shown in the language selector. You can copy `en.json` and translate every value by hand; **machine-assisted generation is optional** and never required.

**Optional: Argos Translate bootstrap** -- If you want a machine-generated first draft from `en.json`, you can use `scripts/argos_translate.py`. It handles formatting, color output, and helps protect interpolation variables (like `{count}`) from accidental edits.

```bash
# Install argostranslate if you haven't already
pipx install argostranslate

# Run the translation script
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Your Language Name"
```

After any machine-assisted pass, have an LLM or a human reviewer verify grammar, context, and tone (for example formal vs informal).

Run `pnpm test -- tests/frontend/i18n.test.js --run` to verify key parity with `en.json`.

No other code changes are required. The app, language selector, and tests all discover locales from the `meshchatx/src/frontend/locales/` directory at build time.

## Donation

Donations are voluntary. They help fund time and effort to develop this app.

**Ways to give:** [`donate.md`](donate.md) (Monero, Ko-Fi, Buy Me a Coffee).

## Credits

- [Liam Cottle](https://github.com/liamcottle) - Original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron parser JavaScript work
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## License

Project-owned portions are licensed under 0BSD.
Original upstream portions from Reticulum MeshChat remain under MIT.
See [`LICENSE`](LICENSE) for full text and notices.
