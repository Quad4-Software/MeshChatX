# Core conventions

- Read `.agents/overview.md` for layout, commands, and domain traps.
- Mesh-facing work: read `.agents/conventions/reticulum-zen.md` and run `.agents/skills/reticulum-design-gates/SKILL.md` gates first.
- Prefer `task` targets (`format`, `lint`, `test:quick`, `test:backend`, `test:frontend`).
- Minimal diffs. Match nearby style. Keep SPDX headers on new project files (`0BSD` unless file already differs).
- No emojis in repo text. No TODO/FIXME comment noise.
- No emdashes or semicolons in comments or docs you write.
- No backticks in code comments. Prefer plain words or quoted identifiers.
- Do not commit/push unless asked.
- User-visible UI strings: i18n keys. Action feedback: `ToastUtils`.
- Do not invent install/run flows when Taskfile already covers them.
- Do not create markdown docs unless asked (except agent guidance under `.agents/` when requested).
- Do not generate exploit PoCs, malware, or attack tooling.

## Prose

Before writing or editing prose, read `.agents/skills/no-ai-slop/SKILL.md` and self-check against `.agents/skills/no-ai-slop/references/ai-writing-detection.md`. The 24 rules are in `.agents/skills/no-ai-slop/references/rules.md`.

Say what the thing is. Headings name the section contents. Every claim ends on a checkable detail (a path, an API, a status code, a measured quantity). Do not invent numbers, quotes, or incidents.

Load `.agents/skills/rossmann-voice/SKILL.md` only when the user asks for that voice. Do not rewrite MeshChatX technical docs into that voice by default.
