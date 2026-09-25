# Verifying downloads

Every release ships the verification pieces alongside the binaries. Pick
the level you want - none of them are mandatory for normal use, all of
them are additive confidence.

## What you get per release

- The binaries and packages themselves.
- `checksums.txt` plus per-artifact `*.sha256` where applicable - plain
  SHA256 checksums.
- `*.intoto.jsonl` - SLSA v3 build provenance tying the artifact to the
  GitHub workflow that built it.
- `*.cosign.bundle` - repository-managed signing-key attestations (when
  signing secrets are configured for that release).
- `sbom.cyclonedx.json` - a CycloneDX SBOM of what is inside.
- `openvex.json` - maintainer triage notes for scanner findings.

## 1. Checksums

Always available, works offline:

```bash
sha256sum -c checksums.txt --ignore-missing
```

Or verify a single artifact:

```bash
sha256sum meshchatx-linux-x64.AppImage
# compare against the published .sha256 / checksums.txt entry
```

## 2. SLSA provenance

The `*.intoto.jsonl` bundles prove the artifact came from this
repository's release workflow. Use the official `slsa-verifier`:

```bash
slsa-verifier verify-artifact \
    meshchatx-linux-x64.AppImage \
    --provenance-path <artifact>.intoto.jsonl \
    --source-uri github.com/Quad4-Software/MeshChatX \
    --source-tag v4.9.1
```

A passing result means: the binary was built by GitHub Actions from the
tagged source, on an ephemeral runner - not by a random upload.

## 3. cosign attestations

When `.cosign.bundle` files are present, verify them against the
repository's public key. `cosign.pub` is committed in this repo so no
out-of-band key hunt is needed:

```bash
cosign verify-blob-attestation \
    --bundle <artifact>.cosign.bundle \
    --key cosign.pub \
    --insecure-ignore-tlog=true \
    <artifact>
```

`--insecure-ignore-tlog=true` is required because repository-key bundles
are deliberately built without a Rekor transparency-log entry. The
signature and the SLSA predicate are still checked against the public key.

## 4. Scan the SBOM yourself

The CycloneDX SBOM feeds standard scanners:

```bash
grype sbom:sbom.cyclonedx.json
# with maintainer triage applied:
grype sbom:sbom.cyclonedx.json --vex openvex.json
```

## Expected failures

- No `.cosign.bundle` for older or unsigned-channel releases: only some
  release channels have signing secrets configured. The checksums and
  SLSA provenance still apply.
- slsa-verifier "no matching artifact": download the binary under the
  exact release name first - the provenance binds the file name.
- A failed `sha256sum` after a partial re-download: retry the download
  before assuming tampering; interrupted fetches are the usual cause.

## See also

- `SECURITY.md` in the repository for the trust model behind these
  signatures (key rotation, Rekor policy, what each artifact proves).
- **Building from source and packaging** for building the same artifacts
  locally instead of trusting the download.
