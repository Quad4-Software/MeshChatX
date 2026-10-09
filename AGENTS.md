# Working notes for contributors and agents

## Relay chat wire behavior

RRC hubs are stateless relays. Anything a client sends reaches every room
member, so a client bug becomes network-wide spam. Keep these rules when
touching `meshchatx/src/backend/rrc/`:

- Every retry must be idempotent. Reuse the original envelope id and
  timestamp so receivers collapse a retry with the original copy.
- Retries must be bounded. Auto-retry only failures from the current
  session, never history loaded from disk. The protocol has no memory
  across links.
- Every chat envelope must spend a send budget token. Hubs advertise
  `rate_limit_msgs_per_minute` in WELCOME and may drop the link for
  clients that exceed it.
- Restarts must be silent. A reconnect may rejoin rooms and request the
  room list, nothing else.
- Wire-level behavior changes need a loopback invariant test in
  `tests/backend/test_rrc_wire_invariants.py`. RNS link payloads are
  encrypted, so packet captures cannot verify this.

## Verification

- Backend: `uv run pytest tests/backend -k rrc`
- Frontend: `npx vitest run tests/frontend/RelayChatPage.test.js`
- Lint: `uv run ruff check .` and eslint on touched files
- Live e2e: `npx playwright test tests/e2e/nomad-favourites-menu.spec.js`

## Commit provenance

AI-assisted commits carry trailers described in AI.md.
