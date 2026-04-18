# Sidecar Extension Protocol Draft (SEP v1)

This is a draft design for extension support in MeshChatX.

## Goals

- Keep extension failures isolated from core messaging runtime.
- Provide a stable, versioned API for trusted and power-user automation.
- Minimize direct access to Reticulum internals, local DB internals, and process memory.
- Support repeatable testing, contract validation, and fuzzing from day one.

## Non-Goals

- No in-process plugin execution in v1.
- No arbitrary UI code execution inside the main frontend runtime in v1.
- No remote extension installation pipeline in v1.

## Runtime Model

- MeshChatX host discovers extension manifests from a local configured directory.
- Each extension is started as a separate local process.
- Host and extension communicate over a local JSON-RPC channel.
- Host enforces capability checks on every privileged request.
- Host applies lifecycle controls: startup timeout, health checks, backoff restart policy, and hard stop.

## Platform Profiles

SEP v1 uses a shared manifest with platform-specific runtime profiles.

### Desktop Profile (Linux, Windows, macOS)

- Sidecar process execution is allowed via manifest entrypoint.
- Local IPC transport defaults to Unix domain socket or localhost loopback transport.
- Full `entrypoint` command and args model applies.

### Android Profile

- Android support is planned as a constrained profile, not a full desktop-equivalent runtime.
- Host may reject arbitrary executable launch and require approved runtimes or packaged modules.
- Lifecycle contract must tolerate app pause/resume, background restrictions, and process reclaim.
- Extensions should assume tighter CPU/memory quotas and more aggressive timeout enforcement.
- Long-running background behavior should be explicit and policy-gated by host configuration.

## Trust Model

Three trust levels are defined in the manifest:

- `first_party`: shipped and maintained with MeshChatX.
- `trusted_third_party`: explicitly approved by operator policy.
- `untrusted_local`: local experiments with restrictive permissions and stricter limits.

Even for trusted extensions, API permissions are explicit and least-privilege.

## API Shape (Draft)

Host to extension:

- `sep.initialize`
- `sep.event`
- `sep.health`
- `sep.shutdown`

Extension to host:

- `host.get_capabilities`
- `host.messages.send`
- `host.messages.list`
- `host.contacts.list`
- `host.ui.register_tool_panel`
- `host.notifications.toast`

All methods are version-gated by protocol version and permission checks.

## Permission Model

Permissions are stable string capabilities. Initial candidates:

- `messages.read`
- `messages.send`
- `contacts.read`
- `events.subscribe`
- `tools.register`
- `notifications.create`

Permissions should be audited in logs with extension id, method name, decision, and reason.

## UI Integration Constraints

v1 should avoid arbitrary extension-rendered code in core UI.

Allowed model:

- Extension registers metadata for approved host-owned UI slots.
- MeshChatX renders UI components and invokes extension actions through host API.

This keeps UX consistent and lowers attack surface.

## Draft Manifest Contract

See `docs/sep_manifest.example.json` for an initial manifest layout and `docs/sep_manifest.schema.json` for the draft validation contract.

Required fields:

- `id`
- `name`
- `version`
- `apiVersion`
- `entrypoint`
- `permissions`
- `trustLevel`
- `health`
- `limits`

Optional platform section:

- `platformProfile`
- `android` (required when `platformProfile` is `android`)

## Error Handling and Resilience

- Host returns structured errors with stable codes.
- Extension failures do not crash host runtime.
- Host tracks crash loops and disables extensions after policy threshold.
- Startup and request timeouts are mandatory.

## Observability

- Per-extension log stream with bounded retention.
- Metrics counters: starts, exits, restarts, failed RPC calls, denied permissions.
- Optional debug tracing mode for protocol troubleshooting.

## Testing Strategy

### Contract Tests

- Validate manifest schema acceptance/rejection.
- Validate capability enforcement per API method.
- Validate version negotiation and downgrade behavior.

### Integration Tests

- Start host with a fixture extension process and assert lifecycle transitions.
- Verify extension crash does not affect messaging flows.
- Verify timeout and restart policies.
- For Android profile, simulate pause/resume and process restart during active extension calls.

### End-to-End Tests

- Register tool panel metadata and validate host UI representation.
- Send and receive sample messages through extension API path.
- Validate Android profile fallback behavior when sidecar runtime is unavailable.

### Regression Tests

- Freeze behavior for error codes and permission-denied responses.
- Snapshot protocol payloads for compatibility checks.

## Fuzzing Plan

### Message-Level Fuzzing

- Fuzz JSON-RPC payload structure, field types, nested depth, and size boundaries.
- Fuzz invalid method names, duplicate ids, malformed params, and unknown capability requests.

### State Transition Fuzzing

- Randomize lifecycle sequences: initialize, event storm, health checks, shutdown, restart loops.
- Inject extension process faults during active calls.

### Boundary Fuzzing

- Oversized payloads near configured limits.
- High-rate event bursts to verify backpressure controls.
- Invalid UTF-8 and control character edge cases in text fields.
- Android-profile fuzzing for lifecycle churn: rapid foreground/background transitions and delayed heartbeat acknowledgements.

Fuzzing should run in CI with deterministic seeds plus rotating random seeds for nightly jobs.

## Open Questions

- Whether `untrusted_local` should be enabled by default.
- Whether extension signatures are mandatory in v1 or policy-configurable.
- Whether API tokens are needed for local RPC channel or if socket isolation is sufficient.
- Whether Android should permit third-party runtime execution or only first-party packaged extensions in v1.

## Delivery Approach

1. Finalize manifest schema and protocol error model.
2. Implement host-side schema validator and capability gate only.
3. Build one first-party reference extension for test coverage.
4. Wire CI contract tests and initial fuzz harness.
5. Validate Android profile behavior with restricted lifecycle tests.
6. Decide on public SDK timing after operational feedback.
