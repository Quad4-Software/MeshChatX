# Building from source and packaging

How to build MeshChatX offline, package desktop artifacts, and produce Android APKs. For day-to-day install and CLI flags, see **Installation and setup**.

Tagged releases build Linux wheel/AppImage/deb/rpm, Windows, macOS, Flatpak, and Android APKs (when the tag is on dev or master) in [build-release.yml](../../.github/workflows/build-release.yml). The container image is [docker.yml](../../.github/workflows/docker.yml). Manual Android builds run via [android-build.yml](../../.github/workflows/android-build.yml) (workflow_dispatch). Linux x64 and arm64 AppImage and DEB are built on GitHub. RPM is uploaded when the job produces one.

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

The bundle is platform-specific (esbuild, Go/Wails, and other native binaries). Create it on the same OS and architecture as the air-gapped host. That host still needs node, pnpm, uv, and python3. The bundle is dependencies and caches, not the toolchain.

Android is separate. The offline bundle does not include Chaquopy wheels. Build those on an online machine with bash scripts/build-android-wheels-local.sh, copy android/vendor/ next to the project, then run Gradle with MESHCHATX_OFFLINE_BUILD=1.

## Desktop packages from source

```bash
pnpm run dist:linux-x64
pnpm run dist:linux-arm64
pnpm run dist:rpm
task dist:linux:deb
```

Windows (x64 and arm64, NSIS + portable zip) and macOS (arm64 and universal .app/dmg) scripts are in package.json for local builds. The desktop shell is built with Wails v3 (`cd desktop && wails3 build`); packaging tasks live in `desktop/build/` (nfpm for deb/rpm, linuxdeploy for AppImage, makensis for Windows, hdiutil for macOS).

### AppImage details

`task linux:create:appimage` (or `pnpm run dist:linux`) builds `desktop/bin/ReticulumMeshChatX-v<version>-linux-<arch>.AppImage` via `desktop/build/linux/appimage/build.sh`. The script downloads linuxdeploy, its GTK4 and GStreamer plugins, appimagetool and patchelf into `desktop/bin/appimage-work/cache`, verifies each against the sha256 pins in `tools.tsv` (re-download and update the pins deliberately; `ALLOW_UNPINNED_TOOLS=1` bypasses only for local experiments), and keeps all scratch under `desktop/bin/appimage-work` — never `/tmp`.

The bundle ships GTK 4, WebKitGTK 6.0 (helpers included), GStreamer plugins, the `.desktop` entry with `lxmf`/`rns` scheme handlers, and the backend under `usr/lib/reticulum-meshchatx/backend/`. `excludelist.txt` keeps glibc, the dynamic loader, GPU drivers and the X11 stack on the host, so the result needs a host glibc at least as new as the build machine's. WebKitGTK 6.0 ignores `WEBKIT_EXEC_PATH`, so `patch-webkitgtk.py` rewrites the helpers' compiled-in `/usr/lib/webkitgtk-6.0` paths to AppDir-relative ones and `AppRun` `cd`s into `$APPDIR` before exec — keep that invariant if you touch either file.

`BACKEND_DIR` selects the bundled backend (default `desktop/bin/backend`); `ARCH=amd64|arm64` selects the tool downloads. The aarch64 path is parameterized but untested. `scripts/ci/test-appimage.sh <AppImage>` smoke-tests a stub-backend build (needs a display; use `xvfb-run` headless).

GStreamer plugins are copied from the build host, so install `gst-plugins-base`, `gst-plugins-good`, `gst-plugins-bad`, `gst-plugins-ugly` and `gst-libav` (names vary by distro) before building or the AppImage's embedded browser cannot play audio or decode most media — `build.sh` warns when coverage is missing but still produces the package.

## Container build (wheel, AppImage, deb, rpm)

[Dockerfile.build](../../docker/Dockerfile.build) runs the same shell steps CI uses (Poetry, pnpm, task, packaging APT deps). It is aimed at linux/amd64 (NodeSource amd64 tarball, Task amd64 binary).

MESHCHATX_BUILD_TARGETS defaults to all. Other values: wheel, or desktop (AppImage + deb + rpm for x64 and arm64, no wheel). The desktop target installs Go, GTK4, WebKitGTK 6.0, and libsoup3 development packages.

```bash
docker build -f docker/Dockerfile.build -t meshchatx-build:local .
docker build -f docker/Dockerfile.build --build-arg MESHCHATX_BUILD_TARGETS=wheel -t meshchatx-build:wheel .
```

Copy artifacts off the image:

```bash
cid=$(docker create meshchatx-build:local)
docker cp "${cid}:/artifacts" ./meshchatx-artifacts
docker rm "${cid}"
```

## Container Windows build (optional, Wine)

The Wails desktop **shell cross-compiles from Linux without Wine**: `pnpm run desktop:cross-check` (or `scripts/ci/check-desktop-cross-build.sh`) builds windows/amd64, windows/arm64, darwin/arm64 and darwin/amd64 with `CGO_ENABLED=0` and verifies the PE/Mach-O outputs; `task windows:build` / `task darwin:build:cross` produce the same binaries (darwin uses `-tags purego`). Windows `.syso` resources (icon + manifest) are generated by `wails3 generate syso` inside the Windows build task and removed afterwards.

The **frozen Python backend cannot be cross-built from Linux** — cx_Freeze must run on (or for) each target OS: use a native runner, or Wine/docker only for that step (`PLATFORM=win32 PYTHON_CMD='wine C:/Python315/python.exe' pnpm run build-backend`). Packaging tasks take the backend dir as input (`BACKEND_DIR=build/exe/<platform>-<arch>`) and fail with a clear message when it is missing. macOS bundling is cross-platform as a directory tree + Info.plist + icns; codesign/notarize/dmg remain macOS-only. Windows NSIS packaging needs `makensis` (available on Linux via the `nsis` package).

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
