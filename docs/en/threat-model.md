# Threat model

Scope: the MeshChatX local application. In scope are the aiohttp UI surface
(localhost or self-hosted), the plugin runtime, the LXMF/RNS ingress path,
local file storage, and the release supply chain. Out of scope are the
mesh fabric itself (peer honesty, network availability) and OS-level
compromise of the host account.

This document is the reviewable artifact behind the controls referenced in
`identity-and-security.md` and `.agents/conventions/path-jail.md`.

## Trust boundaries

1. Browser to aiohttp UI - user (and any site in the same browser) to HTTP/WS.
2. Plugin code to PluginManager - installed plugin bundles to host APIs.
3. Mesh peers to RNS/LXMF handlers - untrusted network input to parsers and storage.
4. Process to filesystem - all file writes confined to the storage jail.
5. CI to release artifacts - build pipeline to signed downloads.

## STRIDE per element

### 1. HTTP/WebSocket surface

- Spoofing: session cookie auth on mutating routes; per-request session
  validation on WS mutators (`test_websocket_config_security.py`).
  CSRF: Origin check plus token for browser mutators; same-origin deep links
  are the standing assumption.
- Tampering: JSON schema contracts on inbound WS/HTTP payloads; payload
  size caps; structured error envelopes.
- Repudiation: session + access-attempt audit logs (`/debug/access-attempts`).
- Information disclosure: `log_redaction.py` strips paths, destination
  hashes, emails, IPs, PEM blocks from any user-facing diagnostic text.
- DoS: WS rate limits (token bucket), per-client payload caps, broadcast
  timeouts, idle-client reaping.
- Elevation: no plugin or remote input reaches `call_manager` without an
  explicit granted capability.

### 2. Plugin sandbox

- Spoofing: manifest-declared permission ids; grants normalized via
  `plugin_permissions.py`; signature verification on packaged plugins
  (invalid signatures hard-block install).
- Tampering: install-time tree hash; changed files outside the app
  auto-disable the plugin as tampered.
- Repudiation: plugin install/enable/disable recorded in app logs.
- Information disclosure: storage is namespaced per plugin
  (`storage: isolated`); `debugLog.read` returns redacted logs only.
- DoS: frontend runs in a Worker with a JSON uiDescriptor (no arbitrary
  DOM); backend Python plugins run with declared capabilities only.
- Elevation: `permissions.managers` allowlist maps to `KNOWN_MANAGERS`;
  unknown capabilities fail closed. `network: none` blocks fetch entirely.
  `ui: sandboxed-html` is the only escape hatch and is itself a grant.

### 3. LXMF / RNS ingress

- Spoofing: announce signatures verified by Reticulum; blocked-destination
  list enforced at ingress (`test_announce_ingress_gate.py`).
- Tampering: packet decoding bounded (size caps); malformed payloads drop
  before storage (`test_lxmf_rejection.py`, spam attachment strip).
- Repudiation: announces and accepted/dropped messages logged.
- Information disclosure: telemetry and attachments from strangers are
  stripped unless accepted; content defaults protect previews.
- DoS: announce rate limits and flood handling (`test_announce_flood_load.py`),
  ingress gate, per-peer message caps, expiry sweeps.
- Elevation: no inbound message can trigger filesystem writes outside the
  storage jail; file sync paths resolve through `resolve_safe_path`.

### 4. Filesystem path jail

- All user-influenced paths (backup restore, plugin assets, file sync,
  identity dirs, translation packs) resolve through canonicalization +
  jail-root membership checks. Reference: `test_security_path_jail_regressions.py`,
  `test_translation_pack_manager_properties.py`.
- SQLite storage is per-identity; backups/restores never write outside the
  storage root.
- `MESHCHAT_LANDLOCK` further narrows the process filesystem view; SQLite
  runs `temp_store=MEMORY` under Landlock (`.agents` Landlock trap note).

### 5. Release supply chain

- SLSA3 provenance for release binaries, cosign attestations, CycloneDX
  SBOM per release, Rekor log monitoring (`rekor-monitor.yml`), OpenSSF
  Scorecard, weekly SBOM re-scan for post-release CVEs, OpenVEX triage
  document shipped with releases.
- CI itself: SHA-pinned actions, minimal job permissions, harden-runner
  egress audit, zizmor workflow self-analysis, gitleaks history + diff
  scanning.

## Standing assumptions

- The host OS account running MeshChatX is trusted at the OS level. The
  jail resists application-level escapes, not a hostile kernel or a
  compromised user account.
- Loopback binding is the default trust boundary; self-hosted deployments
  must keep auth enabled (`identity-and-security.md` covers reverse-proxy
  and TLS guidance).
- Peer honesty is out of scope: malformed input is defended, a sybil-fed
  but well-formed stream is a protocol problem, not an app bug.

## Review procedure

- Update this file when a new trust boundary appears (new remote surface,
  new plugin capability class, new file-writing feature).
- Every closed gap should land as a regression test, listed next to the
  control it proves.
