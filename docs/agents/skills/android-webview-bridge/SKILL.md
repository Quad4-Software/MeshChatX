# Skill: android-webview-bridge

Keep Chaquopy backend boot, WebView file choosers, storage locks, and external navigation correct on Android.

## When to use

- Changing `MainActivity` bridges, file pickers, or storage setup
- Touching Android Python wrapper / Chaquopy packaging
- Identity or database restore pickers on Android
- Debugging empty file pickers or "fresh install" after storage location change

## File chooser

- Extension tokens like `.identity` are **not** valid MIME types for `Intent.EXTRA_MIME_TYPES`.
- Map `.ext` accepts to `application/octet-stream` and/or `*/*`.
- Set `EXTRA_ALLOW_MULTIPLE` only when the WebView chooser mode is multi-select.

## Storage and lock

- Internal vs external app storage can look like a fresh install if the user picks a different location than previous data.
- `fcntl.flock` may be missing. `StorageLock` falls back to a PID soft lock.
- Stale `.meshchatx.lock` may need clearing in the Chaquopy wrapper path.

## Navigation and packaging

- External http(s) links open in the system browser. Do not navigate the WebView away from the app.
- Vendored `lxmfy` is synced into Chaquopy `src/main/python/`. Android pip does not install it like desktop setuptools.
- RNS panic containment matters on Android (see `deferred-network-startup`).

## Key files

- `android/app/src/main/java/com/meshchatx/MainActivity.java`
- `android/app/src/main/python/meshchat_wrapper.py`
- `meshchatx/src/frontend/js/rnode/AndroidBridge.js`
- `docs/agents/conventions/android.md`

## Verification

- Unit / bridge-focused tests if present for the change.
- Emulator smoke when file chooser, storage, or boot paths change (CI workflow when available).
- For identity picker changes, also follow `identity-restore`.
