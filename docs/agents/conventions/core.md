# Core conventions

- Read `docs/agents/overview.md` for layout, commands, and domain traps.
- Mesh-facing work: read `docs/agents/conventions/reticulum-zen.md` and run `docs/agents/skills/reticulum-design-gates/SKILL.md` gates first.
- Prefer `task` targets (`format`, `lint`, `test:quick`, `test:backend`, `test:frontend`).
- Minimal diffs. Match nearby style. Keep SPDX headers on new project files (`0BSD` unless file already differs).
- No emojis in repo text. No TODO/FIXME comment noise.
- No emdashes or semicolons in comments or docs you write.
- No backticks in code comments. Prefer plain words or quoted identifiers.
- Do not commit/push unless asked.
- User-visible UI strings: i18n keys. Action feedback: `ToastUtils`.
- Do not invent install/run flows when Taskfile already covers them.
- Do not create markdown docs unless asked (except agent guidance under `docs/agents/` when requested).
- Do not generate exploit PoCs, malware, or attack tooling.
