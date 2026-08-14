# Android conventions

Applies when editing `android/**/*.{java,kt}`.

- WebView `accept` extension tokens are not valid MIME types. Map `.ext` to `application/octet-stream` / `*/*` before `EXTRA_MIME_TYPES`.
- Set `EXTRA_ALLOW_MULTIPLE` only when the chooser mode is multi-open.
- Prefer existing bridge patterns in `MainActivity` for storage, file pick, and push.
- After Android bridge changes, note whether emulator smoke or unit coverage is needed.
- WebView navigation uses `RemoteBackendUrl.isAllowedShellNavigation` (backend origin only). Deny `data:` and userinfo. The JS bridge follows every loaded page. See `.agents/skills/url-origin-allowlists/SKILL.md`.
