# Security Policy

## Reporting a vulnerability

If you believe you have found a **security vulnerability** in MeshChatX, please report it privately so it can be fixed before wider disclosure.

**Preferred contact (in order):**

1. **LXMF**: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

Include enough detail to reproduce or understand the issue (what version or build you used, what you expected, what happened). Do not open a public issue for unfixed vulnerabilities.

**Not security (legal, licensing, general questions):** `legal@quad4.io` or see [`LEGAL.md`](LEGAL.md).

---

MeshChatX is meant to be used on **trusted networks** (for example at home, on a LAN, or over a VPN you control).

If you still put the web interface on the **public internet**, you accept much higher risk (password guessing, misconfigured TLS or proxies, automated scanning, and overload of a single-node app). If you must expose it: **turn on authentication**, use **HTTPS** with a valid certificate for the public name, **restrict who can reach the port** (firewall, VPN, or a reverse proxy with sensible rules), and **keep the application updated**. `/robots.txt` with `Disallow: /` is only a hint to crawlers, not protection.

The app adds **rate limiting** and **lockout** for failed logins, **logging** of access attempts (viewable under Debug Logs), and **HttpOnly** session cookies with **SameSite=Lax**. These measures reduce some abuse; they do not make a public deployment “safe by default.”

### What you download should match what we built

Official release binaries and packages are built in **automation on GitHub**, not by hand on a laptop. Each tagged release is intended to ship:

- **Installable files** (for example AppImage, `.deb`, Windows and macOS installers, Python wheels) from that tag.
- A **software bill of materials (SBOM)** in CycloneDX form (`sbom.cyclonedx.json`) where the Linux release pipeline produces it, so you or your tools can see what went into the build.
- **Signed provenance** files (`*.intoto.jsonl`) that cryptographically tie those binaries to the **same source repository and tag** on GitHub, using the industry [SLSA](https://slsa.dev/) approach and the [slsa-github-generator](https://github.com/slsa-framework/slsa-github-generator) project. New tags also get a **draft** GitHub release so assets can be reviewed before the release is published.

**Docker images** published to GitHub Container Registry are built in CI and **signed with Cosign (keyless / Sigstore)** so the signature can be checked against the image digest.

**Optional extra signatures:** If you see `*.cosign.bundle` files next to a binary, those are additional attestations from a **repository-managed signing key** (when the project enables it). They are separate from the SLSA `*.intoto.jsonl` files; either or both may be present depending on configuration.

### Practical tips

- Prefer **official download pages** or **GitHub Releases** for your copy of the app.
- For Docker, prefer an image referenced by **digest** (`@sha256:…`) once you trust a given build, not only by a moving tag.
- If something claims to be MeshChatX but does not match published checksums or verification steps, treat it as **untrusted**.

---

## For security professionals and auditors

### Product controls (high level)

- **Desktop (Electron):** Packaging and runtime follow [Electron security guidance](https://www.electronjs.org/docs/latest/tutorial/security); ASAR integrity and hardened defaults (for example fuses that reduce risky Node integration) are part of the shipped app.
- **Backend:** A SHA-256 manifest of the bundled Python backend is checked on startup to detect tampering with the on-disk payload.
- **Data at rest:** The application can detect unexpected changes to sensitive files between runs (integrity monitoring around identities and database state).
- **Web surface:** Content Security Policy is applied in depth across the stack.
- **Containers:** Images are intended to run **without root** inside the container where the platform supports it.

### Build, supply chain, and transparency

- **CI:** Automated pipelines (hosted on GitHub Actions) run dependency and configuration scanning (including **Trivy** and **pip-audit** on relevant paths), build checks, and security-relevant automated tests (authentication, path safety on dangerous operations, schema upgrades, backup/restore, rate limiting and access logging, and related areas).
- **Action pinning:** Third-party GitHub Actions are referenced with **pinned commit SHAs** in workflow definitions to reduce unexpected upgrades.
- **Releases:** Tagged release artifacts for Linux, Windows, and macOS are produced in CI. **SLSA Build Level 3–style provenance** for those artifacts is generated via the **generic** SLSA GitHub generator (`generator_generic_slsa3.yml` at release **v2.1.0**), which satisfies the **isolated builder and signed provenance** expectations for that tier; **distribution** (draft releases, mirrors) and **consumer verification** remain your operational controls, as described in upstream SLSA documentation.
- **Transparency logs:** Many Sigstore flows write to the **public Rekor** log (`https://rekor.sigstore.dev` by default). **Repository-key** `*.cosign.bundle` files next to release artifacts are built **without** a Rekor entry; with **Cosign v3+**, verify them against `cosign.pub` using `cosign verify-blob-attestation` and `--insecure-ignore-tlog=true` (signature and predicate are still checked against the public key). Private-repo or air-gapped policies may require different Sigstore settings; operators should align `COSIGN_REKOR_URL` and related variables with their own governance.
- **Cosign public key:** When repository key-based signing is used, the **public** key is published in-repo as `cosign.pub` so verifiers do not need a separate out-of-band key hunt. **Key rotation:** replace the GitHub secret holding the private key and update `cosign.pub` in the repository; older releases remain verifiable with the key that was current at build time.
