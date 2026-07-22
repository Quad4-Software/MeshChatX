# Skill: path-jail-local-fs

Add or change local filesystem features (browse, upload, download, mkdir, delete) with a hard path jail, CSRF-safe mutators, and oracle-style tests. Do not ship file CRUD that can escape identity or feature roots.

## When to use

- New in-app file managers, uploads, downloads, or directory browsers
- Extending FileSync, RNCP, page-nodes files, docs packs, repo wheels, or similar storage APIs
- Any handler that takes a client path or multipart filename and touches disk
- Security review of existing list/read/write/delete file endpoints

Also read:

- `docs/agents/conventions/path-jail.md`
- `docs/agents/skills/auth-csrf-ws-security/SKILL.md`
- `docs/agents/skills/test-oracles/SKILL.md`
- `docs/agents/skills/page-toast-tests/SKILL.md` when adding UI

## Threat model (assume without asking)

Caller already has MeshChatX HTTP API access. They must not list, read, write, or delete outside the configured feature root. That includes host home dirs, `/etc`, other identities, and reserved identity-storage tops.

You do not need the user to restate path jail, symlink policy, CSRF, or bait-file tests. Apply them by default.

## Workflow

### 1) Choose the jail root

Pick the tightest correct root for the feature:

| Feature shape                          | Jail root                                     |
| -------------------------------------- | --------------------------------------------- |
| FileSync in-app manager                | Configured `sync_directory` only              |
| Folder picker for choosing a sync root | Identity storage with reserved tops blocked   |
| RNCP received / shared                 | That feature directory under identity storage |
| Page-node files                        | That node file directory                      |

Never use a looser picker jail for tree/upload/delete/content of a tighter feature.

### 2) One resolve helper

Add something like `_resolve_<feature>_path(...)` that:

1. Takes relative client paths only (reject absolute / drive / UNC / null bytes)
2. Uses vendor or shared normalize helpers when available (`normalize_relpath`, `resolve_under_root`)
3. Rejects forbidden names (dotfiles, protocol sidecars)
4. `realpath` membership: equal root or `root + sep` prefix
5. Symlinks: after realpath still inside root. Prefer rejecting symlink entries for write/delete/content
6. Returns fail-closed errors with generic messages (no out-of-jail path reflection)

Reference: `RnsFilesyncHandler._resolve_manager_path` in `meshchatx/src/backend/rns_filesync_handler.py`.

### 3) Wire APIs

Typical surface:

| Method        | Role                                                                              |
| ------------- | --------------------------------------------------------------------------------- |
| GET tree/list | Browse under jail (works even if a mesh service is stopped when state is on disk) |
| POST mkdir    | Relative path under jail                                                          |
| POST upload   | Multipart. Optional subdir. Basename only. Size cap                               |
| DELETE entry  | File or empty dir by default                                                      |
| GET content   | Stream only after jail pass                                                       |

HTTP: 400 on jail failure / bad input. Register routes in `tests/backend/fixtures/http_api_routes.json`. Add JSON GET contracts or exclude binary download routes in `http_api_response_registry.py`. Add mutating samples to EECT auth surface when relevant.

### 4) Frontend

- Relative paths only in the UI. Never send host absolute paths for CRUD.
- Mutators via `window.api` / FormData so CSRF attaches.
- Confirm before delete. Toasts via `ToastUtils`. User strings via i18n.
- Keep OS "open folder" as optional convenience, not the only management path.

### 5) Mandatory tests

Extend or add:

- Happy-path CRUD under the root (including stopped-service disk CRUD when applicable)
- `_TRAVERSAL_PAYLOADS`-style rejects for tree, content, delete, mkdir, upload subdir
- Absolute path to bait file outside storage (must survive)
- Reserved tops under identity storage
- Second identity storage bait in the same test
- Symlink inside root pointing outside (list/read/write/delete fail closed)
- Upload basename sanitization (path segments stripped or rejected, never escape)
- Hypothesis or explicit oracle: accept only when resolved path stays under root
- Frontend: mock `window.api`, assert upload/delete calls and toasts

Soft fuzz that only checks "did not crash" is not enough. See `test-oracles`.

## Stupid crap to refuse

- Reusing identity-storage browse APIs as the file-manager base for a tighter root
- Trusting `Content-Disposition` or multipart filenames as full save paths
- Recursive delete of arbitrary trees without an explicit, tested flag
- New WebSocket mutators for file upload/delete
- Logging full absolute paths of failed escapes into user-visible errors
- Cross-identity caches or shared temp dirs for uploads

## Verification

```bash
task test:filesync:security
uv run pytest tests/backend/test_path_jail_oracles.py -q --tb=short
pnpm exec vitest run tests/frontend/apiFetchGuard.test.js
```

Adjust pytest and vitest paths to the feature you touched. Prefer `task` targets when they exist.

## Finish gate

Do not ship until all are true:

1. Every list/read/write/delete/upload goes through the feature resolve helper
2. Escape payloads never read or delete bait files outside the root
3. Symlink-out and cross-identity cases fail closed with tests
4. Oracle or Hypothesis coverage exists for the resolve helper
5. Mutators are CSRF HTTP via `window.api`
6. Route fixture / JSON contract registry updated when routes change
