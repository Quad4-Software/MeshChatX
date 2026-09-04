# Building from source and packaging

How to build MeshChatX offline, package desktop artifacts, and produce Android APKs. For day-to-day install and CLI flags, see **Installation and setup**.

Tagged releases build Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, and Android APKs (when the tag is on dev or master) in [build-release.yml](../../.github/workflows/build-release.yml). Flatpak OSTree is published to `https://cdn.meshchatx.com/flatpak/` in that workflow. The container image is [docker.yml](../../.github/workflows/docker.yml). Branch and PR Android CI is [android-build.yml](../../.github/workflows/android-build.yml). Linux x64 and arm64 AppImage and DEB are built on GitHub. RPM is uploaded when the job produces one.

## Offline builds

Two levels:

1. Cached: you already ran make install once, so node_modules, .venv, and local caches exist.
2. Air-gapped: the build machine has never had internet. Build a bundle on a networked machine and copy it over.

### Cached offline builds

Set MESHCHATX_OFFLINE_BUILD=1 before any build command. That skips micron-parser-go WASM, the Reticulum manual, and repository wheel fetches, and runs package managers offline. Missing cache files fail the build instead of hanging.

```bash
MESHCHATX_OFFLINE_BUILD=1 make install
MESHCHATX_OFFLINE_BUILD=1 pnpm run build:offline
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux:offline
MESHCHATX_OFFLINE_BUILD=1 ./gradlew :app:assembleRelease
```

Cached mode only skips build-time network. The first make install still needs the network, or pre-populated pnpm and uv caches.

### Air-gapped builds

On the online machine:

```bash
pnpm run bundle:offline
bash scripts/create-offline-bundle.sh --warm-packaging
tar czf meshchatx-offline-linux-x64.tar.gz -C vendor/offline meshchatx-offline-bundle-*/
```

--warm-packaging is optional. It pre-downloads tools such as appimagetool.

On the air-gapped machine:

```bash
tar xzf meshchatx-offline-linux-x64.tar.gz
bash scripts/install-offline.sh
MESHCHATX_OFFLINE_BUILD=1 make build
MESHCHATX_OFFLINE_BUILD=1 pnpm run dist:linux
```

The bundle is platform-specific (Electron, esbuild, and other native binaries). Create it on the same OS and architecture as the air-gapped host. That host still needs node, pnpm, uv, and python3. The bundle is dependencies and caches, not the toolchain.

Android is separate. The offline bundle does not include Chaquopy wheels. Build those on an online machine with bash scripts/build-android-wheels-local.sh, copy android/vendor/ next to the project, then run Gradle with MESHCHATX_OFFLINE_BUILD=1.

## Desktop packages from source

```bash
pnpm run dist:linux-x64
pnpm run dist:linux-arm64
pnpm run dist:rpm
task dist:fe:rpm
```

Windows (x64 and arm64) and macOS (arm64 and universal) scripts are in package.json for local builds.

## Container build (wheel, AppImage, deb, rpm)

[Dockerfile.build](../../Dockerfile.build) runs the same shell steps CI uses (Poetry, pnpm, task, packaging APT deps). It is aimed at linux/amd64 (NodeSource amd64 tarball, Task amd64 binary).

MESHCHATX_BUILD_TARGETS defaults to all. Other values: wheel, or electron (AppImage + deb for x64 and arm64, best-effort RPM, no wheel).

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

## Container Windows build (optional, Wine)

Tagged releases still build Windows on GitHub windows-latest. For a local cross-build without that runner, use [Dockerfile.electron-wine](../../Dockerfile.electron-wine) on top of electronuserland/builder:24-wine. It installs embeddable Windows Python under Wine for cx_Freeze (same role as task setup:wine), downloads win_amd64 wheels on the Linux side (Wine HTTPS to PyPI is flaky), then runs electron-builder for portable and NSIS.

```bash
task docker:dist:win:smoke
task docker:dist:win
```

Or:

```bash
docker build -f Dockerfile.electron-wine -t meshchatx-electron-wine:local .
cid=$(docker create meshchatx-electron-wine:local)
docker cp "${cid}:/artifacts/." ./meshchatx-artifacts-win
docker rm "${cid}"
```

MESHCHATX_ELECTRON_WINE_TARGETS values: smoke (toolchain only), win (default), linux+win. Host helper: scripts/docker/electron-wine-build.sh.

This path can fail on packages that lack Windows wheels under Wine. Prefer a real Windows host or GH Actions when the Wine freeze misbehaves.

## Android APK

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
- Release: android/app/build/outputs/apk/release/ReticulumMeshChatX-v*-android-universal-unsigned.apk
- GitHub release: `ReticulumMeshChatX-v<version>-android-universal.apk`

Release APKs are unsigned unless you configure signing (scripts/sign-android-apks.sh). Native ABIs follow android/app/build.gradle, including armeabi-v7a when that ABI is enabled. Building those wheels needs an Android SDK on ANDROID_HOME.

If dist/reticulum_meshchatx-*.whl exists (for example from python -m build --wheel -o dist .), bundled repository refresh prefers that wheel over PyPI. CI builds that wheel before the Android Gradle step.

More: [android-termux.md](platform-guides/android-termux.md), [android/README.md](../../android/README.md), [quest-sidequest.md](platform-guides/quest-sidequest.md).

## See also

- **Installation and setup** for Docker, wheels, and CLI flags
- **Development** for task targets and version sync
- **Linux sandboxing** for Firejail and Bubblewrap around a built binary
