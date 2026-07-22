# Agent guidance for MeshChatX

Neutral, tool-agnostic notes for automated agents and human contributors who work like agents.
This tree is not part of the in-app user documentation. End-user docs live under `docs/en/`.

## Start here

1. Read [overview.md](overview.md) for architecture, storage, security, env vars, and invariants.
2. Read [conventions/reticulum-zen.md](conventions/reticulum-zen.md) before any mesh-facing design or code.
3. Apply [conventions/](conventions/) for the surface you are editing.
4. Open a [skills/](skills/) guide when the task matches that workflow.

Root [AGENTS.md](../../AGENTS.md) is a short pointer to this directory.

Optional editor rules (if present under `.cursor/rules/` or similar):

- Always on: MeshChatX core standards and Reticulum Zen gates
- Globs: backend, frontend, Android, tests

## Layout

| Path                                                         | Purpose                                   |
| ------------------------------------------------------------ | ----------------------------------------- |
| [overview.md](overview.md)                                   | Project brief and critical invariants     |
| [module-ownership.md](module-ownership.md)                   | Domain to manager / HTTP / WS / tests map |
| [conventions/reticulum-zen.md](conventions/reticulum-zen.md) | Zen of Reticulum hard gates               |
| [conventions/core.md](conventions/core.md)                   | Always-on standards                       |
| [conventions/frontend.md](conventions/frontend.md)           | Vue UI                                    |
| [conventions/backend.md](conventions/backend.md)             | Python / HTTP / SQLite                    |
| [conventions/path-jail.md](conventions/path-jail.md)         | Local FS APIs: jail, symlinks, tests      |
| [conventions/android.md](conventions/android.md)             | Android WebView bridge                    |
| [conventions/tests.md](conventions/tests.md)                 | Test placement, oracles, verification     |

## Skills

### UI and wiring

| Skill                                                                        | Use when                                               |
| ---------------------------------------------------------------------------- | ------------------------------------------------------ |
| [page-toast-tests](skills/page-toast-tests/SKILL.md)                         | New pages, toasts, i18n, tests                         |
| [contribution-registries](skills/contribution-registries/SKILL.md)           | Nav, tools, commands, settings search, WS event wiring |
| [meshchat-orchestration-split](skills/meshchat-orchestration-split/SKILL.md) | Extract HTTP/WS from meshchat.py, multi-file scanners  |

### Mesh protocols (RNS / LXMF / LXST / RRC)

| Skill                                                            | Use when                                                  |
| ---------------------------------------------------------------- | --------------------------------------------------------- |
| [reticulum-design-gates](skills/reticulum-design-gates/SKILL.md) | Any mesh design review against Zen of Reticulum           |
| [rns-link-api](skills/rns-link-api/SKILL.md)                     | Generic RNS Link WebSocket / plugin transport             |
| [lxmf-messaging](skills/lxmf-messaging/SKILL.md)                 | LXMF send/receive, stamps, propagation, attachments       |
| [lxst-telephony](skills/lxst-telephony/SKILL.md)                 | LXST calls, audio WS, telephony managers                  |
| [rrc-relay-chat](skills/rrc-relay-chat/SKILL.md)                 | Relay Chat hubs, rooms, +k keys, moderation, client state |

### Identity and data

| Skill                                                                      | Use when                                          |
| -------------------------------------------------------------------------- | ------------------------------------------------- |
| [identity-restore](skills/identity-restore/SKILL.md)                       | Identity key vs database zip restore              |
| [identity-switch-teardown](skills/identity-switch-teardown/SKILL.md)       | Live identity switch without cross-identity leaks |
| [database-migrations-backups](skills/database-migrations-backups/SKILL.md) | Schema bumps, backups, snapshots, restore safety  |
| [landlock-sqlite](skills/landlock-sqlite/SKILL.md)                         | Landlock + SQLite conversation failures           |

### Security and plugins

| Skill                                                              | Use when                                    |
| ------------------------------------------------------------------ | ------------------------------------------- |
| [auth-csrf-ws-security](skills/auth-csrf-ws-security/SKILL.md)     | CSRF, auth, WS mutator denylist             |
| [path-jail-local-fs](skills/path-jail-local-fs/SKILL.md)           | Local file browse/upload/delete path jails  |
| [plugin-install-security](skills/plugin-install-security/SKILL.md) | Plugin install, RSG, permissions, integrity |

### Platforms and boot

| Skill                                                                  | Use when                                      |
| ---------------------------------------------------------------------- | --------------------------------------------- |
| [deferred-network-startup](skills/deferred-network-startup/SKILL.md)   | HTTP-up vs RNS-ready, status, 503s, RNS panic |
| [electron-frozen-packaging](skills/electron-frozen-packaging/SKILL.md) | Frozen desktop spawn, loading, crash recovery |
| [android-webview-bridge](skills/android-webview-bridge/SKILL.md)       | Android chooser MIME, storage, WebView nav    |

### Verification

| Skill                                                      | Use when                                             |
| ---------------------------------------------------------- | ---------------------------------------------------- |
| [test-loop](skills/test-loop/SKILL.md)                     | Focused verification without hung shells             |
| [test-oracles](skills/test-oracles/SKILL.md)               | Property/fuzz oracles: accept/reject, not soft fuzz  |
| [exploratory-testing](skills/exploratory-testing/SKILL.md) | Adversarial exploration to find bugs with hypotheses |

## Product docs (users)

- `docs/en/architecture.md`
- `docs/en/identity-and-security.md`
- `docs/en/getting-started.md`
- `docs/en/rns-link-api.md`
- `docs/en/platform-guides/linux-sandbox.md`
- `CONTRIBUTING.md`
