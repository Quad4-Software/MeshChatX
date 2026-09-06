# Core conventions

Progressive load: root AGENTS.md, then one skill and one surface convention. Full index: .agents/README.md.

- Architecture / storage / security / env: .agents/overview.md (only when needed).
- Mesh-facing work: .agents/conventions/reticulum-zen.md then .agents/skills/reticulum-design-gates/SKILL.md.
- Commit messages on GitHub: .agents/conventions/commits.md. Run task hooks:install once per clone.

Hard rules below are always on.

## Prose

Before writing or editing prose, read .agents/skills/no-ai-slop/SKILL.md and self-check against .agents/skills/no-ai-slop/references/ai-writing-detection.md. The 24 rules are in .agents/skills/no-ai-slop/references/rules.md.

Say what the thing is. Headings name the section contents. Every claim ends on a checkable detail (a path, an API, a status code, a measured quantity). Do not invent numbers, quotes, or incidents.

When editing CHANGELOG.md, use the current CHANGELOG.md as the style reference: terse bullets, **Area**: detail, imperative mood, and specific checkable facts.

Load .agents/skills/rossmann-voice/SKILL.md only when the user asks for that voice. Do not rewrite MeshChatX technical docs into that voice by default.
