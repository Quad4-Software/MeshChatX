# MeshChatX agent entry

Start at [docs/agents/README.md](docs/agents/README.md).

For architecture and invariants, read [docs/agents/overview.md](docs/agents/overview.md).
For mesh design, read [docs/agents/conventions/reticulum-zen.md](docs/agents/conventions/reticulum-zen.md).

## Linux Landlock (quick)

MeshChatX applies an optional filesystem sandbox on Linux (`MESHCHAT_LANDLOCK`, see overview). Besides SQLite `temp_store`, it affects **subprocesses** and **user-local tools** (pipx Argos Translate, `~/.local/bin` wrappers, rnsh/rnx when launched as PATH scripts).

- Implementation: `meshchatx/src/backend/landlock_sandbox.py`
- SQLite symptoms and pragmas: [docs/agents/skills/landlock-sqlite/SKILL.md](docs/agents/skills/landlock-sqlite/SKILL.md)
- Integration probes (subprocess spawn, translator Argos, home write denial): `tests/backend/test_landlock_integration_surfaces.py` and `tests/backend/landlock_integration_support.py`
- After changing Landlock rules or any code that `subprocess`/`Popen`s external binaries, extend read/RW roots and add a probe test in that integration file.
