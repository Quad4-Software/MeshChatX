# Installation and setup

MeshChatX can be installed in several ways. All release artifacts that ship the web UI include pre-built frontend assets. You do not need Node.js on the machine that only runs the Python wheel or Docker image.

## Requirements

| Component | Version                                            |
| --------- | -------------------------------------------------- |
| Python    | 3.11 or newer (`pyproject.toml`)                   |
| Node.js   | 24 or newer (development and frontend builds only) |
| pnpm      | 11.1.2 (development)                               |
| UV        | Used by Taskfile and CI                            |

**Browsers for the web UI:** Safari 16.4+, Chrome 111+, Firefox 128+.

## Choose an install method

| Method           | Frontend included | Best for                                 |
| ---------------- | ----------------- | ---------------------------------------- |
| Docker image     | Yes               | Fast server setup on Linux               |
| Python wheel     | Yes               | Headless install without building the UI |
| Linux AppImage   | Yes               | Portable desktop on x64 or arm64         |
| Debian `.deb`    | Yes               | Debian and Ubuntu systems                |
| RPM package      | Yes               | Fedora, RHEL, openSUSE style systems     |
| Electron desktop | Yes               | Integrated desktop with bundled backend  |
| Android APK      | Yes               | Phones, tablets, Meta Quest sideload     |
| From source      | Built locally     | Development and custom builds            |

Release images are published to Docker Hub (`quad4io/meshchatx`) and GHCR (`ghcr.io/quad4-software/meshchatx`).

## Docker

Quick start with Compose:

```bash
docker compose up -d
```

Manual run with a named volume for persistence:

```bash
docker run -d --name reticulum-meshchatx \
  --restart unless-stopped \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Default Compose maps `127.0.0.1:8000` on the host to port `8000` in the container. Data persists in the `meshchatx-config` volume at `/config`.

To bind a host directory instead, mount it at `/config`. The container runs as UID 1000. The host directory must be writable by that user.

## Python wheel

1. Download `reticulum_meshchatx-*-py3-none-any.whl` from [releases](https://github.com/Quad4-Software/MeshChatX/releases).
2. Install with pip, pipx, or uv:

```bash
pip install reticulum_meshchatx-*.whl
```

3. Start the server:

```bash
meshchatx --headless --host 127.0.0.1
```

The `meshchat` command is a compatibility alias for the same entry point.

## Linux AppImage and packages

**AppImage**

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

**Debian package**

```bash
sudo dpkg -i reticulum-meshchatx_*_amd64.deb
```

Adjust the filename for your architecture.

## From source (development)

```bash
task install
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Useful task targets include `task format`, `task lint`, `task test`, and `task build`.

## First launch

On first run MeshChatX creates a random Reticulum identity if you do not pass one on the command line. The identity file is stored under your configured storage directory.

Open the UI at the host and port you chose. HTTPS is enabled by default with a self-signed certificate unless you pass `--no-https` or provide your own PEM files.

## Command-line options

Common flags and environment variables:

| Flag                     | Environment variable     | Default        | Description                        |
| ------------------------ | ------------------------ | -------------- | ---------------------------------- |
| `--host`                 | `MESHCHAT_HOST`          | `127.0.0.1`    | Bind address                       |
| `--port`                 | `MESHCHAT_PORT`          | `8000`         | HTTP or HTTPS port                 |
| `--no-https`             | `MESHCHAT_NO_HTTPS`      | false          | Serve plain HTTP                   |
| `--ssl-cert`             | `MESHCHAT_SSL_CERT`      | auto           | TLS certificate path               |
| `--ssl-key`              | `MESHCHAT_SSL_KEY`       | auto           | TLS private key path               |
| `--headless`             | `MESHCHAT_HEADLESS`      | false          | Do not open a browser              |
| `--auth`                 | `MESHCHAT_AUTH`          | false          | Require HTTP basic auth for the UI |
| `--storage-dir`          | `MESHCHAT_STORAGE_DIR`   | `./storage`    | Application data directory         |
| `--reticulum-config-dir` | (see `--help`)           | `~/.reticulum` | Reticulum configuration            |
| `--identity-file`        | `MESHCHAT_IDENTITY_FILE` | none           | Load identity from file            |
| `--rns-log-level`        | `MESHCHAT_RNS_LOG_LEVEL` | none           | Reticulum log level                |
| `--auto-recover`         | `MESHCHAT_AUTO_RECOVER`  | false          | Attempt SQLite recovery on start   |
| `--emergency`            |                          | false          | Start without database             |
| `--disable-plugins`      |                          | false          | Disable the plugin system          |

CLI flags override environment variables when both are set.

## Reticulum manual bundle

The Reticulum HTML manual is fetched from the upstream website **master** branch at build time. There is no in-app clearnet refresh. After cloning the repository, or before packaging a release, run:

```bash
pnpm run build-docs
```

That command always re-fetches (`--force`) into `meshchatx/public/reticulum-docs-bundled/current/`. CI release builds run the same step. Without a bundled copy the Reticulum tab may show an upload prompt until you build docs or upload a manual ZIP offline.

## Identity bootstrap

You can supply an identity at startup:

- `--identity-file /path/to/identity`
- `--identity-base64` or `--identity-base32` with the corresponding environment variables

Otherwise MeshChatX generates one and saves it under `<storage>/identity`. Additional identities are created from the **Identities** page. Each identity has its own database, LXMF router, and settings while sharing one Reticulum process.

## After install

1. Add at least one **interface** so Reticulum can reach peers.
2. Review **Settings** for display name, theme, language, and LXMF stamp costs.
3. Enable **telephone** in settings if you plan to use audio calls.
4. Open **Documentation** for MeshChatX guides and the Reticulum manual offline.

Platform-specific notes live under **Platform guides** in this documentation bundle.
