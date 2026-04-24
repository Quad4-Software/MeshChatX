# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

A extensively modified and feature-rich fork of [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) by Liam Cottle.

This project is independent from the original Reticulum MeshChat project and is not affiliated with it.

- Website: [meshchatx.com](https://meshchatx.com)
- Source: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Official GitHub Mirror: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Releases: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Important Changes from Reticulum MeshChat

- Uses LXST
- Replaced Peewee ORM with raw SQL.
- Replaced Axios with native fetch.
- Uses Electron 41.x (bundled Node 24 runtime).
- .whls ships with webserver and built-in frontend assets for more deployment options.
- i18n
- PNPM and Poetry for dependency management.

> [!WARNING]
> MeshChatX is not guaranteed to be wire/data compatible with older Reticulum MeshChat releases. Back up data before migration/testing.

> [!WARNING]
> Legacy systems are not fully supported yet. Current baseline is Python `>=3.11` and Node `>=24` (Electron 41 aligns with Node 24; `package.json` `engines` and CI use the same line).

## Requirements

- Python `>=3.11` (from `pyproject.toml`)
- Node.js `>=24` (from `package.json` `engines`)
- pnpm `10.33.0` (from `package.json` `packageManager`)
- Poetry (used by `Taskfile.yml` and CI workflows)

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

- GitHub Actions builds tagged releases: Windows and macOS via `.github/workflows/build-release.yml`, Linux wheel/AppImage/deb/rpm via `.github/workflows/build-linux-release.yml`, and the container image via `.github/workflows/docker.yml`.
- Linux `x64` and `arm64` AppImage + DEB are built on GitHub; RPM is attempted and uploaded when produced.

## Quick Start: Docker

- **Docker Hub:** `quad4io/meshchatx`
- **GHCR:** `ghcr.io/quad4-software/meshchatx`

```bash
docker compose up -d
```

Default compose file maps:

- `127.0.0.1:8000` on host -> container port `8000`
- `./meshchat-config` -> `/config` for persistence

If your local `meshchat-config` permissions block writes, fix ownership:

```bash
sudo chown -R 1000:1000 ./meshchat-config
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
pip install "poetry==2.3.4"
poetry check --lock
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Notes on the install commands above:

- `pnpm install --frozen-lockfile` refuses to update `pnpm-lock.yaml` and fails if the lockfile does not match `package.json`. This is what blocks an unexpected upstream version from being silently pulled in.
- `verify-store-integrity=true` is also set in the project `.npmrc`; the explicit `pnpm config set` line above just hardens the user-level config too.
- Lifecycle scripts (`preinstall`/`postinstall`) are blocked by default in pnpm v10+. Only the packages listed under `pnpm.onlyBuiltDependencies` in `package.json` are allowed to run install scripts (currently `electron`, `electron-winstaller`, `esbuild`).
- `poetry check --lock` fails fast if `poetry.lock` is out of sync with `pyproject.toml`; `poetry install` then resolves only from the lockfile.
- For a strict lockfile-only Poetry install (no implicit lockfile refresh), pin Poetry with `pip install "poetry==2.3.4"` to match what CI uses.

If you intentionally want to update dependencies, run `pnpm update` / `poetry update` in a dedicated commit and review the resulting lockfile diff before pushing.

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
- Android: native APKs — ABIs `arm64-v8a`, `x86_64`, `armeabi-v7a` (32-bit ARM), plus universal

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

There is a **single** Android variant. Gradle syncs the full `meshchatx/` tree into `app/src/main/python/meshchatx/`, including the offline repository wheel bundle. **ABI packaging** is `universal` (default) or `split` (see `android/app/build.gradle`).

With **`-PmeshchatxAbiPackaging=universal`** (default), each build type is one APK with every selected ABI:

- Debug: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

With **`-PmeshchatxAbiPackaging=split`** and more than one ABI in `-PmeshchatxAbis`, Gradle may emit per-ABI APKs as documented in `android/README.md`.

Notes:

- Release outputs are unsigned by default unless you configure signing (`scripts/sign-android-apks.sh`).
- Android targets the ABIs listed in `android/app/build.gradle` (including `armeabi-v7a` when enabled). Building wheels for `armeabi-v7a` needs an Android SDK on `ANDROID_HOME` (see `android/README.md`).
- Override ABI selection with `-PmeshchatxAbis=<comma-separated list>` or `MESHCHATX_ABIS`. Override packaging with `-PmeshchatxAbiPackaging=universal|split` or `MESHCHATX_ABI_PACKAGING`.
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
| `make install` | Install pnpm and poetry dependencies    |
| `make run`     | Run MeshChatX via poetry                |
| `make build`   | Build frontend                          |
| `make lint`    | Run eslint and ruff                     |
| `make test`    | Run frontend and backend tests          |
| `make clean`   | Remove build artifacts and node_modules |

## Versioning

Current version in this repo is `4.5.1`.

- `package.json` is the JavaScript/Electron version source.
- `meshchatx/src/version.py` is synced from `package.json` using:

```bash
pnpm run version:sync
```

For release consistency, keep version fields aligned where required (`package.json`, `pyproject.toml`, `meshchatx/__init__.py`).

## Security

Security and integrity details:

- [`SECURITY.md`](SECURITY.md)
- [`LEGAL.md`](LEGAL.md)
- Built-in integrity checks and HTTPS/WSS defaults in app runtime
- CI and release builds on GitHub Actions (`.github/workflows/`). Version tags also get **SLSA Build Level 3** provenance (`*.intoto.jsonl` via [slsa-github-generator](https://github.com/slsa-framework/slsa-github-generator)) and a **draft** GitHub release with binaries plus provenance for review before publishing. Verify with [slsa-verifier](https://github.com/slsa-framework/slsa-verifier) (see `SECURITY.md`). On Gitea, only `.gitea/workflows/github-release-sync.yml` is kept: for tags matching `release_*` it waits for successful GitHub workflow runs and publishes assets to a GitHub release using the `GH_PAT` and `GH_REPOSITORY` repository secrets (see `SECURITY.md`).

## Adding a Language

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

## Credits

- [Liam Cottle](https://github.com/liamcottle) - Original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron parser JavaScript work
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## License

Project-owned portions are licensed under 0BSD.
Original upstream portions from Reticulum MeshChat remain under MIT.
See [`LICENSE`](LICENSE) for full text and notices.
