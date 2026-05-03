#!/usr/bin/env bash
# Ensure an x86_64 (Rosetta) Homebrew exists at /usr/local/bin/brew.
# GitHub-hosted Apple Silicon runners ship /opt/homebrew only; cx_Freeze universal
# x64 slices need x86_64 libraries from /usr/local (see codec2, libyaml steps).
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    exit 0
fi

if [[ -x /usr/local/bin/brew ]]; then
    exit 0
fi

echo "github-ensure-macos-x86-64-homebrew: installing Homebrew under Rosetta into /usr/local (one-time on this runner)" >&2
export NONINTERACTIVE=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_AUTO_UPDATE=1
arch -x86_64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
test -x /usr/local/bin/brew
