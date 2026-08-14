# Reticulum MeshChatX

[Русский](lang/README.ru.md) | [Deutsch](lang/README.de.md) | [Italiano](lang/README.it.md) | [中文](lang/README.zh.md) | [日本語](lang/README.ja.md)

Fork of [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat) by Liam Cottle. MeshChatX adds LXST voice calls, RRC relay chat, Nomad map overlays, plugins, raw SQLite (no Peewee), and Electron 41 desktop builds.

This project is independent from the original Reticulum MeshChat project and is not affiliated with it.

- Website: [meshchatx.com](https://meshchatx.com)
- Source: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Mirror: [lavaforge.org/Reticulum-Things/MeshChatX](https://lavaforge.org/Reticulum-Things/MeshChatX)
- Releases: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)
- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Donate: [donate.md](donate.md)
- LXMF: `f489752fbef161c64d65e385a4e9fc74`
- Umbrel App Store: [apps.umbrel.com/app/meshchatx](https://apps.umbrel.com/app/meshchatx)

<a href="https://apps.obtainium.imranr.dev/redirect.html?r=obtainium://add/https://github.com/Quad4-Software/MeshChatX"><img src="https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/badge_obtainium.png" height="60" alt="Get it on Obtainium"></a>

rngit NomadNet Node: `132f67e79d9b24aad014e93015fb858f:/page/index.mu`

```bash
git clone rns://06a54b505bb67b25ef3f8097e8001edc/public/MeshChatX
```

## Changes from Reticulum MeshChat

- LXST for calls
- [RRC](https://rrc.kc1awv.net/0) relay chat
- More tools, panes, and tabs
- Map with MBTiles, plus remote KMZ/KML/GeoJSON overlays (NomadNet /file/ and RNGit sparse fetch)
- Raw SQL instead of Peewee
- Native fetch instead of Axios
- Electron 41.x (bundled Node 24)
- Wheels ship with the web server and built frontend assets
- i18n
- pnpm and UV for dependencies

## Requirements

- Python 3.11 or newer
- Node.js 24 or newer
- pnpm 11.1.2
- UV

The bundled web UI needs Safari 16.4, Chrome 111, or Firefox 128 or later.

## Install methods

| Method         | Frontend assets | Architectures             | Best for                                  |
| -------------- | --------------- | ------------------------- | ----------------------------------------- |
| Docker image   | Yes             | linux/amd64, linux/arm64  | Linux servers                             |
| Python wheel   | Yes             | Any Python-supported arch | Headless/web install without a Node build |
| Linux AppImage | Yes             | x64, arm64                | Portable desktop                          |
| Debian package | Yes             | x64, arm64                | Debian/Ubuntu                             |
| RPM package    | Yes             | CI-runner dependent       | Fedora/RHEL/openSUSE                      |
| From source    | Built locally   | Host arch                 | Development and custom builds             |

Tagged releases build Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, and Android APKs (when the tag is on dev or master) in [build-release.yml](.github/workflows/build-release.yml). The container image is [docker.yml](.github/workflows/docker.yml). Branch and PR Android CI is [android-build.yml](.github/workflows/android-build.yml). Linux x64 and arm64 AppImage + DEB are built on GitHub. RPM is uploaded when the job produces one.

## Docker

- Docker Hub: `quad4io/meshchatx`
- GHCR: `ghcr.io/quad4-software/meshchatx`
- Default tags (for example `:latest`) are Alpine. Use `-hardened` for Chainguard/Wolfi, or `-extra` for Alpine plus i2pd and yggdrasil (`:latest-extra`, same Dockerfile with `VARIANT=extra`).

```bash
docker compose up -d
```

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

Swap in `quad4io/meshchatx:latest` if you prefer Docker Hub.

Default compose mapping: host 127.0.0.1:8000 to container port 8000, named volume `meshchatx-config` to `/config`. That volume works with the image meshchat user (UID 1000) without bind-mount permission fixes.

To bind a host directory instead, use `-v "$(pwd)/meshchat-config:/config"` (or the same path in Compose volumes). The container runs as UID 1000, so that directory must be writable by uid 1000:

```bash
sudo chown -R 1000:1000 ./meshchat-config
```

Create the directory first if it is empty. Otherwise Docker may create it as root-only.

Inspect or wipe the named volume:

```bash
docker volume inspect meshchatx-config
docker rm -f reticulum-meshchatx
docker volume rm meshchatx-config
```

The last two commands destroy persisted data.

## Install from release artifacts

### Linux AppImage (x64/arm64)

Download `ReticulumMeshChatX-v<version>-linux-<arch>.AppImage` from releases, then:

```bash
chmod +x ./ReticulumMeshChatX-v*-linux-*.AppImage
./ReticulumMeshChatX-v*-linux-*.AppImage
```

### Debian/Ubuntu

Download the matching `.deb`, then:

```bash
sudo apt install ./ReticulumMeshChatX-v*-linux-*.deb
```

### RPM

Download the `.rpm` if the release has one, then:

```bash
sudo rpm -Uvh ./ReticulumMeshChatX-v*-linux-*.rpm
```

### Python wheel

Release wheels include the built web assets.

```bash
pip install ./reticulum_meshchatx-*-py3-none-any.whl
meshchatx --headless
```

pipx works too:

```bash
pipx install ./reticulum_meshchatx-*-py3-none-any.whl
```

## Run from source (web server)

```bash
git clone https://github.com/Quad4-Software/MeshChatX.git
cd MeshChatX
corepack enable
pnpm config set verify-store-integrity true
pnpm install --frozen-lockfile
pip install "uv==0.11.15"
uv lock --check
uv sync --group dev
pnpm run build-frontend
uv run python -m meshchatx.meshchat --headless --host 127.0.0.1
```

`pnpm install --frozen-lockfile` fails if pnpm-lock.yaml does not match package.json, so an unexpected upstream version cannot land silently. Store integrity is also on in pnpm-workspace.yaml. The extra `pnpm config set` line hardens the user-level config too.

pnpm v11+ blocks lifecycle scripts by default. Only packages listed under allowBuilds in pnpm-workspace.yaml may run install scripts (electron, electron-winstaller, esbuild). `uv lock --check` fails if uv.lock is out of date with pyproject.toml. `uv sync` then installs from the lockfile only. Pin UV with `pip install "uv==0.11.15"` to match CI.

To update dependencies on purpose, run `pnpm update` or `uv lock` in its own commit and read the lockfile diff before you push.

## Linux sandbox

Firejail or Bubblewrap (bwrap) can isolate the native meshchatx binary (alias: meshchat) while leaving network access for Reticulum and the web UI. Examples, pip/pipx, Poetry, and USB serial notes: [linux-sandbox.md](docs/en/platform-guides/linux-sandbox.md).

That page also shows up in the in-app Documentation list when meshchatx-docs is bundled or synced.

## Linux desktop emoji fonts

The emoji picker uses system fonts through Electron/Chromium. Empty squares mean a color emoji package is missing. Install one and restart the app.

| Distro               | Package                                   |
| -------------------- | ----------------------------------------- |
| Arch, Artix, Manjaro | `sudo pacman -S noto-fonts-emoji`         |
| Debian, Ubuntu       | `sudo apt install fonts-noto-color-emoji` |
| Fedora               | google-noto-emoji-color-fonts             |

If glyphs still fail, run `fc-cache -fv` or wait until the next login. noto-fonts helps on minimal installs that lack other symbol coverage.

## Windows microphone (Electron, Windows 10 / 11)

Calls and voice attachments use the mic through Chromium. If the UI has no access or getUserMedia fails, check Windows privacy first. That is a common miss for Win32 apps, Electron included.

1. Win+R, paste `ms-settings:privacy-microphone`, Enter.
2. Turn Microphone access on.
3. Enable Let desktop apps access your microphone (wording varies by Windows version).
4. If a per-app list appears, make sure MeshChatX is not denied.

Also check Settings, System, Sound so the app is not muted and a working input device is selected.

## Offline builds

Two levels:

1. Cached: you already ran `make install` once, so node_modules, .venv, and local caches exist.
2. Air-gapped: the build machine has never had internet. Build a bundle on a networked machine and copy it over.

### Cached offline builds

Set `MESHCHATX_OFFLINE_BUILD=1` before any build command. That skips micron-parser-go WASM, the Reticulum manual, and repository wheel fetches, and runs package managers offline. Missing cache files fail the build instead of hanging.

```bash
MESHCHATX_OFFLINE_BUILD=1 make install
MESHCHATX_OFFLINE_BUILD=1 pnpm run build:offline
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux:offline
MESHCHATX_OFFLINE_BUILD=1 ./gradlew :app:assembleRelease
```

Cached mode only skips build-time network. The first `make install` still needs the network, or pre-populated pnpm and uv caches.

### Air-gapped builds

On the online machine:

```bash
pnpm run bundle:offline
bash scripts/create-offline-bundle.sh --warm-packaging
tar czf meshchatx-offline-linux-x64.tar.gz -C vendor/offline meshchatx-offline-bundle-*/
```

`--warm-packaging` is optional. It pre-downloads tools such as appimagetool.

On the air-gapped machine:

```bash
tar xzf meshchatx-offline-linux-x64.tar.gz
bash scripts/install-offline.sh
MESHCHATX_OFFLINE_BUILD=1 make build
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux
```

The bundle is platform-specific (Electron, esbuild, and other native binaries). Create it on the same OS and architecture as the air-gapped host. That host still needs node, pnpm, uv, and python3. The bundle is dependencies and caches, not the toolchain.

Android is separate. The offline bundle does not include Chaquopy wheels. Build those on an online machine with `bash scripts/build-android-wheels-local.sh`, copy android/vendor/ next to the project, then run Gradle with `MESHCHATX_OFFLINE_BUILD=1`.

## Desktop packages from source

```bash
pnpm run dist:linux-x64
pnpm run dist:linux-arm64
pnpm run dist:rpm
task dist:fe:rpm
```

Windows (x64 and arm64) and macOS (arm64 and universal) scripts are in package.json for local builds.

## Container build (wheel, AppImage, deb, rpm)

[Dockerfile.build](Dockerfile.build) runs the same shell steps CI uses (Poetry, pnpm, task, packaging APT deps). It is aimed at linux/amd64 (NodeSource amd64 tarball, Task amd64 binary).

`MESHCHATX_BUILD_TARGETS` defaults to all. Other values: wheel, or electron (AppImage + deb for x64 and arm64, best-effort RPM, no wheel).

```bash
docker build -f Dockerfile.build -t meshchatx-build:local .
docker build -f Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

Copy artifacts off the image:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Android

Native APK builds, not only Termux. From the repo root:

```bash
bash scripts/build-android-wheels-local.sh
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

Offline:

```bash
MESHCHATX_OFFLINE_BUILD=1 ./gradlew --no-daemon :app:assembleRelease
```

That skips the repository wheels fetch. android/vendor/ wheels and meshchatx/public/repository-server-bundled/bundled/ must already be present.

There is one Android variant. Gradle syncs the full meshchatx/ tree into app/src/main/python/meshchatx/, including the offline repository wheel bundle. Published builds are universal: one debug APK and one release APK per run, with the native ABIs from android/app/build.gradle.

- Debug: android/app/build/outputs/apk/debug/app-debug.apk
- Release: android/app/build/outputs/apk/release/app-release-unsigned.apk

Release APKs are unsigned unless you configure signing (scripts/sign-android-apks.sh). Native ABIs follow android/app/build.gradle, including armeabi-v7a when that ABI is enabled. Building those wheels needs an Android SDK on ANDROID_HOME.

If dist/reticulum_meshchatx-*.whl exists (for example from `python -m build --wheel -o dist .`), bundled repository refresh prefers that wheel over PyPI. CI builds that wheel before the Android Gradle step.

More: [android-termux.md](docs/en/platform-guides/android-termux.md), [android/README.md](android/README.md).

## Configuration

CLI args and matching env vars:

| Argument                   | Environment variable                     | Default      | Description                                                                                                            |
| -------------------------- | ---------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------- |
| `--host`                   | `MESHCHAT_HOST`                          | `127.0.0.1`  | Web server bind address                                                                                                |
| `--port`                   | `MESHCHAT_PORT`                          | `8000`       | Web server port                                                                                                        |
| `--no-https`               | `MESHCHAT_NO_HTTPS`                      | `false`      | Disable HTTPS                                                                                                          |
| `--ssl-cert` / `--ssl-key` | `MESHCHAT_SSL_CERT` / `MESHCHAT_SSL_KEY` | (none)       | PEM cert and key. Both must be set. Overrides auto-generated certs under the identity ssl/ directory.                  |
| `--rns-log-level`          | `MESHCHAT_RNS_LOG_LEVEL`                 | (none)       | RNS log level: none, critical, error, warning, notice, verbose, debug, extreme, or a number. CLI wins if both are set. |
| `--headless`               | `MESHCHAT_HEADLESS`                      | `false`      | Do not auto-launch a browser                                                                                           |
| `--auth`                   | `MESHCHAT_AUTH`                          | `false`      | Enable basic auth                                                                                                      |
| `--reset-password`         | `MESHCHAT_RESET_PASSWORD`                | `false`      | Clear the stored password hash so a new one can be set in the UI                                                       |
| `--storage-dir`            | `MESHCHAT_STORAGE_DIR`                   | `./storage`  | Data directory                                                                                                         |
| `--public-dir`             | `MESHCHAT_PUBLIC_DIR`                    | auto/bundled | Frontend files. Needed for source installs without bundled assets.                                                     |

## Branches

| Branch | Purpose                                            |
| ------ | -------------------------------------------------- |
| master | Stable releases                                    |
| dev    | Active development. May be incomplete or breaking. |

## Development

```bash
task install
task format
task lint
task test
task build
```

Makefile targets call the same Taskfile commands:

| Command              | Delegates to | Description                               |
| -------------------- | ------------ | ----------------------------------------- |
| make install         | task install | Install pnpm and UV dependencies          |
| make run             | task run     | Run MeshChatX via UV                      |
| make build           | task build   | Build frontend and backend artifacts      |
| make format          | task format  | Format frontend and backend               |
| make lint            | task lint    | ESLint, vue-tsc, knip, Ruff, basedpyright |
| make test            | task test    | Frontend and backend tests                |
| make clean           | task clean   | Remove build artifacts and node_modules   |
| make tree-rsm-verify | (shell)      | Verify meshchatx.rsm signature and hashes |
| make tree-rsm-sign   | (shell)      | Sign tree inventory (needs RNS_ID_PATH)   |
| make hooks-install   | (shell)      | Enable tracked pre-commit RSM resign hook |

## Versioning

Current version is 4.8.4.

Edit the version field in package.json, then run `pnpm run version:sync` (also the first step of `pnpm run build`). That copies the number into pyproject.toml, the Python version modules, Android Gradle, electron/app-version.json, this README and the translated READMEs, the Raspberry Pi pipx example, Arch PKGBUILD helpers, third-party notices, and GitHub issue-template placeholders.

Changelog entries are still written by hand when you cut a release. meshchatx.**version** is read from meshchatx/src/version.py without importing meshchatx.src, so `import meshchatx` stays lightweight.

## Database corruption and data reset

If MeshChatX fails to start with errors such as `database disk image is malformed`, DatabaseError, or corrupted ratchet data, the desktop crash screen offers:

- Restore latest backup from database-backups/ or snapshots/ inside the MeshChatX storage folder
- Choose backup file for a zip you saved elsewhere
- Try auto-repair (`--auto-recover`: SQLite checkpoint / integrity pass)
- Emergency mode, which opens the app without the database so you can export from About when possible
- Copy reset instructions with the folders to delete for a clean reinstall

### Storage locations

| Platform         | MeshChatX storage                              | Reticulum network stack              |
| ---------------- | ---------------------------------------------- | ------------------------------------ |
| Linux / macOS    | `~/.reticulum-meshchatx/`                      | `~/.reticulum/`                      |
| Windows          | `%USERPROFILE%\.reticulum-meshchatx\`          | `%USERPROFILE%\.reticulum\`          |
| Windows portable | `<MeshChatX.exe folder>\.reticulum-meshchatx\` | `<MeshChatX.exe folder>\.reticulum\` |

Legacy Reticulum MeshChat data may still exist at `~/.reticulum-meshchat/` (or the Windows equivalent). Automatic database backups go to database-backups/ inside the MeshChatX storage folder after a successful run.

### Complete removal

Quit MeshChatX. On Windows, also end ReticulumMeshChatX.exe in Task Manager if it is still running. Then delete the MeshChatX storage folder and the Reticulum config folder for your install type. That removes the local identity, messages, contacts, path cache, and ratchet state. The next launch creates a new identity unless you restore a backup first.

Linux / macOS:

```bash
rm -rf ~/.reticulum-meshchatx ~/.reticulum ~/.reticulum-meshchat
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.reticulum-meshchatx", "$env:USERPROFILE\.reticulum", "$env:USERPROFILE\.reticulum-meshchat" -ErrorAction SilentlyContinue
```

If you pass `--storage-dir` or `--reticulum-config-dir`, delete those directories instead.

### Command-line restore

When the backend can start briefly, or you run from source:

```bash
meshchatx --storage-dir /path/to/storage --restore-db /path/to/backup.zip
```

## Security

- [SECURITY.md](SECURITY.md)
- [LEGAL.md](LEGAL.md)
- Built-in integrity checks and HTTPS/WSS defaults at runtime
- CI and release builds on GitHub Actions

## Adding a language

My workflow: ArgosTranslate, then a local LLM (Qwen 3 + Gemma 4).

People are welcome to send fixes via LXMF (`f489752fbef161c64d65e385a4e9fc74`) or however you can reach me.

Locale discovery is automatic. Add a file under meshchatx/src/frontend/locales/ (for example xx.json) with the same keys as en.json and a top-level `_languageName` string for the selector label. Copy en.json and translate the values. Machine-assisted generation is optional.

For a machine-generated first draft from en.json, use scripts/argos_translate.py. It keeps interpolation variables such as `{count}` intact.

```bash
pipx install argostranslate
python scripts/argos_translate.py --from en --to xx --input meshchatx/src/frontend/locales/en.json --output meshchatx/src/frontend/locales/xx.json --name "Your Language Name"
```

After a machine pass, have an LLM or a human check grammar, context, and tone.

```bash
pnpm test -- tests/frontend/i18n.test.js --run
```

That checks key parity with en.json. No other code changes. The app, language selector, and tests pick up locales from meshchatx/src/frontend/locales/ at build time.

## Donation

Donations are voluntary. They help fund time spent on this app.

Ways to give: [donate.md](donate.md) (Monero, Ko-Fi, Buy Me a Coffee).

## Credits

- [Liam Cottle](https://github.com/liamcottle) - original Reticulum MeshChat
- [RFnexus](https://github.com/RFnexus) - micron parser JavaScript work
- [markqvist](https://github.com/markqvist) - Reticulum, LXMF, LXST

## License

Project-owned portions are 0BSD. Original upstream portions from Reticulum MeshChat remain MIT. Full text: [LICENSE](LICENSE).
