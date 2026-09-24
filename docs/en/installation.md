# Installation and setup

MeshChatX can be installed in several ways. All release artifacts that ship the web UI include pre-built frontend assets. You do not need Node.js on the machine that only runs the Python wheel or Docker image.

## Requirements

| Component | Version                                            |
| --------- | -------------------------------------------------- |
| Python    | 3.11 or newer (pyproject.toml)                     |
| Node.js   | 24 or newer (development and frontend builds only) |
| pnpm      | 11.1.2 (development)                               |
| UV        | Used by Taskfile and CI                            |

**Browsers for the web UI:** Safari 16.4+, Chrome 111+, Firefox 128+.

## Choose an install method

| Method                     | Frontend included | Best for                                 |
| -------------------------- | ----------------- | ---------------------------------------- |
| Docker image               | Yes               | Fast server setup on Linux               |
| PyPI (reticulum-meshchatx) | Yes               | Headless install without building the UI |
| Release wheel              | Yes               | Same as PyPI from a GitHub artifact      |
| Python zipapp (.pyz)       | Yes               | Single-file download for a known Python  |
| Linux AppImage             | Yes               | Portable desktop on x64 or arm64         |
| Flatpak                    | Yes               | Desktop from cdn.quad4.io                |
| Debian .deb                | Yes               | Debian and Ubuntu systems                |
| RPM package                | Yes               | Fedora, RHEL, openSUSE style systems     |
| Electron desktop           | Yes               | Integrated desktop with bundled backend  |
| Android APK                | Yes               | Phones, tablets, Meta Quest sideload     |
| From source                | Built locally     | Development and custom builds            |

Release images are published to Docker Hub (quad4io/meshchatx) and GHCR (ghcr.io/quad4-software/meshchatx). Tag suffixes: none for the standard Alpine image, -hardened for Chainguard/Wolfi, -extra for Alpine plus i2pd and yggdrasil (VARIANT=extra on the same Dockerfile).

## Docker

Quick start with Compose:

```bash
docker compose up -d
```

Basic run:

```bash
docker run -d --name reticulum-meshchatx \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Hardened example with a named volume for persistence:

```bash
docker run -d --name reticulum-meshchatx \
  --restart unless-stopped \
  --init \
  --user 1000:1000 \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,size=256m \
  --tmpfs /home/meshchat:nosuid,size=64m \
  --cpus=2.0 \
  --memory=1g \
  --memory-reservation=256m \
  --pids-limit=512 \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Default Compose maps 127.0.0.1:8000 on the host to port 8000 in the container. Data persists in the meshchatx-config volume at /config.

Compose caps Docker's own json-file logs at **10 MB x 5 files** per container (logging.options). App file logs under /config already rotate separately (meshchatx.log, about 20 MB). For a bare docker run without Compose, add the same limits or the host can fill under /var/lib/docker/containers/:

```bash
docker run -d --name reticulum-meshchatx \
  --log-opt max-size=10m --log-opt max-file=5 \
  -p 127.0.0.1:8000:8000 \
  -v meshchatx-config:/config \
  ghcr.io/quad4-software/meshchatx:latest
```

Coolify and other hosts that ignore Compose logging options should set equivalent log rotation in the platform UI.

To bind a host directory instead, mount it at /config. The container runs as UID 1000. The host directory must be writable by that user. When the container is started as root, the entrypoint chowns /config to the meshchat user automatically before dropping privileges.

Run only **one** MeshChatX instance per /config volume. Startup takes an exclusive storage lock so schema migration and runtime do not overlap. For Docker or Coolify, use a single replica on that volume and replace containers in a rolling stop-then-start order instead of two replicas sharing one config path.

### Kubernetes

The image ENTRYPOINT chowns /config (when run as root) and then execs the given argv as the meshchat user. Overriding `command`/`args` in a Pod spec replaces the image CMD, so the entrypoint prepends `meshchatx` when argv starts with a flag. Both of these work:

```yaml
# flags only: entrypoint runs `meshchatx --host=0.0.0.0 ...`
args: ["--host=0.0.0.0", "--headless"]

# or a full command, used as-is
command: ["python", "/opt/venv/bin/meshchatx"]
args: ["--host=0.0.0.0", "--headless"]
```

