# MeshChatX Android App

This directory contains the Android app build configuration using Chaquopy to embed the Python MeshChatX server.

## Architecture

The app uses a **WebView** to display the existing Vue.js frontend. The Python server runs in the background via Chaquopy and serves the web interface on `https://127.0.0.1:8000`.

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