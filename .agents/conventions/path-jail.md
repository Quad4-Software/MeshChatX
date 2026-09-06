# Path jail for local filesystem APIs

Applies when adding or changing HTTP or handler code that lists, reads, writes, uploads, downloads, or deletes files under identity storage or a feature root.

## Default threat model

Treat MeshChatX local API access (UI session, shared host, scripted client) as already compromised for the purpose of path checks. The attacker must still fail to:

- Escape the feature root with ../, absolute paths, null bytes, or Windows separators
- Reach sibling identity storage or host paths outside the active identity
- Touch reserved tops (identity, lxmf, database.db, bots, plugins, backups, keys)
- Follow symlinks that point outside the jail
- Exfil via download or content endpoints that skip the same resolve helper
- Upload filenames that smuggle path segments or reserved sidecars

## Hard rules

1. One dedicated resolve helper per feature root (example: sync-root only for FileSync manager). Do not reuse a looser picker jail for CRUD.
2. Normalize then realpath. Success paths must equal the root or start with root + sep.
3. Fail closed: generic error, HTTP 400 for bad input, never 500 for jail rejects.
4. Upload: sanitize to basename only. Join under a resolved parent. Cap size.
5. Delete: refuse the root itself. Default to file or empty directory only unless recursive delete is explicit and tested.
6. Skip and refuse mutation of dotfiles and protocol sidecars (for FileSync: .rns-filesync*, .rns-xfer*).
7. Mutating routes stay CSRF-protected HTTP via window.api. No WS mutators for file CRUD.
8. Keep identity-scoped state. Never browse or mutate another identity storage path.

## Tests required

- Adversarial traversal and absolute-path cases with bait files that must survive
- Cross-identity bait directory in the same test
- Symlink-out cases (POSIX) for list, read, write, delete
- Oracle or Hypothesis: accept only when resolved path stays under the root
- Frontend mutators go through window.api (apiFetchGuard stays green)

Full workflow: .agents/skills/path-jail-local-fs/SKILL.md.
Reference implementation: meshchatx/src/backend/rns_filesync_handler.py (_resolve_manager_path and manager APIs).
Oracle examples: tests/backend/test_rns_filesync_security.py, tests/backend/test_path_jail_oracles.py.
