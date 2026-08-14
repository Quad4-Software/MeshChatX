---
name: privacy-mode-clearnet
description: Privacy mode blocks backend outbound HTTP/HTTPS and tightens CSP. It does not stop Reticulum mesh traffic. Use when adding clearnet fetches, translators, community lists, docs download, or CSP changes.
---

# Skill: privacy-mode-clearnet

`privacy_mode_enabled` is a config flag. When it is on, server-side HTTP/HTTPS from MeshChatX app features must fail closed. LXMF, LXST, RRC, announces, and other RNS traffic keep running.

## When to use

- Translator, GIF search, community interface lists, docs fetch, repository download, or any new `urllib`/`aiohttp`/`requests` call
- CSP or outbound-allow changes
- A feature that "just needs to hit GitHub/PyPI once"

## Mechanism

`meshchatx/src/backend/privacy_mode.py`:

- `privacy_mode_enabled(config)` reads `config.privacy_mode_enabled`
- `ensure_outbound_http_allowed(config, feature=...)` raises `OutboundHttpBlockedError` when the flag is on

Call `ensure_outbound_http_allowed` at the start of every backend path that would open a clearnet socket. Map `OutboundHttpBlockedError` to HTTP 403 or a structured `{ok: false}` the UI already handles. Do not swallow it and retry.

New `httpx` / `urllib` / `aiohttp.ClientSession` code under `meshchatx/src/backend/` must call `ensure_outbound_http_allowed` or `http_url_guard` (or `MeshChat._require_outbound_http`). Do not rewrite existing translator, map tile, firmware, community-directory, or repository fetches into one mega-guard. The RNS `HTTPInterface` is mesh transport, not app clearnet.

`tests/backend/test_outbound_http_allowlist.py` fails if a new backend file opens a clearnet client without being listed in `KNOWN_CLEARNET_FETCH_FILES`. Add the file to that set only after the privacy-mode or URL guard is wired.

Config key: `privacy_mode_enabled` in `config_manager.py`. Settings copy lives under `app.privacy_mode_*` locale keys.

## What privacy mode is not

- Not a mesh kill switch
- Not Landlock (filesystem sandbox). See `landlock-sqlite`.
- Not `--no-https` (local UI TLS)
- Not plugin `network:fetch` grants. Plugins still need declared permissions even when privacy mode is off. See `plugin-install-security`.

Optional clearnet helpers (docs fetch, community interface lists) stay behind this flag and explicit settings. Core messaging, identity, and pathfinding must work with privacy mode on.

## Tests

When you add a clearnet call, add a test that enables privacy mode and asserts the call is blocked (`OutboundHttpBlockedError` or the HTTP status the route already uses). Search existing tests for `privacy_mode` and match that pattern. Also run:

```bash
uv run pytest tests/backend/test_outbound_http_allowlist.py -q --tb=short
```