The same single-instance-per-volume rule applies: use one replica per PVC and a Recreate-style rollout so two pods never share /config.

Mounting TLS material as a Secret is supported. Point --ssl-cert and --ssl-key at the mounted files. The Linux filesystem sandbox grants read access to the parent directory of each path automatically:

```yaml
args:
    - --ssl-cert=/tls/tls.crt
    - --ssl-key=/tls/tls.key
volumeMounts:
    - name: tls
      mountPath: /tls
volumes:
    - name: tls
      secret:
          secretName: meshchatx-tls
```

### Public demo instance (Coolify)

For a read-only mesh showcase on [Coolify](https://coolify.io/docs/knowledge-base/docker/compose), deploy [docker-compose.demo.yml](../../docker/docker-compose.demo.yml). For a normal (non-demo) Coolify deployment, use [docker-compose.coolify.yml](../../docker/docker-compose.coolify.yml).

Demo compose expects settings like:

```bash
MESHCHAT_DEMO_MODE=1
MESHCHAT_AUTH=1
MESHCHAT_DEMO_AUTH_PASSWORD=demo   # default showcase password
MESHCHAT_AUTH_PAGE_HINT=...        # optional login-page text
```

MESHCHAT_DEMO_MODE=1 blocks outbound mesh actions and almost all API mutations. Optional MESHCHAT_AUTH_PAGE_HINT shows custom text on the login page (for example Username: demo and Password: demo). Assign a domain with container port **8000**, for example https://meshchatx.example.com:8000. Do not set MESHCHAT_AUTH_BYPASS=1 on a public host.

## Running behind a reverse proxy

MeshChatX enforces a same-authority Origin check on the WebSocket endpoints (/ws and /ws/telephone/audio). The browser sends an Origin built from the public scheme, host, and port, while the backend sees only the hop from the proxy. To make the comparison work, the proxy addresses must be marked trusted.

Set MESHCHAT_TRUSTED_PROXIES to a comma, semicolon, or space separated list of proxy IPs or CIDRs:

```bash
MESHCHAT_TRUSTED_PROXIES="10.0.0.0/8 192.168.1.2"
```

The same value is persisted per instance as `trusted_proxy_cidrs` in <storage>/app_security.json (also writable through the app security settings API). The environment variable wins when both are set. When the direct peer matches, the app trusts X-Forwarded-Host, X-Forwarded-Proto, and X-Forwarded-Port for the WebSocket origin check and X-Forwarded-For for client-IP attribution (login lockouts and the optional web UI IP allowlist). Keep the list tight: any address in it can assert the public authority and the client IP.

### TLS layouts

- **TLS termination at the proxy (recommended):** run MeshChatX with --no-https and have the proxy send X-Forwarded-Proto. With MESHCHAT_TRUSTED_PROXIES set, https browser origins pass the WebSocket check even though the backend hop is plain HTTP.
- **TLS passthrough:** the proxy routes raw TLS by SNI and MeshChatX terminates with its own certificate. Works with no extra app configuration.
- **HTTPS backend:** the proxy speaks TLS to the app port. The proxy must trust the app certificate (self-signed by default, so configure skip-verify) or you must supply a certificate it accepts via --ssl-cert/--ssl-key.

### WebSocket forwarding

The live UI channel and call audio use WebSockets. The proxy must forward the Upgrade and Connection headers and allow long-lived connections on /ws and /ws/telephone/audio. An nginx server block that covers the whole app, WebSockets included:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;
}
```

Traefik needs no header configuration for this: it forwards Host and the X-Forwarded-* family by default and upgrades WebSocket connections automatically.

## Python package (PyPI or release wheel)

Published on PyPI as [reticulum-meshchatx](https://pypi.org/project/reticulum-meshchatx/). Wheels include the built web assets. No Node.js on the runtime host.

```bash
pip install reticulum-meshchatx
# or
pipx install reticulum-meshchatx
# or
uv tool install reticulum-meshchatx
```

```bash
meshchatx --headless --host 127.0.0.1
```

The meshchat command is a compatibility alias for the same entry point.

From a GitHub release artifact instead of PyPI:

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
```

