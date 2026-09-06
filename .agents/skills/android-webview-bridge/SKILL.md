---
name: android-webview-bridge
description: Android WebView chooser MIME mapping, storage paths, Chaquopy boot, and external navigation. Use when changing MainActivity bridges, file pickers, Android Python packaging, or WebView origin allowlists.
---

# Skill: android-webview-bridge

Keep Chaquopy backend boot, WebView file choosers, storage locks, and external navigation correct on Android.

## When to use

- Changing MainActivity bridges, file pickers, or storage setup
- Touching Android Python wrapper / Chaquopy packaging
- Identity or database restore pickers on Android
- Debugging empty file pickers or "fresh install" after storage location change
- Changing WebView navigation allowlists or the MeshChatXAndroid JS bridge

## File chooser

- Extension tokens like .identity are **not** valid MIME types for Intent.EXTRA_MIME_TYPES.
- Map .ext accepts to application/octet-stream and/or _/_.
- Set EXTRA_ALLOW_MULTIPLE only when the WebView chooser mode is multi-select.

## Storage and lock

- Internal vs external app storage can look like a fresh install if the user picks a different location than previous data.
- fcntl.flock may be missing. StorageLock falls back to a PID soft lock.
- Stale .meshchatx.lock may need clearing in the Chaquopy wrapper path.

## Navigation and packaging

- External http(s) links open in the system browser. Do not navigate the WebView away from the app.
- isAllowedWebViewNavigationUri must call RemoteBackendUrl.isAllowedShellNavigation. Allow the configured backend origin, about:blank, and blobs whose inner origin matches the backend.
- Deny data:, javascript:, file:, and userinfo URLs. The MeshChatXAndroid JS bridge is injected into every page the WebView loads.
- Keep setAllowFileAccess(false), setAllowFileAccessFromFileURLs(false), setAllowUniversalAccessFromFileURLs(false), and MIXED_CONTENT_NEVER_ALLOW. File pickers use Intents, not WebView file: URLs.
- Any loopback host on any port is not an allowlist. Remote-backend mode must not still permit 127.0.0.1:<other-port>.
- Parse with java.net.URI. Reject getUserInfo(). Do not prefix-match http://127.0.0.1.
- Vendored lxmfy and rns_filesync are synced into Chaquopy src/main/python/. Android pip does not install them like desktop setuptools.
- RNS panic containment matters on Android (see deferred-network-startup).

## RNode on Android

- Chaquopy has no pyjnius. Ship android/app/src/main/python/jnius/ as a shim over java.jclass.
- Override usb4a under android/app/src/main/python/usb4a/ and inject the Activity via meshchat_wrapper.start_server(..., activity).
- BLE uses bundled able plus org.able.BLE (not Kivy PythonActivity).
- RNode flasher is native RNodeFlasherActivity (USB via UsbSerialHub, ESP32 ROM flash in Java). WebView only launches it via openRNodeFlasher().
- Codec2 requires System.loadLibrary("codec2") before Python import (see MeshChatApplication).
- Keep RNS panic containment and panic_on_interface_error = No.

## Key files

- android/app/src/main/java/com/meshchatx/MainActivity.java
- android/app/src/main/java/com/meshchatx/RemoteBackendUrl.java
- android/app/src/test/java/com/meshchatx/RemoteBackendUrlTest.java
- android/app/src/main/java/com/meshchatx/rnode/RNodeFlasherActivity.java
- android/app/src/main/java/com/meshchatx/rnode/UsbSerialHub.java
- android/app/src/main/java/com/meshchatx/rnode/Esp32SerialFlasher.java
- android/app/src/main/java/com/meshchatx/MeshChatApplication.java
- android/app/src/main/java/org/able/BLE.java
- android/app/src/main/python/meshchat_wrapper.py
- android/app/src/main/python/jnius/
- android/app/src/main/python/usb4a/
- android/app/src/main/python/able/
- meshchatx/android_codec2.py
- meshchatx/src/backend/android_rnode/
- meshchatx/src/frontend/js/rnode/AndroidBridge.js
- .agents/conventions/android.md

## Verification

- Unit / bridge-focused tests if present for the change (RemoteBackendUrlTest for navigation allowlists).
- Emulator smoke when file chooser, storage, or boot paths change (CI workflow when available).
- For identity picker changes, also follow identity-restore.
- URL origin allowlists: .agents/skills/url-origin-allowlists/SKILL.md.
