# MeshChatX Android App

This directory contains the Android app build configuration using Chaquopy to embed the Python MeshChatX server.

## Architecture

The app uses a **WebView** to display the existing Vue.js frontend. The Python server runs in the background via Chaquopy and serves the web interface on `https://127.0.0.1:8000`.

## Build debug APK

Prerequisites:

- **JDK 17 or newer** (required by the Android Gradle Plugin used in this project). On distributions with multiple JDKs, point the build at JDK 17+ (for example `JAVA_HOME` for the Gradle invocation).
- **Android SDK** with API **34** platform and **Build-Tools 34** installed. Set `ANDROID_HOME` and `ANDROID_SDK_ROOT` to the SDK root (the same directory for both is fine).
- **`android/vendor/`** must contain the Chaquopy vendor wheels (see [Updating Android Python ABI Wheels](#updating-android-python-abi-wheels-python-311)). The build fails fast if this directory is missing or incomplete.
- **MeshChatX Python sources** at the repository root (`meshchatx/`). The build syncs them into the app before compiling.

SDK licenses:

- Use **Command-line Tools** `sdkmanager`, not the legacy `tools/bin/sdkmanager` from old SDK layouts. The legacy tool loads JAXB classes that were removed from the JDK in Java 11, so running it on JDK 17+ fails with `NoClassDefFoundError: javax/xml/bind/annotation/XmlSchema`.
- Install Command-line Tools if needed: download the package for your OS from [Android Studio command-line tools](https://developer.android.com/studio#command-tools), extract it so you have `cmdline-tools/latest/bin/sdkmanager` under `ANDROID_HOME` (the inner folder is often named `latest`; see Google’s layout for that zip).
- Accept licenses (writes under the SDK; use sudo if the SDK is root-owned):

```text
yes | path/to/cmdline-tools/latest/bin/sdkmanager --licenses
```

- Install missing packages if the build still complains (platform 34, build-tools 34, etc.):

```text
path/to/cmdline-tools/latest/bin/sdkmanager "platforms;android-34" "build-tools;34.0.0"
```

Build from the `android/` directory:

```text
./gradlew assembleDebug
```

Debug APK outputs (ABI splits plus universal) are written under `app/build/outputs/apk/debug/`, for example:

- `app-arm64-v8a-debug.apk`
- `app-x86_64-debug.apk`
- `app-universal-debug.apk`

## Updating Android Python ABI Wheels (Python 3.11)

Use this workflow when a dependency (for example `cryptography`) requires custom Android wheels for `arm64-v8a` and `x86_64`.

1. Build wheels in a Podman Python 3.11 container to avoid host Python mismatches:
   - Use `docker.io/library/python:3.11-bookworm`.
   - Mount project root to `/work` and Android SDK to `/opt/android-sdk`.
   - Export `ANDROID_HOME` and `ANDROID_SDK_ROOT` to `/opt/android-sdk`.
   - Example container entry:
     `podman run --rm --network host -e ANDROID_HOME=/opt/android-sdk -e ANDROID_SDK_ROOT=/opt/android-sdk -v "/opt/android-sdk:/opt/android-sdk" -v "<repo>:/work" -w /work docker.io/library/python:3.11-bookworm bash`
2. Keep custom Chaquopy recipes in `android/chaquopy-recipes/<package>-<major>/`:
   - Define package/version in `meta.yaml`.
   - Store source patches in `patches/`.
3. Build both ABIs with Chaquopy `build-wheel.py` and place final wheels in `android/vendor/`.
4. Update `android/app/build.gradle` `pip` installs to the new pinned version.
5. Rebuild with `./gradlew assembleDebug` and verify split outputs:
   - `app-arm64-v8a-debug.apk`
   - `app-x86_64-debug.apk`
   - `app-universal-debug.apk`

Notes:
- For Rust-backed wheels (such as modern `cryptography`), build inside the container with Rust toolchain available.
- Keep recipe files and patches versioned; keep generated build artifacts untracked.

## Custom Recipes and Patches

This project keeps Android-specific Chaquopy recipes in `android/chaquopy-recipes/` to bridge gaps between desktop Python dependencies and Android wheel availability.

- `cryptography-46`
  - Purpose: provide Android ABI wheels for `cryptography 46.0.7` (`arm64-v8a`, `x86_64`) because upstream Chaquopy index only provided older builds.
  - `patches/openssl_no_legacy.patch`: disables OpenSSL legacy provider loading, which is unavailable in the bundled Android OpenSSL runtime.
  - `patches/pyo3_no_interpreter.patch`: enables compatible `pyo3` ABI settings for Chaquopy Python 3.11 Android builds.

- `aiohttp-3.13`
  - Purpose: align Android with desktop dependency line (`aiohttp 3.13.3`) by building fresh ABI wheels with Chaquopy.
  - No source patch is required; recipe pins the newer upstream version for Android wheel generation.

- `psutil-7.2`
  - Purpose: align Android with desktop dependency line (`psutil 7.2.2`) while preserving Android runtime behavior.
  - `patches/chaquopy.patch`: treats `android` platform as Linux in psutil internals and forces a safe partition enumeration path because `/proc/filesystems` can be restricted by SELinux on some Android API levels.

- `bcrypt-5`
  - Purpose: tracks attempted upgrade path to desktop-equivalent bcrypt.
  - Status: currently not enabled in Android app dependencies; `bcrypt==3.1.7` remains pinned for stable APK builds.

## License

This directory is part of the main project licensing split:
- project-owned portions: 0BSD
- original upstream MeshChat portions: MIT

See [`../LICENSE`](../LICENSE) for full text and notices.