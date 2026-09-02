# MeshChatX agent entry

Start at [.agents/README.md](.agents/README.md).

Architecture and invariants: [.agents/overview.md](.agents/overview.md).
Mesh design: [.agents/conventions/reticulum-zen.md](.agents/conventions/reticulum-zen.md).
Prose: [.agents/skills/no-ai-slop/SKILL.md](.agents/skills/no-ai-slop/SKILL.md) before writing or editing docs, UI copy, or commit messages longer than a sentence.

## Linux Landlock

Optional filesystem sandbox on Linux (MESHCHAT_LANDLOCK, see overview). Besides SQLite temp_store, it affects subprocesses and user-local tools (pipx Argos Translate, ~/.local/bin wrappers, rnsh/rnx launched as PATH scripts).

- Implementation: meshchatx/src/backend/landlock_sandbox.py
- SQLite symptoms and pragmas: [.agents/skills/landlock-sqlite/SKILL.md](.agents/skills/landlock-sqlite/SKILL.md)
- Integration probes (subprocess spawn, translator Argos, home write denial): tests/backend/test_landlock_integration_surfaces.py and tests/backend/landlock_integration_support.py
- After changing Landlock rules or any code that subprocess/Popens external binaries, extend read/RW roots and add a probe test in that integration file.
