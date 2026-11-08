#!/usr/bin/env bash
# Ensure named CLI tools exist on PATH for CI steps that run outside the
# dependency bootstrap (e.g. CodeQL autobuild helpers). On self-hosted
# runners without root, missing tools are fetched as user-space Arch
# packages under $HOME/.local/meshchatx-ci/syslibs.
#
# Usage: ensure-user-tools.sh <tool> [tool...]
#   Tool names map to same-named Arch packages; override with
#   TOOL_PKG_<name>=<pkg> env vars for exceptions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# shellcheck source=scripts/ci/user-space-pkgs.sh
. "$(dirname "$0")/user-space-pkgs.sh"

[[ $# -gt 0 ]] || { echo "usage: $0 <tool> [tool...]" >&2; exit 2; }

missing=0
for tool in "$@"; do
    if command -v "${tool}" >/dev/null 2>&1; then
        continue
    fi
    pkg_var="TOOL_PKG_$(printf '%s' "${tool}" | tr 'a-z-' 'A-Z_')"
    pkg="${!pkg_var:-${tool}}"
    if fetch_arch_pkg "${pkg}"; then
        link_syslib_bins
    fi
    if ! command -v "${tool}" >/dev/null 2>&1; then
        echo "ensure-user-tools: could not provide ${tool} (tried package ${pkg})" >&2
        missing=1
    fi
done

exit "${missing}"
