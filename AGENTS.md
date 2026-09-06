# MeshChatX agent entry

Load only what the task needs. Do not dump the whole tree into context.

## Load order

1. Task match: open one skill under .agents/skills/<name>/SKILL.md (index: .agents/README.md).
2. Surface: open one file under .agents/conventions/ (frontend, backend, android, tests, path-jail, commits).
3. Mesh behaviour: .agents/conventions/reticulum-zen.md then .agents/skills/reticulum-design-gates/SKILL.md.
4. Architecture / storage / security / env: .agents/overview.md.
5. Where code lives: .agents/module-ownership.md.
6. Prose: .agents/skills/no-ai-slop/SKILL.md.

Hard rules and skill triggers also live in .agents/conventions/core.md (always on).
Zen gates: .agents/conventions/reticulum-zen.md.

## Do not confuse

| Topic                          | Open                                          |
| ------------------------------ | --------------------------------------------- |
| Identity key vs zip restore    | .agents/skills/identity-restore/SKILL.md      |
| Landlock + SQLite + subprocess | .agents/skills/landlock-sqlite/SKILL.md       |
| CSRF / WS mutators             | .agents/skills/auth-csrf-ws-security/SKILL.md |
| Local file path jail           | .agents/conventions/path-jail.md              |
| Privacy mode vs mesh traffic   | .agents/skills/privacy-mode-clearnet/SKILL.md |

## Landlock trap

MESHCHAT_LANDLOCK sandboxes the process. SQLite must keep temp_store=MEMORY under Landlock. Features that call Popen or read outside allowed roots need rule updates plus a probe in:

```
tests/backend/test_landlock_integration_surfaces.py
```

Implementation: meshchatx/src/backend/landlock_sandbox.py.
User docs: docs/en/.
Agent docs: .agents/ only.
