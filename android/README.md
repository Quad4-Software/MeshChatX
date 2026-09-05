# MeshChatX Android (Chaquopy)

Native APK with embedded Python (meshchatx/) and a WebView UI.

## Prerequisites

- Android SDK (ANDROID_HOME / ANDROID_SDK_ROOT) with cmdline-tools and a matching **NDK** (see android/app/build.gradle for the pinned NDK version used in CI).
- **JDK 17** (Temurin or compatible).
- Chaquopy vendor wheels under android/vendor/ (build locally with bash scripts/build-android-wheels-local.sh from repo root, or use CI artifacts). That script builds native recipes under android/chaquopy-recipes/ and also vendors pure-Python wheels such as bleak and httpx[http2] (for bundled RNS-over-HTTP / HTTPInterface).

## Lint and static analysis

- **Android Lint** (Java, Kotlin, manifests, resources): from android/, run ./gradlew --no-daemon :app:lintDebug. HTML report: app/build/reports/lint-results-debug.html. CI runs this in the Android workflow when tests run.
- **SAST (GitHub CodeQL)**: the repository workflow includes a java-kotlin matrix entry (see .github/workflows/security.yml) for GitHub's security analysis on default branches and PRs.

## Launcher shortcuts, language

- **App shortcuts** (long-press the launcher icon): open **Messages** (meshchatx://app/messages) and **Call** (meshchatx://app/call). The WebView handles these in App.vue via handleProtocolLink. Message notification taps can open a specific conversation with meshchatx://app/messages/<destination_hash>.
- **Android Auto**: The APK declares the notification capability (`res/xml/automotive_app_desc.xml`). Inbound LXMF alerts use MessagingStyle with reply and mark-as-read actions handled by MessagingReplyService against the local (or configured remote) backend with CSRF. Password auth must already be signed in on the phone so the WebView session cookie is available. This is not a full car UI template app.
- **Per-app language (Android 13+)**: android:localeConfig points to res/xml/locales_config.xml. Add translated values-xx/strings.xml for Android notification/shortcut strings; the in-app language still comes from MeshChatX server config.

## Build

From repo root:

```bash
bash scripts/build-android-wheels-local.sh
cd android
./gradlew --no-daemon :app:assembleDebug :app:assembleRelease
```

There is a **single** application variant (no product flavors). Gradle syncs the **entire** meshchatx/ tree into app/src/main/python/meshchatx/ (including public/repository-server-bundled for the in-app repository server), and syncs vendored **vendor/lxmfy/lxmfy** into app/src/main/python/lxmfy/ (required for bots; not installed via Chaquopy pip) plus **vendor/rns_filesync/rns_filesync** into app/src/main/python/rns_filesync/ (required for FileSync). The fetchRepositoryBundledWheels task runs before sync when bundled wheels are missing; if repo root dist/reticulum_meshchatx-*.whl exists (e.g. from python -m build --wheel -o dist .), that wheel is preferred over PyPI for the bundled set.

### Native ABIs (universal APK)

Release and debug artifacts are **universal APKs** only: one APK per build type, embedding the native libraries for each ABI selected at build time.

- **-PmeshchatxAbis=...** or **MESHCHATX_ABIS**: comma-separated list from arm64-v8a, x86_64, armeabi-v7a (default: all three). This controls which .so variants are merged into the single universal APK, not separate per-ABI store listings.

### Outputs

Each build produces:

- Debug: app/build/outputs/apk/debug/app-debug.apk
- Release (unsigned until you sign): app/build/outputs/apk/release/ReticulumMeshChatX-v*-android-universal-unsigned.apk
- GitHub release asset (after signing): `ReticulumMeshChatX-v<version>-android-universal.apk`

### Signing release APKs

See repo root scripts/sign-android-apks.sh (default glob targets outputs/apk/release/).

## Troubleshooting

1. Confirm android/vendor/ contains required .whl files from the wheel build script.
2. Codec2 (voice messages, LXST Codec2 profiles): wheels must include pycodec2/libcodec2.so beside pycodec2.so. The wheel build script repacks automatically; for an existing android/vendor/ tree run python3 scripts/repack-android-pycodec2-wheels.py. Gradle also runs this before sync and copies `libcodec2.so` into jniLibs per ABI.
3. Run ./gradlew :app:assembleDebug with --stacktrace if Python sync or Chaquopy pip steps fail.
4. Re-run ./gradlew :app:assembleDebug after changing meshchatx/ assets; sync runs on merge Python sources tasks.

See [../LICENSE](../LICENSE) for full text and notices.