On hosts where `libopus` is installed but `libogg` is not, LXST's vendored pyogg can raise `NameError: c_int_p` on import. MeshChatX applies a ctypes compatibility fix at startup (the same patch Docker runs after install). Optional telephony audio still needs the usual Opus/Ogg system libraries when you use those codecs.

## Python zipapp (.pyz)

GitHub releases include a meshchatx-py<ver>-linux-<arch>.pyz zipapp built with shiv. It contains the web UI, backend, and all dependencies in one file. Run it with the matching Python version:

```bash
python3.11 ./meshchatx-py311-linux-x64.pyz --headless --host 127.0.0.1
python3.14 ./meshchatx-py314-linux-x64.pyz --headless --host 127.0.0.1
```

First run extracts the dependency cache to ~/.shiv. The PYZ is architecture and Python-version specific. Pick the file that matches both the CPU and the interpreter on the host.

## From source (git clone)

HTTPS:

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
cd MeshChatX
```

Over Reticulum with rngit (git-remote-rns):

```bash
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
cd MeshChatX
```

Then use Make or Task (equivalent targets):

```bash
make install
make build
make run
```

```bash
task install
task build
task run
```

## Linux AppImage and packages

**AppImage**

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

**Debian package**

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

Adjust the filename for your architecture.

**RPM**

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

Download the .rpm only when the release includes one. CI uploads RPM when the packaging job produces it.

**Flatpak**

```bash
flatpak install --from https://cdn.quad4.io/flatpak/meshchatx-stable.flatpakref
flatpak run com.meshchatx.app
flatpak update
```

Swap in `meshchatx-beta.flatpakref` or `meshchatx-testing.flatpakref` for those channels. If a leftover GitHub Pages remote is still named `meshchatx`, run `flatpak remote-delete meshchatx` first.

## Linux desktop emoji fonts

The emoji picker uses system fonts through Electron/Chromium. Empty squares mean a color emoji package is missing. Install one and restart the app.

| Distro               | Install command                           |
| -------------------- | ----------------------------------------- |
| Arch, Artix, Manjaro | pacman -S noto-fonts-emoji                |
| Debian, Ubuntu       | apt install fonts-noto-color-emoji        |
| Fedora               | dnf install google-noto-emoji-color-fonts |

Example:

```bash
# Arch family
sudo pacman -S noto-fonts-emoji

# Debian / Ubuntu
sudo apt install fonts-noto-color-emoji
```

If glyphs still fail, run fc-cache -fv or wait until the next login. noto-fonts helps on minimal installs that lack other symbol coverage.

## From source (development)

```bash
task install
task dev
```

task dev starts the HTTPS backend on 127.0.0.1:8000 and Vite on [http://127.0.0.1:5173](http://127.0.0.1:5173). Open that Vite URL. The [Vue DevTools](https://devtools.vuejs.org/) overlay is injected for this serve only. vite build / task run never ship it (**VUE_PROD_DEVTOOLS** is false). Set MESHCHAT_VUE_DEVTOOLS=0 to hide the overlay. Click a component in the inspector to open it in the editor (LAUNCH_EDITOR, default code).

Python breakpoints: task debug is the same stack with [debugpy](https://github.com/microsoft/debugpy) listening on 127.0.0.1:5678 (never 0.0.0.0). Run **MeshChatX: Vite + Python** from the debugger, or start task debug and attach **Backend: Attach debugpy**. task debug:wait pauses the backend until that attach happens.

A production-like run without HMR:

```bash
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

Useful task targets include task format, task lint, task test, task test:fe:ui, and task build.

## First launch

On first run MeshChatX creates a random Reticulum identity if you do not pass one on the command line. The identity file is stored under your configured storage directory.

Open the UI at the host and port you chose. HTTPS is enabled by default with a self-signed certificate unless you pass --no-https or provide your own PEM files.

## Command-line options

Common flags and environment variables:

