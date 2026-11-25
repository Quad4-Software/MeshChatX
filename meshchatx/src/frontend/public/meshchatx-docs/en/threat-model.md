# Threat model

Scope: the MeshChatX local application. In scope are the aiohttp UI surface
(localhost or self-hosted), the plugin runtime, the LXMF/RNS ingress path,
local file storage, and the release supply chain. Out of scope are the
mesh fabric itself (peer honesty, network availability) and OS-level
compromise of the host account.

This document is the reviewable artifact behind the controls referenced in
`identity-and-security.md`.

## Trust boundaries

1. Browser to aiohttp UI - user (and any site in the same browser) to HTTP/WS.
2. Plugin code to PluginManager - installed plugin bundles to host APIs.
3. Mesh peers to RNS/LXMF handlers - untrusted network input to parsers and storage.
4. Process to filesystem - all file writes confined to the storage jail.
5. CI to release artifacts - build pipeline to signed downloads.

## STRIDE per element

### 1. HTTP/WebSocket surface

- Spoofing: session cookie auth on mutating routes, per-request session
  validation on WS mutators (`test_websocket_config_security.py`).
  CSRF: Origin check plus token for browser mutators. Same-origin deep
  links are the standing assumption.
- Tampering: JSON schema contracts on inbound WS/HTTP payloads, payload
  size caps, structured error envelopes.
- Repudiation: session + access-attempt audit logs (`/debug/access-attempts`).
- Information disclosure: `log_redaction.py` strips paths, destination
  hashes, emails, IPs, PEM blocks from any user-facing diagnostic text.
- DoS: WS rate limits (token bucket), per-client payload caps, broadcast
  timeouts, idle-client reaping.
- Elevation: no plugin or remote input reaches `call_manager` without an
  explicit granted capability.

### 2. Plugin sandbox

- Spoofing: manifest-declared permission ids, grants normalized via
  `plugin_permissions.py`, signature verification on packaged plugins
  (invalid signatures hard-block install).
- Tampering: install-time tree hash, changed files outside the app
  auto-disable the plugin as tampered.
- Repudiation: plugin install/enable/disable recorded in app logs.
- Information disclosure: storage is namespaced per plugin
  (`storage: isolated`), and `debugLog.read` returns redacted logs only.
- DoS: frontend runs in a Worker with a JSON uiDescriptor (no arbitrary
  DOM). Direct worker network access is blocked by CSP.
- Python plugins require the explicit `backend:python` grant but execute
  in-process with the app user's OS privileges. Treat them as trusted code.
  Declared host capabilities do not sandbox arbitrary Python imports or I/O.
- Elevation: `permissions.managers` allowlist maps to `KNOWN_MANAGERS`.
  Unknown capabilities fail closed for host calls. `network: none` denies the
  host network flag but does not constrain a granted Python backend.
  `ui: sandboxed-html` is the only escape hatch and is itself a grant.

### 3. LXMF / RNS ingress

- Spoofing: announce signatures verified by Reticulum, blocked-destination
  list enforced at ingress (`test_announce_ingress_gate.py`).
- Tampering: packet decoding bounded (size caps), malformed payloads drop
  before storage (`test_lxmf_rejection.py`, spam attachment strip).
- Repudiation: announces and accepted/dropped messages logged.
- Information disclosure: telemetry and attachments from strangers are
  stripped unless accepted, content defaults protect previews.
- DoS: announce rate limits and flood handling (`test_announce_flood_load.py`),
  ingress gate, per-peer message caps, expiry sweeps.
- Elevation: no inbound message can trigger filesystem writes outside the
  storage jail. File sync paths resolve through `resolve_under_root`.

### 4. Filesystem path jail

- All user-influenced paths (backup restore, plugin assets, file sync,
  identity dirs, translation packs) resolve through canonicalization +
  jail-root membership checks. Reference: `test_security_path_jail_regressions.py`,
  `test_translation_pack_manager_properties.py`.
- SQLite storage is per-identity, and backups/restores never write outside
  the storage root.
- `MESHCHAT_LANDLOCK` further narrows the process filesystem view, and SQLite
  runs `temp_store=MEMORY` under Landlock.

### 5. Release supply chain

- SLSA3 provenance for release binaries, cosign attestations, CycloneDX
  SBOM per release, OpenVEX triage document shipped with releases.
- CI itself: SHA-pinned actions, minimal job permissions, harden-runner
  egress audit, zizmor workflow self-analysis, gitleaks history + diff
  scanning.

### 6. Update delivery

- The signed manifest is the only trust anchor. Mirrors, the CDN,
  release hosts, RNS peers and peer relays are untrusted transports.
- Pins: signer identity hash (32 or 64 hex), channel binding inside the
  signed payload, expiry, high-water mark per channel, downgrade
  rejection, per-artifact SHA-256 and size, blockmap hash.
- Staging is atomic under the storage jail, and apply happens only through
  the desktop relaunch path or manual install, never mid-session.
- RNS update links use an ephemeral identity, never the main LXMF
  identity. Peer relay is opt-in and serves only manifest-verified
  hashes under rate limits.
- Residual risk: a compromised release signing key can ship malicious
  updates. Mitigate by pinning additional signers or replacing the
  default. A hostile mirror can withhold updates (availability), never
  forge them.

## Standing assumptions

- The host OS account running MeshChatX is trusted at the OS level. The
  jail resists application-level escapes, not a hostile kernel or a
  compromised user account.
- Loopback binding is the default trust boundary, so self-hosted deployments
  must keep auth enabled (`identity-and-security.md` covers reverse-proxy
  and TLS guidance).
- Peer honesty is out of scope: malformed input is defended, a sybil-fed
  but well-formed stream is a protocol problem, not an app bug.

## Review procedure

- Update this file when a new trust boundary appears (new remote surface,
  new plugin capability class, new file-writing feature).
- Every closed gap should land as a regression test, listed next to the
  control it proves.
