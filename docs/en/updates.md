# Updates

MeshChatX can check for and install signed updates. The whole feature is
off by default. With default settings the app makes no update-related
network requests, registers no RNS destination, and announces nothing.

Current builds ship the updater disabled while the staged rollout is
finalized. The settings section is hidden and staged apply is a no-op.
Set `MESHCHATX_UPDATE_ROLLOUT=1` in the environment to exercise it
during development.

This page describes what is contacted, what is trusted, and how to pin
your own signer and mirrors.

## What is contacted, and when

Nothing happens until you enable updates in Settings, under Maintenance,
in the Updates section. The section shows exactly what will be contacted
before you turn it on:

- The mirror list. Defaults are the GitHub repository, the Forgejo
  mirror, and the project CDN. You can replace them with your own HTTPS
  mirrors.
- The RNS destination `meshchatx.update`, used only if RNS transport is
  selected or reached through auto mode.
- The trusted signer hashes used to verify manifests.

Once enabled, a manual "Check for updates" fetches a small signed
manifest. If you also enable auto check, the app repeats that check on
your interval (default 24 hours, minimum 6, with jitter so installs do
not synchronize). Auto download is a separate opt-in and is skipped on
slow links.

A no-change check is cheap: a few hundred bytes over HTTP (a 304 against
the stored ETag) or a tiny probe over RNS that carries only the hash of
the last accepted manifest.

## Trust model

The signature is the only trust anchor. Mirrors, the CDN, GitHub,
Forgejo, RNS peers, and peer relays are all untrusted transports. They
can withhold or corrupt data, but they cannot forge an update.

The manifest is a compact msgpack document inside a signed envelope
(rnid-compatible RSG). It carries the channel, version, issue and expiry
timestamps, minimum supported version, and per-artifact name, size,
SHA-256, platform, architecture, kind, and blockmap hash. The client
rejects:

- unsigned, malformed, or tampered manifests
- manifests signed by an identity whose hash is not pinned
- manifests for a different channel than this install
- expired manifests or manifests issued in the future
- versions that are not newer than the installed version (downgrade),
  unless you explicitly allow it
- manifests older than the last accepted one for that channel
  (high-water mark, persisted locally)
- artifacts over your size cap, with unsafe names, or whose downloaded
  bytes fail the SHA-256 and size check

Artifacts download over HTTPS Range requests or RNS byte ranges, then
verify against the signed manifest before staging. Blockmaps let the
client reuse unchanged blocks from the installed copy, so a small
release delta costs only the changed ranges. A whole-file SHA-256 check
still runs after assembly. On mismatch the client retries once as a
full download and discards on a second failure.

## Clearnet and RNS

Transport preference is auto, clearnet only, or RNS only. Auto tries
clearnet mirrors first, then known RNS update destinations.

Over RNS the client uses a throwaway ephemeral identity for update
links. It never uses your main LXMF or MeshChat identity and never
reuses your normal delivery destination. Update links are low priority
and rate limited (default 256 kbit/s, configurable) so chat traffic is
not starved. When a path is unknown the client backs off instead of
flooding path requests.

You can seed RNS destinations by hash in settings, or let the client
learn them from `meshchatx.update` announces.

## Peer relay

Peer relay is off by default. When you enable it, a node that has
verified a manifest and staged artifact can announce itself on
`meshchatx.update` and serve manifest probes, sizes, and byte ranges to
other peers. This is store-and-forward friendly: a peer can fetch an
update through another node when it has no clearnet path.

Peers are untrusted. Receivers verify the signed manifest and artifact
checksums themselves, so a malicious relay can only withhold data. The
server side only serves bytes whose SHA-256 appears in a manifest the
node itself verified, and it rate limits and size caps what it serves.
Files dropped into the seed directory (for example via sneakernet or
RNS filesync) are indexed only when their hash matches a verified
manifest.

## Low-bandwidth guard

Automatic downloads are skipped on slow links. The heuristic looks at
the bitrates of your online RNS interfaces (LoRa, serial, packet radio
and similar links report well under the default 1 Mbit/s threshold,
configurable). If every available path is slow, auto download waits. You
can always start a manual download. Clearnet transport over a normal
interface is unaffected.

## Applying updates

Verified artifacts stage into private update storage with an atomic
`pending.json` marker. Nothing applies mid-session.

- `manual` (default): the UI shows the staged file and offers to reveal
  it. Self-apply covers AppImage installs (shell swap and relaunch) and
  portable installs marked `updatable.txt` by packaging (atomic install
  dir swap and relaunch).
- `on_restart`: the desktop shell applies the staged artifact before
  starting the backend on the next launch. Only kinds the shell can
  apply swap automatically, the rest report as staged.

Windows MSI/NSIS installers, macOS `.dmg`, and `deb`/`rpm` packages
stage for manual install with instructions. The package manager or
installer owns those files. Container and flatpak installs are
external: the client reports the new version and tells you to pull the
image or run `flatpak update`. Rollback keeps the previous AppImage as
`.bak`, or the previous install directory as `<dir>.bak`.

## Offline and manual verification

Everything works disconnected. You can verify a file you received by
sneakernet or RNS filesync: place the artifact and its
`<file>.manifest.rsm` sidecar (or rely on a previously stored manifest)
and use "Apply update file" in the settings section. The file must
match a signed manifest artifact by name or SHA-256, size, and hash.

## Signer pinning and custom mirrors

The default signer pin covers the project release identity. It is only
a default: you can replace it with your own signer hashes in settings,
one per line, 32 hex characters for an identity hash or 64 for a full
public-key hash. When you set signer hashes, the default is replaced, so
list every signer you trust.

Custom mirrors are HTTPS base URLs, one per line. Plain HTTP is accepted
only for loopback addresses, which exists for local testing. Mirrors
must not embed credentials.

## What is not collected

There is no telemetry, analytics, crash upload, or installation
identifier. Requests carry a constant `MeshChatX-Updater` user agent, no
cookies, and no query parameters. The client downloads the whole signed
manifest and selects the artifact locally, so mirrors learn nothing
about your platform beyond the bytes they serve. RNS update links use an
ephemeral identity that is never announced as your main identity.

## Environment overrides

- `MESHCHATX_UPDATE_DISABLED=1` disables the whole feature even when
  enabled in settings.
- `MESHCHATX_UPDATE_SIGNER` pins a single signer hash.
- `MESHCHATX_UPDATE_MIRRORS` overrides the mirror list
  (comma-separated base URLs).
- `MESHCHATX_UPDATE_RNS_SEEDS` seeds RNS destination hashes
  (comma-separated 32-hex hashes).
