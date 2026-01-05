# Security Policy

## Contact Information

If you discover a security vulnerability or have concerns about the security of Reticulum MeshChatX, please contact the lead developer using the following methods in order of preference:

1. **LXMF**: `7cc8d66b4f6a0e0e49d34af7f6077b5a` (Ideally)
2. **XMPP**: `ivan@chat.quad4.io`
3. **Email**: `ivan@quad4.io`

## Security Overview

Reticulum MeshChatX is designed with a high degree of security in mind, leveraging multiple layers of protection and modern security practices. Detailed security enhancements are documented in the [CHANGELOG.md](CHANGELOG.md) and [README.md](README.md).

### Core Security Features

- **ASAR Integrity Validation**: Utilizes Electron 39 features to protect the application against tampering.
- **Backend Binary Verification**: Generates a SHA-256 manifest of the unpacked Python backend during build and verifies it on every startup.
- **Data-at-Rest Integrity Monitoring**: Snapshots the state of identities and database files on clean shutdown and warns if they were modified while the app was closed.
- **3-Layer CSP Hardening**: Multi-layered Content Security Policy protection across the entire application stack:
    1. **Backend Server CSP**: Applied via security middleware to all HTTP responses.
    2. **Electron Session CSP**: Shell-level fallback CSP applied via `webRequest.onHeadersReceived`.
    3. **Loading Screen CSP**: Bootloader CSP defined in HTML meta tags.
- **Hardened Electron Environment**: Hardened security by disabling `runAsNode` and `nodeOptions` environment variables via Electron Fuses.
- **Rootless Docker Images**: Support for running in restricted environments with rootless container images.

### Automated Security Measures

The project employs continuous security monitoring and testing:

- **Security Scanning**: Automated daily scans using OSV-Scanner and Trivy for container image vulnerabilities.
- **Pinned Actions**: All CI/CD workflows use pinned actions with full URLs to forked, vetted actions hosted on our Gitea instance (`git.quad4.io`) to prevent supply chain attacks.
- **Extensive Testing & Fuzzing**: Comprehensive backend benchmarking suite with high-precision timing, memory delta tracking, and extreme stress modes to ensure stability and prevent resource exhaustion.
- **Linting & Code Quality**: Strict linting rules and static analysis are enforced on every push.