| Flag                       | Environment variable                    | Default              | Description                                                                            |
| -------------------------- | --------------------------------------- | -------------------- | -------------------------------------------------------------------------------------- |
| --host                     | MESHCHAT_HOST                           | 127.0.0.1            | Bind address                                                                           |
| --port                     | MESHCHAT_PORT                           | 8000                 | HTTP or HTTPS port                                                                     |
| --no-https                 | MESHCHAT_NO_HTTPS                       | false                | Serve plain HTTP                                                                       |
| --ssl-cert                 | MESHCHAT_SSL_CERT                       | auto                 | TLS certificate path                                                                   |
| --ssl-key                  | MESHCHAT_SSL_KEY                        | auto                 | TLS private key path                                                                   |
| --headless                 | MESHCHAT_HEADLESS                       | false                | Do not open a browser                                                                  |
| --auth                     | MESHCHAT_AUTH                           | false                | Require password auth for the UI                                                       |
| --reset-password           | MESHCHAT_RESET_PASSWORD                 | false                | Clear the stored password hash so a new one can be set in the UI                       |
| --storage-dir              | MESHCHAT_STORAGE_DIR                    | ./storage            | Application data directory                                                             |
| --public-dir               | MESHCHAT_PUBLIC_DIR                     | auto/bundled         | Frontend files. Needed for source installs without bundled assets.                     |
| --reticulum-config-dir     | MESHCHAT_RETICULUM_CONFIG_DIR           | ~/.reticulum         | Reticulum configuration                                                                |
| --data-dir                 | MESHCHAT_DATA_DIR                       | none                 | Portable root (storage + .reticulum subdirs when the two paths above are unset)        |
| --identity-file            | MESHCHAT_IDENTITY_FILE                  | none                 | Load identity from file                                                                |
| --identity-base64          | MESHCHAT_IDENTITY_BASE64                | none                 | Load identity from a base64 string                                                     |
| --identity-base32          | MESHCHAT_IDENTITY_BASE32                | none                 | Load identity from a base32 string                                                     |
| --generate-identity-file   |                                         | none                 | Write a new identity to PATH and exit                                                  |
| --generate-identity-base64 |                                         | none                 | Print a new identity as base64 and exit                                                |
| --rns-log-level            | MESHCHAT_RNS_LOG_LEVEL                  | none                 | Reticulum log level                                                                    |
| (env only)                 | MESHCHAT_RNS_LOG_DEST                   | logging              | stdout keeps RNS on the console. With a log dir, default is the rotating Python logger |
| (env only)                 | MESHCHAT_LOG_DIR                        | auto                 | Log file directory                                                                     |
| --auto-recover             | MESHCHAT_AUTO_RECOVER                   | false                | Attempt SQLite recovery on start                                                       |
| --emergency                | MESHCHAT_EMERGENCY                      | false                | Start without database                                                                 |
| --disable-plugins          | MESHCHAT_DISABLE_PLUGINS                | false                | Disable the plugin system                                                              |
| --demo                     | MESHCHAT_DEMO_MODE                      | false                | Public read-only demo mode                                                             |
| --no-crash-recovery        | MESHCHAT_NO_CRASH_RECOVERY              | false                | Disable the crash recovery and diagnostic system                                       |
| --self-check               | MESHCHAT_SELF_CHECK                     | false                | Run startup diagnostics and exit 0 on pass, 1 on fail                                  |
| --memory-diag              | MESHCHAT_MEMORY_DIAG                    | false                | Enable tracemalloc memory diagnostics                                                  |
| --gitea-base-url           | MESHCHAT_GITEA_BASE_URL                 | none                 | Gitea instance base URL                                                                |
| --backup-db                |                                         | none                 | Create a database backup zip at PATH and exit                                          |
| --restore-db               |                                         | none                 | Restore the database from a zip or db file and exit                                    |
| --list-backups             |                                         | none                 | List automatic backups in storage (JSON) and exit                                      |
| --export-backup            |                                         | none                 | Write a new backup zip to PATH, or copy backup NAME to DEST, and exit                  |
| --restore-from-snapshot    | MESHCHAT_RESTORE_SNAPSHOT               | none                 | Restore the database from a snapshot name or path on startup                           |
| --test-exception-message   |                                         | none                 | Throw an exception at startup (Electron error dialog testing)                          |
| (env only)                 | MESHCHAT_TRUSTED_PROXIES                | none                 | Proxy IPs/CIDRs allowed to supply X-Forwarded-* headers (see reverse proxy section)    |
| (env only)                 | MESHCHAT_LANDLOCK                       | auto                 | Linux filesystem sandbox: 1/0 to force on or off                                       |
| (env only)                 | MESHCHAT_SECCOMP                        | auto                 | Linux seccomp syscall filter: 1/0 to force on or off                                   |
| (env only)                 | MESHCHAT_APPCONTAINER                   | off                  | Windows AppContainer sandbox: 1 forces on, 0 forces off, auto enables with fallback    |
| (env only)                 | MESHCHAT_FORCE_WEB_AUDIO                | false                | Force browser-side call audio (no host audio device)                                   |
| (env only)                 | MESHCHAT_EXPERIMENTAL_WEBTRANSPORT      | false                | Enable the experimental WebTransport live channel                                      |
| (env only)                 | MESHCHAT_LIBCODEC2_PATH                 | auto                 | Explicit libcodec2 shared library path                                                 |
| (env only)                 | MESHCHAT_NATIVE_LIB_DIR                 | auto                 | Directory holding native codec libraries                                               |
| (env only)                 | MESHCHAT_PRE_MIGRATE_BACKUP_KEEP        | 5                    | Number of pre-migration backups kept in storage                                        |
| (env only)                 | MESHCHAT_SKIP_PRE_MIGRATE_BACKUP        | false                | Skip the safety backup before schema migrations                                        |
| (env only)                 | MESHCHAT_SKIP_UPSTREAM_FOLDER_MIGRATION | false                | Do not auto-migrate the legacy upstream data folder                                    |
| (env only)                 | MESHCHAT_SKIP_LEGACY_MIGRATION_UI       | false                | Skip the legacy migration prompt in the UI                                             |
| (env only)                 | MESHCHAT_REPOSITORY_EXTRA_PIP           | none                 | Extra pip arguments for the in-app repository installer                                |
| (env only)                 | MESHCHAT_BOT_RETICULUM_CONFIG_DIR       | none                 | Reticulum config dir for spawned bot processes                                         |
| (env only)                 | MESHCHAT_AUTH_PAGE_HINT                 | none                 | Custom text shown on the login page                                                    |
| (env only)                 | MESHCHAT_OIDC_ENABLED                   | none                 | Force OIDC single sign-on on or off (overrides stored config)                          |
| (env only)                 | MESHCHAT_OIDC_ISSUER                    | none                 | OIDC issuer URL. Setting it implies enabled                                            |
| (env only)                 | MESHCHAT_OIDC_CLIENT_ID                 | none                 | OIDC client ID                                                                         |
| (env only)                 | MESHCHAT_OIDC_CLIENT_SECRET             | none                 | OIDC client secret                                                                     |
| (env only)                 | MESHCHAT_OIDC_DISPLAY_NAME              | none                 | Label for the SSO button                                                               |
| (env only)                 | MESHCHAT_OIDC_SCOPES                    | openid profile email | OIDC scopes                                                                            |

