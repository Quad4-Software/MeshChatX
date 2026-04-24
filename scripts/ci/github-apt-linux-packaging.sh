#!/usr/bin/env bash
# APT packages needed for Linux Electron packaging (AppImage, deb, rpm) on Debian/Ubuntu or in Dockerfile.build (root).
set -euo pipefail

# shellcheck source=scripts/ci/priv.sh
. "$(dirname "$0")/priv.sh"

run_priv dpkg --add-architecture i386 || true
run_priv apt-get update -y
run_priv apt-get install -y --no-install-recommends \
    patchelf \
    libopusfile0 \
    espeak-ng \
    zip \
    rpm \
    elfutils \
    fakeroot \
    file \
    libc6:i386 \
    libstdc++6:i386
