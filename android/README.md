# MeshChatX Android (Chaquopy)

Native APK with embedded Python (`meshchatx/`) and a WebView UI.

## MeshChatX server (Docker)

The headless/web server is also published as a container (separate from this APK):

- **Docker Hub:** `quad4io/meshchatx`
- **GHCR:** `ghcr.io/quad4-software/meshchatx`

See the repository root [README](../README.md#quick-start-docker) for `docker compose` usage.

## Prerequisites

- Android SDK (`ANDROID_HOME` / `ANDROID_SDK_ROOT`) with `cmdline-tools` and a matching **NDK** (see `android/app/build.gradle` for the pinned NDK version used in CI).
- **JDK 17** (Temurin or compatible).
- Chaquopy vendor wheels under `android/vendor/` (build locally with `bash scripts/build-android-wheels-local.sh` from repo root, or use CI artifacts).

## Build

From repo root:

```bash
bash scripts/build-android-wheels-local.sh
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

There is a **single** application variant (no product flavors). Gradle syncs the **entire** `meshchatx/` tree into `app/src/main/python/meshchatx/` (including `public/repository-server-bundled` for the in-app repository server). The `fetchRepositoryBundledWheels` task runs before sync when bundled wheels are missing; if repo root `dist/reticulum_meshchatx-*.whl` exists (e.g. from `python -m build --wheel -o dist .`), that wheel is preferred over PyPI for the bundled set.

### ABI selection and packaging

- **`-PmeshchatxAbis=...`** or **`MESHCHATX_ABIS`**: comma-separated list from `arm64-v8a`, `x86_64`, `armeabi-v7a` (default: all three).
- **`-PmeshchatxAbiPackaging=universal|split`** or **`MESHCHATX_ABI_PACKAGING`**: `universal` (default) emits one APK per build type; `split` may emit per-ABI splits when more than one ABI is selected.

### Outputs

With default **universal** packaging:

- Debug: `app/build/outputs/apk/debug/app-debug.apk`
- Release (unsigned until you sign): `app/build/outputs/apk/release/app-release-unsigned.apk`

### Signing release APKs

See repo root `scripts/sign-android-apks.sh` (default glob targets `outputs/apk/release/`).

## Troubleshooting

1. Confirm `android/vendor/` contains required `.whl` files from the wheel build script.
2. Run `./gradlew :app:assembleDebug` with `--stacktrace` if Python sync or Chaquopy pip steps fail.
3. Re-run `./gradlew :app:assembleDebug` after changing `meshchatx/` assets; sync runs on merge Python sources tasks.

See [`../LICENSE`](../LICENSE) for full text and notices.
