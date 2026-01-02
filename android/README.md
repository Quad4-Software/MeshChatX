# MeshChatX Android App

This directory contains the Android app build configuration using Chaquopy to embed the Python MeshChatX server.

## Architecture

The app uses a **WebView** to display the existing Vue.js frontend. The Python server runs in the background via Chaquopy and serves the web interface on `http://127.0.0.1:8000`.

**No Kotlin frontend needed** - we reuse the entire existing Vue.js web frontend!

## Prerequisites

- Android Studio (latest version)
- Android SDK with API level 24+ (Android 7.0+)
- Chaquopy license (free for open source projects, see https://chaquo.com/chaquopy/pricing/)

## Setup

1. **Initialize Gradle Wrapper** (if not already done):

    ```bash
    task android-init
    ```

    Or manually:

    ```bash
    cd android
    gradle wrapper --gradle-version 8.2
    ```

2. **Get Chaquopy License**:
    - Sign up at https://chaquo.com/chaquopy/
    - Add your license key to `android/local.properties`:
        ```
        chaquopy.license=your-license-key-here
        ```

3. **Prepare Build**:
    ```bash
    task android-prepare
    ```
    This will:
    - Build the frontend
    - Copy the `meshchatx` package to `app/src/main/python/`
    - Initialize Gradle wrapper if needed

## Building

### Using Task (Recommended)

```bash
# Build debug APK
task android-build

# Build release APK (requires signing config)
task android-build-release
```

### Using Gradle Directly

```bash
cd android
./gradlew assembleDebug
```

Or open the `android` directory in Android Studio and build from there.

## Configuration

The server is configured to:

- Run on `127.0.0.1:8000` (localhost only)
- Use HTTPS for local WebView access
- Run in headless mode (no browser launch)

## Notes

- The app requires network permissions for RNS/mesh networking
- Storage permissions are needed for identity and message storage
- The Python server runs in a background thread
- The WebView loads the Vue.js frontend after a 2-second delay to allow server startup

## Troubleshooting

- If the WebView shows a blank page, check logcat for Python errors
- Ensure all Python dependencies are listed in `app/build.gradle` chaquopy.pip block
- Some native dependencies (like RNS) may need additional configuration
