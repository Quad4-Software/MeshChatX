# Backend conventions

Applies when editing meshchatx/**/*.py.

- Prefer uv run / task for pytest and ruff.
- HTTP handlers: return 400 for ValueError / bad input, 503 for retryable SQLite/Landlock unavailability, 500 only for unexpected failures.
- Thin HTTP handlers live under meshchatx/src/backend/http/routes/. Parse the request, call a manager or app method, map errors. Do not add new business logic in route modules.
- Shared HTTP helpers: backend/http/errors.py, backend/http/context.py, backend/http/middleware.py, backend/http/register.py, backend/http/live_names.py.
- errors.py and context.py are intentional scaffolding. Adopt http_bad_request / http_unavailable / http_unexpected only when a handler is already thin. Do not refactor fat handlers only to call them.
- When splitting or moving handlers among routes/<domain>.py, follow .agents/skills/meshchat-orchestration-split/SKILL.md and .agents/module-ownership.md. Mechanical moves only (no behaviour change in the same change).
- Multipart parsers must not assume field order.
- SQLite worker connections must set temp_store=MEMORY in DatabaseProvider (Landlock-safe).
- Under Landlock, memory-pressure must not force FILE temp for conversation queries.
- Subprocess or user-local CLI features must remain usable under Landlock. Extend landlock_sandbox.py read/RW roots and add a probe in tests/backend/test_landlock_integration_surfaces.py (see landlock-sqlite skill).
- Keep conversation list queries slim: truncate content, derive attachment flags in SQL, avoid shipping full fields blobs.
- Identity restore validates size and empty payloads. Preserve existing identity metadata on re-import.
- No backticks in code comments. Prefer plain words or quoted identifiers.
- RRC / LXMF / LXST changes: open the matching skill under .agents/skills/ and run oracle-style tests when behaviour changes.
- Local filesystem browse/upload/download/delete: follow .agents/conventions/path-jail.md and .agents/skills/path-jail-local-fs/SKILL.md.
