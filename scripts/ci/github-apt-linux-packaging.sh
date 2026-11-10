#!/usr/bin/env bash
# APT packages needed for Linux Electron packaging (AppImage, deb, rpm, apk) on Debian/Ubuntu or in docker/Dockerfile.build (root).
set -euo pipefail

# shellcheck source=priv.sh disable=SC1091
. "$(dirname "$0")/priv.sh"

_HOST_ARCH="$(uname -m)"
if [ "$_HOST_ARCH" = "x86_64" ]; then
    run_priv dpkg --add-architecture i386 || true
fi

_PKGS=(patchelf libopusfile0 espeak-ng zip rpm elfutils fakeroot file libgtk-4-dev libwebkitgtk-6.0-dev)
if [ "$_HOST_ARCH" = "x86_64" ]; then
    _PKGS+=("libc6:i386" "libstdc++6:i386")
fi

_APT_OPTS=(-o Acquire::Retries=3)
for _attempt in 1 2 3; do
    if run_priv apt-get "${_APT_OPTS[@]}" update -y \
        && run_priv apt-get "${_APT_OPTS[@]}" install -y --no-install-recommends "${_PKGS[@]}"; then
        break
    fi
    if [ "$_attempt" -eq 3 ]; then
        exit 1
    fi
    echo "apt attempt $_attempt failed; retrying" >&2
    sleep 15
done
