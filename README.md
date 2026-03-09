# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

A extensively modified and feature-rich fork of Reticulum MeshChat by Liam Cottle.

This project is independent from the original Reticulum MeshChat project and is not affiliated with it.

- Source: [git.quad4.io/RNS-Things/MeshChatX](https://git.quad4.io/RNS-Things/MeshChatX)
- Releases: [git.quad4.io/RNS-Things/MeshChatX/releases](https://git.quad4.io/RNS-Things/MeshChatX/releases)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- TODO: [`TODO.md`](TODO.md)

## Important Notes

- Uses LXST
- Replaced Peewee ORM with raw SQL.

> [!WARNING]
> MeshChatX is not guaranteed to be wire/data compatible with older Reticulum MeshChat releases. Back up data before migration/testing.

> [!WARNING]
> Legacy systems are not fully supported yet. Current baseline is Python `>=3.11` and Node `>=24`.

## Demo And Screenshots

<video src="https://strg.0rbitzer0.net/raw/62926a2a-0a9a-4f44-a5f6-000dd60deac1.mp4" controls="controls" style="max-width: 100%;"></video>

### UI Previews

![Phone](screenshots/phone.png)
![Network Visualiser](screenshots/network-visualiser.png)
![Archives](screenshots/archives.png)
![Identities](screenshots/identities.png)

## Requirements

- Python `>=3.11` (from `pyproject.toml`)
- Node.js `>=24` (from `package.json`)
- pnpm `10.30.0` (from `package.json`)
- Poetry (used by `Taskfile.yml` and CI workflows)

## Nix (flake.nix)

This repo includes a Nix flake at `flake.nix`.

### Enter the dev shell

```bash
nix develop
```

The flake dev shell provides Python, Poetry, Node, pnpm, Task, packaging tools (`rpm`, `dpkg`, `fakeroot`), Android build tools, and Docker tooling.

### Build the default Nix package

```bash
nix build .#default
```

### Typical workflow inside `nix develop`

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
meshchat --headless
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
poetry run meshchat --headless --host 127.0.0.1
```

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

| Argument        | Environment Variable   | Default      | Description                                                                  |
| --------------- | ---------------------- | ------------ | ---------------------------------------------------------------------------- |
| `--host`        | `MESHCHAT_HOST`        | `127.0.0.1`  | Web server bind address                                                      |
| `--port`        | `MESHCHAT_PORT`        | `8000`       | Web server port                                                              |
| `--no-https`    | `MESHCHAT_NO_HTTPS`    | `false`      | Disable HTTPS                                                                |
| `--headless`    | `MESHCHAT_HEADLESS`    | `false`      | Do not auto-launch browser                                                   |
| `--auth`        | `MESHCHAT_AUTH`        | `false`      | Enable basic auth                                                            |
| `--storage-dir` | `MESHCHAT_STORAGE_DIR` | `./storage`  | Data directory                                                               |
| `--public-dir`  | `MESHCHAT_PUBLIC_DIR`  | auto/bundled | Frontend files directory (needed for source installs without bundled assets) |

## Branches

| Branch   | Purpose                                                        |
| -------- | -------------------------------------------------------------- |
| `master` | Stable releases. Production-ready code only.                   |
| `dev`    | Active development. May contain breaking or incomplete changes.|

## Development

Common tasks from `Taskfile.yml`:

```bash
task install
task lint:all
task test:all
task build:all
```

`Makefile` shortcuts are also available:

| Command      | Description                              |
| ------------ | ---------------------------------------- |
| `make install` | Install pnpm and poetry dependencies   |
| `make run`     | Run MeshChatX via poetry               |
| `make build`   | Build frontend                         |
| `make lint`    | Run eslint and ruff                    |
| `make test`    | Run frontend and backend tests         |
| `make clean`   | Remove build artifacts and node_modules|

## Versioning

Current version in this repo is `4.3.0`.

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

## Credits

- [Liam Cottle](https://github.com/liamcottle) - Original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron parser JavaScript work
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST
