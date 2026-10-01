# Updates

MeshChatX supports signed, channel-based updates delivered through the
project CDN. Every update decision is anchored on a signed manifest, not
on HTTPS alone: the manifest carries a Reticulum identity signature, and
the app verifies it against the pinned release signer before trusting
anything inside.

## Channels

Updates follow the channel baked into your build:

- `stable` builds track `release/` on the CDN.
- `beta` builds track `beta/`.
- `testing` builds track `testing/`.
- `local` (self-built) installs never auto-check; the section shows as
  disabled.

## Automatic check

In Settings, under the Maintenance tab, open **Updates** and press
**Check for updates**. The app fetches
`<cdn>/<track>/latest.rsm`, verifies the signature and signer hash,
compares versions, and lists the artifacts that match your platform and
architecture. Anything that fails verification is rejected before it is
ever downloaded.

## Download and apply

Press **Download and stage**. The app downloads the matching artifact to a
temporary file, re-verifies its size and SHA-256 against the signed
manifest, then moves it to a pending folder. For AppImage builds you get
a **Restart to apply** button: the desktop shell re-hashes the staged
file once more, swaps it over the running image (keeping the previous
image as a `.bak` rollback copy), and relaunches.

For packages the app cannot apply itself (deb, rpm, flatpak, wheel, pyz,
APK), the staged file is verified and left ready with install
instructions. Use **Show file** to open its folder.

## Manual update files

If you downloaded an update file yourself (from GitHub Releases or the
CDN), use **Apply update file** in the same section. The app hashes the
file and accepts it only if its SHA-256, size, platform and architecture
exactly match an entry in the *currently published signed manifest*.
This means:

- The app must be able to reach the CDN once to fetch the signed
  manifest. Verification is cryptographic; the network answer cannot be
  forged without the release private key.
- A stale file for an older release is rejected once a newer manifest is
  live.
- A file that is not listed in the manifest is rejected even if it came
  from a trusted-looking source.

## Security model

- The manifest signature is the trust anchor. A hostile CDN or MITM can
  withhold or delay updates, but cannot forge or alter a manifest.
- Artifact integrity is enforced twice: at download time against the
  signed manifest, and again at apply time before any file is replaced.
- `minimum_version` in the manifest is enforced as an anti-rollback
  floor.
- Artifact paths in the manifest must be relative paths inside the tag
  directory; traversal and absolute paths are rejected.
- Environment overrides for debugging:
  `MESHCHATX_UPDATE_BASE_URL` (CDN base), `MESHCHATX_UPDATE_SIGNER`
  (hex signer hash), `MESHCHATX_UPDATE_DISABLED=1`.
