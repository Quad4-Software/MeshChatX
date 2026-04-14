# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

A extensively modified and feature-rich fork of Reticulum MeshChat by Liam Cottle.

This project is independent from the original Reticulum MeshChat project and is not affiliated with it.

- Website: [meshchatx.com](https://meshchatx.com)
- Source: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Official Mirror: [github.com/Sudo-Ivan/MeshChatX](https://github.com/Sudo-Ivan/MeshChatX) - Also used for Windows and MacOS builds for the moment.
- Releases: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- TODO: [Boards](https://git.quad4.io/RNS-Things/MeshChatX/projects)

## Important Changes from Reticulum MeshChat

- Uses LXST
- Replaced Peewee ORM with raw SQL.
- Replaced Axios with native fetch.
- Uses latest Electron.
- .whls ships with webserver and built-in frontend assets for more deployment options.
- i18n
- PNPM and Poetry for dependency management.

> [!WARNING]
> MeshChatX is not guaranteed to be wire/data compatible with older Reticulum MeshChat releases. Back up data before migration/testing.

> [!WARNING]
> Legacy systems are not fully supported yet. Current baseline is Python `>=3.11` and Node `>=24`.

## Requirements

- Python `>=3.11` (from `pyproject.toml`)
- Node.js `>=24` (from `package.json`)
- pnpm `10.32.1` (from `package.json`)
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

- The release workflow explicitly builds Linux `x64` and `arm64` AppImage + DEB.
- RPM is also attempted by release workflow and uploaded when produced.

## Quick Start: Docker

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
pnpm install
pip install poetry
poetry install
pnpm run build-frontend
poetry run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

## Run sandboxed (Linux)

To run the native `meshchatx` binary (alias: `meshchat`) with extra filesystem isolation, you can use **Firejail** or **Bubblewrap** (`bwrap`) while keeping normal network access for Reticulum and the web UI. Full examples (pip/pipx, Poetry, USB serial notes) are in:

- [`docs/meshchatx_linux_sandbox.md`](docs/meshchatx_linux_sandbox.md)

The same page appears in the in-app **Documentation** list (MeshChatX docs) when served from the bundled or synced `meshchatx-docs` files.

## Linux desktop: emoji fonts

The emoji picker renders standard Unicode emoji using your system fonts (Electron/Chromium). If emoji show as empty squares (“tofu”), install a color emoji package and restart the app.

| Family (examples) | Package |
| ----------------- | ------- |
| Arch Linux, Artix, Manjaro | `noto-fonts-emoji` (`sudo pacman -S noto-fonts-emoji`) |
| Debian, Ubuntu | `fonts-noto-color-emoji` (`sudo apt install fonts-noto-color-emoji`) |
| Fedora | `google-noto-emoji-color-fonts` |

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

## Architecture Support Summary

- Docker image: `amd64`, `arm64`
- Linux AppImage: `x64`, `arm64`
- Linux DEB: `x64`, `arm64`
- Windows: `x64`, `arm64` (build scripts available)
- macOS: build scripts available (`arm64`, `universal`) for local build environments
- Android: build workflow and Android project are present in this repository

## Android

Use the dedicated docs:

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

Current version in this repo is `4.4.0`.

- `package.json` is the JavaScript/Electron version source.
- `meshchatx/src/version.py` is synced from `package.json` using:

```bash
pnpm run version:sync
```

For release consistency, keep version fields aligned where required (`package.json`, `pyproject.toml`, `meshchatx/__init__.py`).

## Security

Security and integrity details:

- [`SECURITY.md`](SECURITY.md)
- Built-in integrity checks and HTTPS/WSS defaults in app runtime
- CI scanning workflows in `.gitea/workflows/`

## Adding a Language

Locale discovery is automatic. To add a new language, create a single JSON file:

1. Generate a blank template from `en.json`:

```bash
python scripts/generate_locale_template.py
```

This writes `locales.json` with every key set to an empty string.

2. Rename it to your language code and move it into the locales directory:

```bash
mv locales.json meshchatx/src/frontend/locales/xx.json
```

3. Set `_languageName` at the top of the file to the native name of the language (e.g. `"Espanol"`, `"Francais"`). This is displayed in the language selector.

4. Translate all remaining values.

5. Run `pnpm test -- tests/frontend/i18n.test.js --run` to verify key parity with `en.json`.

No other code changes are required. The app, language selector, and tests all discover locales from the `meshchatx/src/frontend/locales/` directory at build time.

## Credits

- [Liam Cottle](https://github.com/liamcottle) - Original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron parser JavaScript work
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
