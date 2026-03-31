# Security Policy

## Contact Information

If you discover a security vulnerability or have concerns about the security of Reticulum MeshChatX, please contact the lead developer using the following methods in order of preference:

1. **LXMF**: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

## Security Overview

Reticulum MeshChatX is designed with a high degree of security and privacy in mind, leveraging multiple layers of protection and modern security practices.

We follow the [Electron Best Security Practices](https://www.electronjs.org/docs/latest/tutorial/security).

### Exposing to the public internet (with authentication)

MeshChatX is primarily intended for **local or trusted networks** (for example behind a home router or VPN). Putting the HTTP(S) UI on the **public internet** is **not recommended**: you enlarge the attack surface (credential stuffing, TLS and certificate management, reverse-proxy misconfiguration, automated scanning, and denial-of-service against the single-node service).

If you still choose to expose it, **enable authentication**, use **HTTPS** (valid certificates on the public name), restrict **who can reach the port** where possible (firewall allowlists, VPN, or a reverse proxy with additional controls), and keep the app **updated**. The application includes **defence-in-depth** for the login and initial-setup endpoints: **per-IP rate limiting**, **lockout** after repeated failed passwords from an address (with **trusted client** recognition after a successful login so your own browsers are less likely to be blocked during broad attacks), **logging** of access attempts (IP, User-Agent, path, time) inspectable under **Debug Logs → Access attempts**, and session cookies configured as **HttpOnly** with **SameSite=Lax**. None of this removes the inherent risks of a public-facing service; it only reduces some abuse and accident scenarios.

### Core Security Features

- **ASAR Integrity Validation**: Utilizes Electron 39 features to protect the application against tampering.
- **Backend Binary Verification**: Generates a SHA-256 manifest of the unpacked Python backend during build and verifies it on every startup.
- **Data-at-Rest Integrity Monitoring**: Snapshots the state of identities and database files on clean shutdown and warns if they were modified while the app was closed.
- **CSP Hardening**: Multi-layered Content Security Policy protection across the entire application stack.
- **Hardened Electron Environment**: Hardened security by disabling `runAsNode` and `nodeOptions` environment variables via Electron Fuses.
- **Rootless Docker Images**: Support for running in restricted environments with rootless container images.

### Automated Security Measures

The project employs continuous security monitoring and testing:

- **Security Scanning**: `.gitea/workflows/scan.yml` runs on a weekly schedule and on pushes to `master` and `dev`. It installs frontend dependencies and runs **`pnpm audit`** (high severity threshold), **Trivy filesystem** vulnerabilities (`trivy fs --exit-code 1`), and **Trivy Dockerfile** misconfiguration (`trivy config --exit-code 1 Dockerfile`). The **Docker** workflow runs **Trivy** on the built image (`trivy image`) separately from that job.
- **Auth and path-safety tests**: Pytest covers HTTP **401** on protected `/api/*` when `auth_enabled` is on and no session (`tests/backend/test_notifications.py`), **ValueError** on backup/snapshot delete paths that escape storage (`tests/backend/test_security_path_and_backup.py`), and **schema upgrade** from version **N-1** (`tests/backend/test_schema_migration_upgrade.py`). Database **backup/restore** round-trips are covered in `tests/backend/test_database_snapshots.py`. Login and setup **rate limiting**, **lockout**, and **access attempt** logging are covered in `tests/backend/test_access_attempts_dao.py` and `tests/backend/test_access_attempts_enforcement.py` (including Hypothesis and HTTP smoke tests).
- **CI**: On pushes and pull requests, **`pip-audit`** (Python) and **`pnpm audit`** run against the resolved dependency trees.
- **Pinned Actions**: CI/CD workflows use pinned actions with full URLs to forked, vetted actions hosted on our Gitea instance (`git.quad4.io`) where an action is used at all.
- **Extensive Testing & Fuzzing**: Backend benchmarking and stress coverage to reduce instability and resource-exhaustion risks.
- **Linting & Code Quality**: Linting and static analysis run on CI paths.

## Release provenance

Tagged releases are built from `.gitea/workflows/build.yml`. Release assets include SHA256 sidecars (`.sha256` files next to each file) and a CycloneDX SBOM (`sbom.cyclonedx.json`). When the repository secret **`COSIGN_PRIVATE_KEY`** is set (PEM from `cosign generate-key-pair`, with **`COSIGN_PASSWORD`** if the key is encrypted), the workflow also produces **SLSA v1**-style cosign bundle files (`*.cosign.bundle`) next to each attested artifact.

Attestations are uploaded to the **Sigstore public transparency log (Rekor)** by default. The build runner must be able to reach the Rekor endpoint (default `https://rekor.sigstore.dev`; override with **`COSIGN_REKOR_URL`** if you use another instance).

Commit the cosign **public** key at the **repository root** as **`cosign.pub`** so others can verify without hunting for the key out of band.

### Signing key rotation

Rotate the signing key when it may be compromised or on an internal schedule (for example annually). Generate a new key pair, replace the **`COSIGN_PRIVATE_KEY`** (and password) secret in Gitea, and replace **`cosign.pub`** in the repository with the new public key. Releases built **before** rotation remain verifiable using the **old** public key kept alongside the download or in git history; document which key applies to which release tag if you maintain multiple keys.

## Verifying releases

Install **[cosign](https://docs.sigstore.dev/cosign/installation/)** for bundle verification. You need the **`cosign.pub`** file from the repository (same tag or `master` as the release you are checking).

### SHA256 checksums

Each released file has a sidecar `filename.sha256` containing the output of `sha256sum` (hex digest and filename). After downloading both files into the same directory:

```bash
sha256sum -c path/to/your-artifact.sha256
```

On macOS without GNU coreutils, compare the printed digest to `shasum -a 256 your-artifact` or use `openssl dgst -sha256 your-artifact`.

### Cosign attestation (SLSA v1 bundle)

From the repository root (so `scripts/ci/verify-release-attestation.sh` resolves), or with **`COSIGN_PUBLIC_KEY`** pointing at your copy of `cosign.pub`:

```bash
sh scripts/ci/verify-release-attestation.sh path/to/your-artifact path/to/your-artifact.cosign.bundle
```

This checks the signature and **Rekor** transparency-log inclusion for the attestation. If you intentionally use a private Sigstore deployment, set the same **`COSIGN_REKOR_URL`** (and any other Sigstore env vars) your builder used.

### Container images

Published images are built in `.gitea/workflows/docker.yml`. **OCI image cosign signing is not wired in that workflow yet.** Until it is, treat digest pinning as the main integrity check: pull or reference the image by **`@sha256:<digest>`** from a trusted manifest or registry UI, and optionally run **`trivy image`** against that digest. When cosign image signing is added, verification will look like:

```bash
cosign verify --key cosign.pub <registry>/<image>@sha256:<digest>
```

(Exact flags may depend on keyless versus key-based signing; follow the release notes when signing lands.)