The next group disables real security controls. They exist for tests and development and must not be set in production:

| Flag       | Environment variable       | Default | Description                                    |
| ---------- | -------------------------- | ------- | ---------------------------------------------- |
| (env only) | MESHCHAT_DISABLE_CSRF      | false   | Disable CSRF validation on mutating API calls  |
| (env only) | MESHCHAT_AUTH_BYPASS       | false   | Skip UI authentication entirely                |
| (env only) | MESHCHAT_SKIP_STORAGE_LOCK | false   | Do not take the exclusive single-instance lock |

CLI flags override environment variables when both are set.

### Portable installs (removable media, Tails, USB sticks)

MeshChatX already supports relocating all persistent state off the home directory. Use either explicit paths or a single data root:

```bash
export PERSIST="/media/amnesia/Persistent/meshchatx"
mkdir -p "$PERSIST"

meshchatx --headless \
  --data-dir="$PERSIST"
```

That creates and uses $PERSIST/storage for MeshChatX (identities, SQLite, plugins) and $PERSIST/.reticulum for Reticulum interfaces and transport config. You can set the same layout with environment variables:

```bash
export MESHCHAT_DATA_DIR="$PERSIST"
meshchatx --headless
```

Equivalent explicit form (overrides any --data-dir subpaths when you set these yourself):

