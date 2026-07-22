# Backend conventions

Applies when editing `meshchatx/**/*.py`.

- Prefer `uv run` / `task` for pytest and ruff.
- HTTP handlers: return 400 for `ValueError` / bad input, 503 for retryable SQLite/Landlock unavailability, 500 only for unexpected failures.
- Multipart parsers must not assume field order.
- SQLite worker connections must set `temp_store=MEMORY` in `DatabaseProvider` (Landlock-safe).
- Under Landlock, memory-pressure must not force FILE temp for conversation queries.
- Keep conversation list queries slim: truncate content, derive attachment flags in SQL, avoid shipping full `fields` blobs.
- Identity restore validates size and empty payloads. Preserve existing identity metadata on re-import.
- No backticks in code comments. Prefer plain words or quoted identifiers.
- RRC / LXMF / LXST changes: open the matching skill under `docs/agents/skills/` and run oracle-style tests when behaviour changes.
- Local filesystem browse/upload/download/delete: follow `docs/agents/conventions/path-jail.md` and `docs/agents/skills/path-jail-local-fs/SKILL.md`.
