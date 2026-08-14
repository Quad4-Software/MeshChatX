---
name: url-origin-allowlists
description: Parse URL origins for shell and outbound allowlists. Never prefix-match http(s). Use when changing Electron navigation, Android WebView nav, preload IPC, ipcMain handlers, or HTTP URL guards.
---

# Skill: url-origin-allowlists

Decide allow/deny from a parsed URL (scheme, host, port, userinfo), never from a string prefix. A prefix such as `http://127.0.0.1:9337` matches `http://127.0.0.1:9337@example.com`, which WHATWG/Java parse as host example.com with userinfo `127.0.0.1:9337`.

## When to use

- Electron `will-navigate`, `will-redirect`, `window.open`, preload IPC, ipcMain sender URL
- Android WebView navigation or `JavascriptInterface` pages
- Outbound HTTP allowlists (`http_url_guard`, community directory, remote backend URL)
- Any new "is this our local backend?" helper

## Rules

1. Parse with `URL` / `java.net.URI` / `urllib.parse.urlparse`. On parse failure, deny.
2. Reject non-empty userinfo (`username`, `password`, or `@` in netloc).
3. Compare hostname and port after parse. Do not `startsWith("http://127.0.0.1")`.
4. `blob:` is not trusted by itself. Check the inner `blob:<origin>/<uuid>` origin.
5. Deny `data:` and `javascript:` in app shells. Those pages still receive Electron preload or Android `addJavascriptInterface`.
6. Electron: attach guards on `web-contents-created` (every WebContents, including popouts). Handle `will-navigate`, `will-redirect`, and `will-frame-navigate`. Deny `will-attach-webview`.
7. Electron preload: no-op IPC unless `isTrustedShellOrigin` (`file:` loading.html/crash.html, local backend `:9337`, trusted blobs).
8. Electron `ipcMain.handle`: reject unless `event.senderFrame.url` (fallback `sender.getURL()`) passes `isTrustedShellOrigin`. Preload checks are not enough.
9. Android WebView: allow only `matchesBackend(url, resolveBackendUrl())`, `about:blank`, and blobs whose inner origin matches the backend. Any loopback host/port is not enough. Keep `setAllowFileAccess(false)` and `MIXED_CONTENT_NEVER_ALLOW`.
10. Hostname RFC1918 checks must require a dotted-quad IPv4 (or a parsed hostname), not `host.startsWith("10.")`.
11. Plugin `network:fetch` scanning: parse the URL host. Do not treat a remote URL as local because the string contains `127.0.0.1` or `localhost`.

## Tests (oracle, not crash-only)

Assert deny for the userinfo-host form against the helper under test:

- `http://127.0.0.1:9337@example.com` (Electron local backend is port 9337)
- `http://127.0.0.1:8000@example.com` (Android local backend is port 8000)
- `data:text/html,...` in shell navigation
- `blob:https://example.com/uuid` in shell navigation

Do not write exploit pages or PoCs. The oracle is accept/reject on the parser.

## Key files

- `electron/shellOrigin.js`
- `electron/main.js` (`web-contents-created`, `trustedIpcHandle`)
- `electron/preload.js`
- `electron/safeExternalUrl.js`
- `android/app/src/main/java/com/meshchatx/RemoteBackendUrl.java`
- `meshchatx/src/frontend/js/remoteBackendUrl.js`
- `meshchatx/src/backend/http_url_guard.py`
- `meshchatx/src/backend/plugin_permissions.py` (`_is_external_http_url`)
- `tests/electron/mainHelpers.test.js`
- `android/app/src/test/java/com/meshchatx/RemoteBackendUrlTest.java`

## Related

- `.agents/skills/electron-frozen-packaging/SKILL.md`
- `.agents/skills/android-webview-bridge/SKILL.md`
- `.agents/skills/plugin-install-security/SKILL.md`
- `.agents/skills/test-oracles/SKILL.md`
