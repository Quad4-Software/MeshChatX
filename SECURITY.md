# Security Policy

## Contact Information

If you discover a security vulnerability or have concerns about the security of Reticulum MeshChatX, please contact the lead developer using the following methods in order of preference:

1. **LXMF**: `7cc8d66b4f6a0e0e49d34af7f6077b5a`

## Security Overview

Reticulum MeshChatX is designed with a high degree of security in mind, leveraging multiple layers of protection and modern security practices.

We follow the [Electron Best Security Practices](https://www.electronjs.org/docs/latest/tutorial/security)

### Core Security Features

- **ASAR Integrity Validation**: Utilizes Electron 39 features to protect the application against tampering.
- **Backend Binary Verification**: Generates a SHA-256 manifest of the unpacked Python backend during build and verifies it on every startup.
- **Data-at-Rest Integrity Monitoring**: Snapshots the state of identities and database files on clean shutdown and warns if they were modified while the app was closed.
- **CSP Hardening**: Multi-layered Content Security Policy protection across the entire application stack.
- **Hardened Electron Environment**: Hardened security by disabling `runAsNode` and `nodeOptions` environment variables via Electron Fuses.
- **Rootless Docker Images**: Support for running in restricted environments with rootless container images.

### Automated Security Measures

The project employs continuous security monitoring and testing:

- **Security Scanning**: Automated daily scans using OSV-Scanner and Trivy for container image vulnerabilities.
- **Pinned Actions**: All CI/CD workflows use pinned actions with full URLs to forked, vetted actions hosted on our Gitea instance (`git.quad4.io`) to prevent supply chain attacks.
- **Extensive Testing & Fuzzing**: Comprehensive backend benchmarking suite with high-precision timing, memory delta tracking, and extreme stress modes to ensure stability and prevent resource exhaustion.
- **Linting & Code Quality**: Strict linting rules and static analysis are enforced on every push.
