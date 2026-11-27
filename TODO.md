# TODO

Tracked codebase improvements from the 2026-11 audit. Ordered roughly by value.

## 1. Break up the meshchat.py god module

`meshchatx/meshchat.py` is ~14,000 lines with ~423 defs, a large share of them
pure delegation shims (`return self._identity_context.X`).

- [ ] Delete delegation properties in batches; pass `identity_context` (or the
      specific dependency) to the constructors that need it instead
- [ ] Split what remains into a web-server lifecycle module, an identity-switch
      module, and an RNS startup module, as the architecture doc prescribes

## 2. Split the oversized Vue components

- [ ] `ConversationViewer.vue` (~7,900 lines, ~250 methods): extract composer,
      message list, header, attachment handling, voice recording. Do it one
      piece at a time with the vitest suite as a safety net
- [ ] `MapPage.vue` (~6,500 lines)
- [ ] `SettingsPage.vue` (~6,100 lines)

## 3. Migrate new and extracted frontend code to composition API + TypeScript

No big-bang rewrite. Rule going forward: new components and anything extracted
during item 2 use `<script setup>` and TS. Current state: 118 Options API
components vs 16 `setup()` + 4 `<script setup>`, 20 `.ts` files total.

- [x] Document the rule in a contributor-facing doc
- [ ] Apply it piecemeal as components are touched for other reasons

## 4. Full-text message search

Biggest product gap. The raw-SQL style fits SQLite FTS5 directly.

- [ ] FTS5 virtual table over message content, maintained by trigger or insert
      hook, with a schema migration
- [ ] `/api/v1/messages/search` route
- [ ] Search UI in the conversation header

## 5. Accessibility pass

Only ~42 components carry any `aria-label`. One-time pass:

- [ ] Labels on icon-only buttons
- [ ] Focus management in modals
- [ ] Keyboard navigation through the sidebar and message list

## 9. Conversation export

Export a conversation as text or JSON, built on the database layer. Companion
to encrypted backup. Cheap and useful for archival.

- [ ] Backend export endpoint (text and JSON formats)
- [ ] UI entry point in the conversation header/menu

---

Tooling note: `task lint:deadcode` runs vulture (Python), knip (JS) and the Go
deadcode analyzer. vulture also runs as a blocking gate in `task lint:backend`
with protocol-parameter false positives whitelisted in
`scripts/ci/vulture_whitelist.py`. Go deadcode findings need care: the analyzer
only sees the host platform's build, so exported symbols used only on other
platforms can appear falsely unreachable.
