#!/usr/bin/env bash
# APT packages needed for Linux Electron packaging (AppImage, deb, rpm, apk) on Debian/Ubuntu or in docker/Dockerfile.build (root).
set -euo pipefail

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

_HOST_ARCH="$(uname -m)"
if [ "$_HOST_ARCH" = "x86_64" ]; then
    run_priv dpkg --add-architecture i386 || true
fi
run_priv apt-get update -y

_PKGS=(patchelf libopusfile0 espeak-ng zip rpm elfutils fakeroot file)
if [ "$_HOST_ARCH" = "x86_64" ]; then
    _PKGS+=("libc6:i386" "libstdc++6:i386")
fi
run_priv apt-get install -y --no-install-recommends "${_PKGS[@]}"
