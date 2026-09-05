---
name: identity-switch-teardown
description: Live identity switch by tearing down IdentityContext and clearing caches. Use when adding managers that hold destinations, timers, or DB handles.
---

# Skill: identity-switch-teardown

Switch identities by tearing down the full `IdentityContext` and clearing frontend caches so routers and managers never leak cross-identity state.

## When to use

- Changing identity create / switch / delete / activate flows
- Adding managers that hold RNS destinations, bots, timers, or DB handles
- Caching peer lists, favourites, or conversation state in process globals or Vue stores

## Model

- One active `IdentityContext` at a time
- Per-identity data under `storage/identities/<hash>/`
- Shared Reticulum config under `~/.reticulum` (does **not** reset on switch)

## Hard rules

- Do not stash identity-specific state in process globals.
- Teardown must deregister RNS handlers, stop bots / RRC / RNSH / forwarding, close LXMRouter destinations, and shut down DB connections (`IdentityContext.teardown()`).
- After switch, prefer a controlled reload / clear of frontend caches over partial UI patches that leave stale WS subscriptions.
- Favourites layout, snapshots, SSL certs, and LXMF dirs are per-identity. Do not write them into shared storage roots.

## Related but different

Identity **key** import vs database **zip** restore is covered by `identity-restore`. This skill is about live switch / teardown correctness.

## Key files

- `meshchatx/src/backend/identity_context.py`
- `meshchatx/src/backend/identity_manager.py`
- `meshchatx/meshchat.py` (switch endpoints, `identity_switched` broadcast)
- `meshchatx/src/frontend/components/App.vue` (`identity_switched` handler)
- `meshchatx/src/frontend/features/settings/components/IdentitiesPage.svelte`

## Verification

```bash
uv run pytest tests/backend/test_identity_restore.py tests/backend/test_identity_restore_http_api.py -q --tb=short
pnpm exec vitest run tests/frontend/IdentitiesPage.test.js
```

When adding a new manager, add teardown coverage or assert it is stopped from `IdentityContext.teardown()`.
