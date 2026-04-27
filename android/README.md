# MeshChatX Android (Chaquopy)

Native APK with embedded Python (`meshchatx/`) and a WebView UI.

## Prerequisites

- Android SDK (`ANDROID_HOME` / `ANDROID_SDK_ROOT`) with `cmdline-tools` and a matching **NDK** (see `android/app/build.gradle` for the pinned NDK version used in CI).
- **JDK 17** (Temurin or compatible).
- Chaquopy vendor wheels under `android/vendor/` (build locally with `bash scripts/build-android-wheels-local.sh` from repo root, or use CI artifacts).

## Lint and static analysis

- **Android Lint** (Java, Kotlin, manifests, resources): from `android/`, run `./gradlew --no-daemon :app:lintDebug`. HTML report: `app/build/reports/lint-results-debug.html`. CI runs this in the Android workflow when tests run.
- **SAST (GitHub CodeQL)**: the repository workflow includes a `java-kotlin` matrix entry (see `.github/workflows/codeql.yml`) for GitHub’s security analysis on default branches and PRs.

## Launcher shortcuts, language

- **App shortcuts** (long-press the launcher icon): open **Messages** (`meshchatx://app/messages`) and **Call** (`meshchatx://app/call`). The WebView handles these in `App.vue` via `handleProtocolLink`.
- **Per-app language (Android 13+)**: `android:localeConfig` points to `res/xml/locales_config.xml`. Add translated `values-xx/strings.xml` for Android notification/shortcut strings; the in-app language still comes from MeshChatX server config.

## Build

From repo root:

```bash
bash scripts/build-android-wheels-local.sh
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

There is a **single** application variant (no product flavors). Gradle syncs the **entire** `meshchatx/` tree into `app/src/main/python/meshchatx/` (including `public/repository-server-bundled` for the in-app repository server). The `fetchRepositoryBundledWheels` task runs before sync when bundled wheels are missing; if repo root `dist/reticulum_meshchatx-*.whl` exists (e.g. from `python -m build --wheel -o dist .`), that wheel is preferred over PyPI for the bundled set.

### Native ABIs (universal APK)

Release and debug artifacts are **universal APKs** only: one APK per build type, embedding the native libraries for each ABI selected at build time.

- **`-PmeshchatxAbis=...`** or **`MESHCHATX_ABIS`**: comma-separated list from `arm64-v8a`, `x86_64`, `armeabi-v7a` (default: all three). This controls which `.so` variants are merged into the single universal APK, not separate per-ABI store listings.

### Outputs

Each build produces:

- Debug: `app/build/outputs/apk/debug/app-debug.apk`
- Release (unsigned until you sign): `app/build/outputs/apk/release/app-release-unsigned.apk`

### Signing release APKs

See repo root `scripts/sign-android-apks.sh` (default glob targets `outputs/apk/release/`).

## Troubleshooting

1. Confirm `android/vendor/` contains required `.whl` files from the wheel build script.
2. Run `./gradlew :app:assembleDebug` with `--stacktrace` if Python sync or Chaquopy pip steps fail.
3. Re-run `./gradlew :app:assembleDebug` after changing `meshchatx/` assets; sync runs on merge Python sources tasks.

See [`../LICENSE`](../LICENSE) for full text and notices.
