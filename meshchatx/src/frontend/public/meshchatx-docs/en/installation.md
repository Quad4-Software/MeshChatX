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

The Reticulum HTML manual is fetched from the upstream website **master** branch at build time by default (clearnet ZIP). There is no in-app clearnet refresh. After cloning the repository, or before packaging a release, run:

```bash
pnpm run build-docs
```

CI release builds use the clearnet path. Without a bundled copy the Reticulum tab may show an upload prompt until you build docs or upload a manual ZIP offline.

## Advanced: Optional RNS-only installation (pip-rns)

MeshChatX includes optional tooling to pull `rns`, `lxmf`, `lxst`, and the Reticulum manual from markqvist's rngit remotes over the mesh instead of clearnet.

**Note:** Installing Python packages over RNS is significantly slower than PyPI and is intended for use in environments with mesh access but restricted clearnet. PyPI remains the default and recommended path for CI and standard development.

| Remote                                                       | Purpose               |
| ------------------------------------------------------------ | --------------------- |
| `rns://7649a50d84610232d1416b41d2896aff/reticulum/reticulum` | RNS package           |
| `rns://7649a50d84610232d1416b41d2896aff/reticulum/lxmf`      | LXMF package          |
| `rns://7649a50d84610232d1416b41d2896aff/reticulum/lxst`      | LXST package          |
| `rns://7649a50d84610232d1416b41d2896aff/reticulum/website`   | Manual / website HTML |

This uses [pip-rns](https://github.com/Quad4-Software/pip-rns) for the Python packages and `git` + `git-remote-rns` for the docs tree. Default aliases live in `scripts/pip-rns/aliases`.

**Bootstrap note:** pip-rns needs a working Reticulum stack to reach the remotes. Install `rns` once from PyPI, a wheel, or an existing environment, then use the mesh path for updates.

```bash
# Optional: Install/update rns, lxmf, lxst into the uv environment over RNS
task deps:backend:rns

# Optional: Bundle the Reticulum manual from the rngit website remote
task docs:rns
```

Equivalent direct commands:

```bash
bash scripts/pip-rns-deps.sh
python scripts/build/fetch_reticulum_manual.py --force --via-rns
```

Set `PIP_RNS_CONFIG` to point at another aliases directory if needed. `MESHCHATX_RETICULUM_DOCS_URL=rns://...` also works for a custom website remote.

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
