#!/usr/bin/env bash
# flatpak-bundler installs runtimes with flatpak --user and a bare ref; that only works
# once the Flathub remote exists (see @malept/flatpak-bundler ensureRef).
set -euo pipefail

if ! command -v flatpak >/dev/null 2>&1; then
    echo "flatpak is not installed." >&2
    exit 1
fi

flatpak --user remote-add --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
