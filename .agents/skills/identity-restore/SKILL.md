---
name: identity-restore
description: Identity key import vs database zip restore, tutorial and Android pickers. Use when changing identity restore UI, APIs, or file accept lists.
---

# Skill: identity-restore

Identity key import vs database zip restore, tutorial and Android pickers.

# MeshChatX Identity Restore

## Two different restores

Full table of goal / UI / API for both restore paths: .agents/overview.md (Identity key restore vs database restore section).
Never imply identity-key import restores message history.

## Guards checklist

- File picker accept: .bin,.key,.identity,application/octet-stream,*/*
- Export download filename: identity.bin
- Reject empty / oversized identity payloads (client + server, max 64 KiB)
- Normalize base32 by stripping all whitespace
- Multipart field order must not matter
- ValueError → HTTP 400
- Re-import must preserve existing metadata (icons/addresses)
- Tutorial: import on Continue, activate on Finish. Split switch vs delete failures.
- Tutorial skip/abandon with pending import: confirm activate or warn
- IdentitiesPage: keep modal open during restore, toast errors, offer switch after success
- Android: map extension accepts to MIME types in MainActivity

## Tests to update

- tests/frontend/TutorialModalMigration.test.js
- tests/frontend/IdentitiesPage.test.js
- tests/backend/test_identity_restore.py
- tests/backend/test_identity_restore_http_api.py

## Key files

- meshchatx/src/frontend/components/TutorialModal.vue
- meshchatx/src/frontend/features/settings/components/IdentitiesPage.svelte
- meshchatx/src/frontend/features/about/AboutPage.svelte
- meshchatx/src/backend/identity_manager.py
- meshchatx/meshchat.py (identity backup/restore routes)
- android/.../MainActivity.java
