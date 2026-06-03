#!/usr/bin/env bash
# Rust cross-target for x86_64 macOS wheels built on Apple Silicon CI runners.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    exit 0
fi

if ! command -v rustup >/dev/null 2>&1; then
    echo "Installing rustup (minimal stable) for macOS x86_64 cross-builds." >&2
    curl -sSfL https://sh.rustup.rs -o /tmp/rustup-init.sh
    sh /tmp/rustup-init.sh -y --profile minimal --default-toolchain stable
    rm -f /tmp/rustup-init.sh
fi

if [[ -d "${HOME}/.cargo/bin" ]]; then
    if [[ -n "${GITHUB_PATH:-}" ]]; then
        echo "${HOME}/.cargo/bin" >> "${GITHUB_PATH}"
    else
        export PATH="${HOME}/.cargo/bin:${PATH}"
    fi
fi
if [[ -f "${HOME}/.cargo/env" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/.cargo/env"
fi

rustup target add x86_64-apple-darwin
rustup show
