#!/usr/bin/env bash
# Build a single-file Python zipapp (PYZ) for MeshChatX using shiv.
#
# Environment options:
#   PYZ_PYTHON_VERSION  e.g. 3.11 (optional; uses uv to locate/install that interpreter)
#   PYZ_SHEBANG         shebang line to embed (default: /usr/bin/env python3)
#   PYZ_OUTPUT          output path (default: dist/meshchatx.pyz, or dist/meshchatx-py<ver>.pyz)
#   SKIP_WHEEL          if 1, do not rebuild the wheel; use an existing one
#   SHIV_VERSION        shiv version to use (default: 1.0.8)
set -euo pipefail

ROOT="$(CDPATH='' cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SHIV_VERSION="${SHIV_VERSION:-1.0.8}"
SKIP_WHEEL="${SKIP_WHEEL:-0}"
PYZ_PYTHON_VERSION="${PYZ_PYTHON_VERSION:-}"

PYZ_SHEBANG="${PYZ_SHEBANG:-}"
PYZ_OUTPUT="${PYZ_OUTPUT:-}"

# Resolve the Python interpreter to build against.
if [ -n "$PYZ_PYTHON_VERSION" ]; then
    if ! PYTHON_BIN="$(uv python find "$PYZ_PYTHON_VERSION" 2>/dev/null)"; then
        echo "Python $PYZ_PYTHON_VERSION not found; installing with uv..." >&2
        uv python install "$PYZ_PYTHON_VERSION"
        PYTHON_BIN="$(uv python find "$PYZ_PYTHON_VERSION")"
    fi
    PY_SHORT="py${PYZ_PYTHON_VERSION//./}"
    PYZ_SHEBANG="${PYZ_SHEBANG:-/usr/bin/env python${PYZ_PYTHON_VERSION}}"
    PYZ_OUTPUT="${PYZ_OUTPUT:-dist/meshchatx-${PY_SHORT}.pyz}"
else
    PYTHON_BIN="$(uv run --no-project python -c 'import sys; print(sys.executable)')"
    PYZ_SHEBANG="${PYZ_SHEBANG:-/usr/bin/env python3}"
    PYZ_OUTPUT="${PYZ_OUTPUT:-dist/meshchatx.pyz}"
fi

export UV_LINK_MODE=copy

# Build or locate the wheel.
if [ "$SKIP_WHEEL" -eq 1 ]; then
    WHEEL="$(ls dist/reticulum_meshchatx-*.whl python-dist/reticulum_meshchatx-*.whl 2>/dev/null | head -n 1 || true)"
    if [ -z "$WHEEL" ]; then
        echo "No existing wheel found; set SKIP_WHEEL=0 or run 'uv build --wheel' first." >&2
        exit 1
    fi
else
    rm -f dist/reticulum_meshchatx-*.whl
    uv build --wheel
    WHEEL="$(ls dist/reticulum_meshchatx-*.whl | head -n 1)"
fi

if [ ! -d meshchatx/public ]; then
    echo "Warning: meshchatx/public is missing; the PYZ will not serve the web UI." >&2
fi

mkdir -p "$(dirname "$PYZ_OUTPUT")"
mkdir -p python-dist

# stage site-packages outside of build/ so setuptools does not delete it
SITE_PACKAGES="$(mktemp -d python-dist/pyz-sitepackages.XXXXXX)"
cleanup() {
    rm -rf "$SITE_PACKAGES"
}
trap cleanup EXIT

echo "Installing $WHEEL and dependencies for $("$PYTHON_BIN" --version)..." >&2
uv pip install --target "$SITE_PACKAGES" --python "$PYTHON_BIN" "$WHEEL"

echo "Building $PYZ_OUTPUT with shiv $SHIV_VERSION..." >&2
uvx --python "$PYTHON_BIN" "shiv==$SHIV_VERSION" \
    --site-packages "$SITE_PACKAGES" \
    --preamble "scripts/meshchatx_pyz_preamble.py" \
    -E -c meshchatx \
    --python "$PYZ_SHEBANG" \
    --compressed \
    --reproducible \
    -o "$PYZ_OUTPUT"

chmod +x "$PYZ_OUTPUT"

echo "Smoke testing $PYZ_OUTPUT..." >&2
"$PYTHON_BIN" "$PYZ_OUTPUT" --help >/dev/null

SIZE="$(du -h "$PYZ_OUTPUT" | cut -f1)"
echo "Built $PYZ_OUTPUT ($SIZE)." >&2
