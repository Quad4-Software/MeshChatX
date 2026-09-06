# .agents index

Agent guidance only. End-user docs: docs/en/.
Entry: root AGENTS.md. Always-on rules: .agents/conventions/core.md and .agents/conventions/reticulum-zen.md.

## Open by need

| Need                                  | File                                                         |
| ------------------------------------- | ------------------------------------------------------------ |
| Architecture, storage, security, env  | [overview.md](overview.md)                                   |
| Domain to manager / HTTP / WS / tests | [module-ownership.md](module-ownership.md)                   |
| Mesh Zen gates                        | [conventions/reticulum-zen.md](conventions/reticulum-zen.md) |
| Always-on standards                   | [conventions/core.md](conventions/core.md)                   |
| Vue UI / Svelte dual stack            | [conventions/frontend.md](conventions/frontend.md)           |
| Python / HTTP / SQLite                | [conventions/backend.md](conventions/backend.md)             |
| Local FS jail                         | [conventions/path-jail.md](conventions/path-jail.md)         |
| Android WebView                       | [conventions/android.md](conventions/android.md)             |
| Tests / oracles / contracts           | [conventions/tests.md](conventions/tests.md)                 |
| Commit messages                       | [conventions/commits.md](conventions/commits.md)             |

Skills: one file each at skills/<name>/SKILL.md. Open the matching skill before coding that surface.

## Skills (trigger to path)

| Trigger                                  | Skill                                                                        |
| ---------------------------------------- | ---------------------------------------------------------------------------- |
| prose, docs, UI copy                     | [no-ai-slop](skills/no-ai-slop/SKILL.md)                                     |
| Rossmann voice (only if asked)           | [rossmann-voice](skills/rossmann-voice/SKILL.md)                             |
| mesh design review                       | [reticulum-design-gates](skills/reticulum-design-gates/SKILL.md)             |
| destination hash, aspect, announce, path | [reticulum-stack](skills/reticulum-stack/SKILL.md)                           |
| interfaces, RNode, medium-agnostic       | [reticulum-interfaces](skills/reticulum-interfaces/SKILL.md)                 |
| RNS Link WS                              | [rns-link-api](skills/rns-link-api/SKILL.md)                                 |
| LXMF send/receive                        | [lxmf-messaging](skills/lxmf-messaging/SKILL.md)                             |
| LXST calls / audio WS                    | [lxst-telephony](skills/lxst-telephony/SKILL.md)                             |
| Relay Chat / RRC                         | [rrc-relay-chat](skills/rrc-relay-chat/SKILL.md)                             |
| FileSync                                 | [rns-filesync](skills/rns-filesync/SKILL.md)                                 |
| NomadNet / page nodes                    | [nomad-pages](skills/nomad-pages/SKILL.md)                                   |
| privacy mode / clearnet HTTP             | [privacy-mode-clearnet](skills/privacy-mode-clearnet/SKILL.md)               |
| new page, toast, i18n                    | [page-toast-tests](skills/page-toast-tests/SKILL.md)                         |
| nav, tools, commands, WS registry        | [contribution-registries](skills/contribution-registries/SKILL.md)           |
| Svelte 5 / feature modules               | [svelte-feature-modules](skills/svelte-feature-modules/SKILL.md)             |
| Vue mega-page extract                    | [vue-mega-page-split](skills/vue-mega-page-split/SKILL.md)                   |
| HTTP/WS extract from meshchat.py         | [meshchat-orchestration-split](skills/meshchat-orchestration-split/SKILL.md) |
| identity key vs zip restore              | [identity-restore](skills/identity-restore/SKILL.md)                         |
| identity switch teardown                 | [identity-switch-teardown](skills/identity-switch-teardown/SKILL.md)         |
| migrations, backups                      | [database-migrations-backups](skills/database-migrations-backups/SKILL.md)   |
| Landlock + SQLite + CLI probes           | [landlock-sqlite](skills/landlock-sqlite/SKILL.md)                           |
| CSRF, auth, WS mutators                  | [auth-csrf-ws-security](skills/auth-csrf-ws-security/SKILL.md)               |
| path jail file CRUD                      | [path-jail-local-fs](skills/path-jail-local-fs/SKILL.md)                     |
| plugins, RSG, permissions                | [plugin-install-security](skills/plugin-install-security/SKILL.md)           |
| URL origin allowlists                    | [url-origin-allowlists](skills/url-origin-allowlists/SKILL.md)               |
| HTTP-up vs RNS-ready                     | [deferred-network-startup](skills/deferred-network-startup/SKILL.md)         |
| Electron frozen packaging                | [electron-frozen-packaging](skills/electron-frozen-packaging/SKILL.md)       |
| Android bridge                           | [android-webview-bridge](skills/android-webview-bridge/SKILL.md)             |
| focused test loops                       | [test-loop](skills/test-loop/SKILL.md)                                       |
| property / fuzz oracles                  | [test-oracles](skills/test-oracles/SKILL.md)                                 |
| exploratory bug hunt                     | [exploratory-testing](skills/exploratory-testing/SKILL.md)                   |
| experimental WebTransport live           | [webtransport-experimental](skills/webtransport-experimental/SKILL.md)       |

Zen philosophy: https://reticulum.network/manual/zen.html

## Product docs (users)

```
docs/en/architecture.md
docs/en/identity-and-security.md
docs/en/getting-started.md
docs/en/rns-link-api.md
docs/en/platform-guides/linux-sandbox.md
CONTRIBUTING.md
```