```bash
meshchatx --headless \
  --storage-dir="$PERSIST/storage" \
  --reticulum-config-dir="$PERSIST/.reticulum"
```

The Electron desktop app (AppImage, portable exe, macOS bundle) honors the same --data-dir / --storage-dir / --reticulum-config-dir flags (or the matching MESHCHAT_DATA_DIR / MESHCHAT_STORAGE_DIR / MESHCHAT_RETICULUM_CONFIG_DIR environment variables) on every platform, not just Windows:

```bash
export PERSIST="/media/amnesia/Persistent/meshchatx"
./MeshChatX-x86_64.AppImage --data-dir="$PERSIST"
```

On Windows portable exe builds, storage and Reticulum config also default next to the .exe when PORTABLE_EXECUTABLE_DIR is set (used by the portable target automatically), without needing any flags.

## Reticulum manual bundle

The Reticulum HTML manual is fetched from the upstream website **master** branch at build time by default (clearnet ZIP). There is no in-app clearnet refresh. After cloning the repository, or before packaging a release, run:

```bash
pnpm run build-docs
```

CI release builds use the clearnet path. Without a bundled copy the Reticulum tab may show an upload prompt until you build docs or upload a manual ZIP offline.

## Advanced: Optional RNS-only installation (pip-rns)

MeshChatX includes optional tooling to pull rns, lxmf, lxst, and the Reticulum manual from markqvist's rngit remotes over the mesh instead of clearnet.

**Note:** Installing Python packages over RNS is slower than PyPI and fits mesh-only hosts with restricted clearnet. PyPI remains the default path for CI and standard development.

| Remote                                                     | Purpose               |
| ---------------------------------------------------------- | --------------------- |
| rns://7649a50d84610232d1416b41d2896aff/reticulum/reticulum | RNS package           |
| rns://7649a50d84610232d1416b41d2896aff/reticulum/lxmf      | LXMF package          |
| rns://7649a50d84610232d1416b41d2896aff/reticulum/lxst      | LXST package          |
| rns://7649a50d84610232d1416b41d2896aff/reticulum/website   | Manual / website HTML |

This uses [pip-rns](https://github.com/Quad4-Software/pip-rns) for the Python packages and git + git-remote-rns for the docs tree. Default aliases live in scripts/pip-rns/aliases.

**Bootstrap note:** pip-rns needs a working Reticulum stack to reach the remotes. Install rns once from PyPI, a wheel, or an existing environment, then use the mesh path for updates.

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

Set PIP_RNS_CONFIG to point at another aliases directory if needed. MESHCHATX_RETICULUM_DOCS_URL=rns://... also works for a custom website remote.

## Identity bootstrap

You can supply an identity at startup:

- --identity-file /path/to/identity
- --identity-base64 or --identity-base32 with the corresponding environment variables

Otherwise MeshChatX generates one and saves it under `<storage>/identity`. Additional identities are created from the **Identities** page. Each identity has its own database, LXMF router, and settings while sharing one Reticulum process.

## After install

1. Add at least one **interface** so Reticulum can reach peers.
2. Review **Settings** for display name, theme, language, and LXMF stamp costs.
3. Enable **telephone** in settings if you plan to use audio calls.
4. Open **Documentation** for MeshChatX guides and the Reticulum manual offline.

Platform-specific notes live under **Platform guides** in this documentation bundle, including **Linux sandboxing** (Firejail and Bubblewrap). Offline packaging, Android APK builds, and docker/Dockerfile.build are in **Building from source and packaging**. Contributor task targets and locales are in **Development**.
