# Core conventions

Progressive load: root `AGENTS.md`, then one skill and one surface convention. Full index: `.agents/README.md`.

- Architecture / storage / security / env: `.agents/overview.md` (only when needed).
- Mesh-facing work: `.agents/conventions/reticulum-zen.md` then `.agents/skills/reticulum-design-gates/SKILL.md`.
- Prefer Taskfile targets (`format`, `lint`, `test:quick`, `test:backend`, `test:frontend`).
- Commit messages on GitHub: `.agents/conventions/commits.md`. Run `task hooks:install` once per clone.
- Minimal diffs. Match nearby style. Keep SPDX headers on new project files (`0BSD` unless file already differs).
- No emojis in repo text or agent replies. No emoji arrows or decorative unicode arrows at all.
- No TODO/FIXME comment noise.
- No emdashes or semicolons in comments or docs you write.
- Prefer fenced code blocks over inline backticks for commands, paths, and snippets. Short names can stay plain words or quoted identifiers.
- No backticks in code comments. Prefer plain words or quoted identifiers.
- CHANGELOG.md entries: plain sentences with a bold lead label, no backticks or code spans, no emdashes. Keep it simple and user-facing.
- Do not commit/push unless asked.
- User-visible UI strings: i18n keys. Action feedback: ToastUtils.
- Do not invent install/run flows when Taskfile already covers them.
- Do not create markdown docs unless asked (except agent guidance under `.agents/` when requested).
- Do not generate exploit PoCs, malware, or attack tooling.

## Prose

Before writing or editing prose, read `.agents/skills/no-ai-slop/SKILL.md` and self-check against `.agents/skills/no-ai-slop/references/ai-writing-detection.md`. The 24 rules are in `.agents/skills/no-ai-slop/references/rules.md`.

Say what the thing is. Headings name the section contents. Every claim ends on a checkable detail (a path, an API, a status code, a measured quantity). Do not invent numbers, quotes, or incidents.

Load `.agents/skills/rossmann-voice/SKILL.md` only when the user asks for that voice. Do not rewrite MeshChatX technical docs into that voice by default.
