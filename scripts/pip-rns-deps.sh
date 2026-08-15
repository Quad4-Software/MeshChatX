#!/usr/bin/env bash
# SPDX-License-Identifier: 0BSD
# Install rns / lxmf / lxst into the project uv environment via pip-rns (rngit).
set -euo pipefail

usage() {
    cat <<'EOF'
Install Reticulum Python packages over RNS using pip-rns.

Requires a working Reticulum stack (rns already importable enough for mesh
pathfinding), git, and git-remote-rns / rngit tooling. First-time bootstrap of
rns itself still needs clearnet, a local wheel, or an existing install.

Usage:
  bash scripts/pip-rns-deps.sh [options] [package ...]

Options:
  -h, --help           Show this help
  --from-release       Prefer rngit release wheels (--from-release)
  --ref REF            Pass --ref REF to each pip-rns install
  --verify IDENTITY    Require release signature (--verify)
  --editable           Editable install
  --use-cache          Pass --use-cache to pip-rns
  --skip-ensure        Do not try to install pip-rns if missing
  --dry-run            Print commands only

Default packages: rns lxmf lxst

Environment:
  PIP_RNS_CONFIG              Config dir with aliases (default: scripts/pip-rns)
  MESHCHATX_PIP_RNS_FROM_RELEASE  Set to 1 to imply --from-release
  MESHCHATX_PIP_RNS_REF       Default --ref when not passed on CLI
  MESHCHATX_PIP_RNS_VERIFY    Default --verify identity hash
  MESHCHATX_PIP_RNS_PACKAGES  Space-separated package list override
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

CONFIG_DIR="${PIP_RNS_CONFIG:-${ROOT_DIR}/scripts/pip-rns}"
export PIP_RNS_CONFIG="${CONFIG_DIR}"

FROM_RELEASE=0
REF="${MESHCHATX_PIP_RNS_REF:-}"
VERIFY="${MESHCHATX_PIP_RNS_VERIFY:-}"
EDITABLE=0
USE_CACHE=0
SKIP_ENSURE=0
DRY_RUN=0
PACKAGES=()

if [[ "${MESHCHATX_PIP_RNS_FROM_RELEASE:-}" == "1" ]]; then
    FROM_RELEASE=1
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --from-release)
            FROM_RELEASE=1
            shift
            ;;
        --ref)
            REF="${2:-}"
            shift 2
            ;;
        --verify)
            VERIFY="${2:-}"
            shift 2
            ;;
        --editable)
            EDITABLE=1
            shift
            ;;
        --use-cache)
            USE_CACHE=1
            shift
            ;;
        --skip-ensure)
            SKIP_ENSURE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            PACKAGES+=("$1")
            shift
            ;;
    esac
done

if [[ ${#PACKAGES[@]} -eq 0 ]]; then
    if [[ -n "${MESHCHATX_PIP_RNS_PACKAGES:-}" ]]; then
        # shellcheck disable=SC2206
        PACKAGES=(${MESHCHATX_PIP_RNS_PACKAGES})
    else
        PACKAGES=(rns lxmf lxst)
    fi
fi

if [[ ! -f "${CONFIG_DIR}/aliases" ]]; then
    echo "Missing aliases file: ${CONFIG_DIR}/aliases" >&2
    exit 1
fi

run_cmd() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf '+'
        printf ' %q' "$@"
        printf '\n'
        return 0
    fi
    "$@"
}

ensure_pip_rns() {
    if command -v pip-rns >/dev/null 2>&1; then
        return 0
    fi
    if [[ "${SKIP_ENSURE}" -eq 1 ]]; then
        echo "pip-rns not found on PATH (and --skip-ensure was set)" >&2
        exit 1
    fi
    echo "pip-rns not found, installing into project environment with uv..." >&2
    if command -v uv >/dev/null 2>&1; then
        run_cmd uv pip install pip-rns
    else
        run_cmd python3 -m pip install pip-rns
    fi
    if ! command -v pip-rns >/dev/null 2>&1; then
        if command -v uv >/dev/null 2>&1; then
            PIP_RNS_BIN=(uv run pip-rns)
            return 0
        fi
        echo "pip-rns still not on PATH after install" >&2
        exit 1
    fi
}

PIP_RNS_BIN=(pip-rns)
if [[ "${DRY_RUN}" -eq 1 ]]; then
    :
else
    ensure_pip_rns
fi

if [[ "${DRY_RUN}" -eq 0 ]]; then
    echo "Note: Installing packages over RNS can be slow and use significant mesh bandwidth." >&2
fi

EXTRA_ARGS=()
if [[ "${FROM_RELEASE}" -eq 1 ]]; then
    EXTRA_ARGS+=(--from-release)
fi
if [[ -n "${REF}" ]]; then
    EXTRA_ARGS+=(--ref "${REF}")
fi
if [[ -n "${VERIFY}" ]]; then
    EXTRA_ARGS+=(--verify "${VERIFY}")
fi
if [[ "${EDITABLE}" -eq 1 ]]; then
    EXTRA_ARGS+=(--editable)
fi
if [[ "${USE_CACHE}" -eq 1 ]]; then
    EXTRA_ARGS+=(--use-cache)
fi

for pkg in "${PACKAGES[@]}"; do
    echo "pip-rns install --uv ${pkg}${EXTRA_ARGS[*]:+ ${EXTRA_ARGS[*]}}"
    run_cmd "${PIP_RNS_BIN[@]}" install --uv "${pkg}" "${EXTRA_ARGS[@]}"
done

if [[ "${DRY_RUN}" -eq 0 ]]; then
    if command -v uv >/dev/null 2>&1; then
        run_cmd uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py
        run_cmd uv run python scripts/patch_lxst_codec2_optional.py
    else
        run_cmd python3 scripts/patch_lxst_pyogg_ogg_ctypes.py
        run_cmd python3 scripts/patch_lxst_codec2_optional.py
    fi
fi

echo "Done. Installed via pip-rns: ${PACKAGES[*]}"
