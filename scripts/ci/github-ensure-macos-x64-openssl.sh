#!/usr/bin/env bash
# Ensure x86_64 openssl@3 dylibs exist for the darwin-x64 cx_Freeze slice.
# cryptography in .venv-x64 records /usr/local/opt/openssl@3/lib/libssl.3.dylib.
# A warm venv cache skips brew, so freeze then copies a path that is not on the runner.
#
# SPDX-License-Identifier: 0BSD
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "github-ensure-macos-x64-openssl: skipping (not macOS)" >&2
    exit 0
fi

_LIBSSL="/usr/local/opt/openssl@3/lib/libssl.3.dylib"
if [[ -f "$_LIBSSL" ]]; then
    echo "github-ensure-macos-x64-openssl: ${_LIBSSL} present" >&2
    exit 0
fi

bash "$(dirname "$0")/github-ensure-macos-x86-64-homebrew.sh"

echo "github-ensure-macos-x64-openssl: installing openssl@3 for cx_Freeze" >&2
export NONINTERACTIVE=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_AUTO_UPDATE=1
if ! arch -x86_64 /usr/local/bin/brew install openssl@3; then
    arch -x86_64 /usr/local/bin/brew reinstall openssl@3
fi
test -f "$_LIBSSL"
