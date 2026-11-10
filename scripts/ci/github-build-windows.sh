#!/usr/bin/env bash
# Build Windows portable zip + NSIS installer (Wails desktop shell).
#
# When MESHCHATX_FRONTEND_PREBUILT=1 the script reuses the prebuilt
# meshchatx/public/ artifact downloaded from the reusable Frontend build
# workflow and only rebuilds the cx_Freeze backend. Otherwise it falls back to
# the full pnpm build pipeline (frontend + docs + backend).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "${MESHCHATX_FRONTEND_PREBUILT:-0}" == "1" ]]; then
    if [[ ! -f "meshchatx/public/index.html" ]]; then
        echo "MESHCHATX_FRONTEND_PREBUILT=1 but meshchatx/public/index.html is missing." >&2
        echo "Download the frontend artifact into meshchatx/public/ before invoking this script." >&2
        exit 1
    fi
    pnpm run version:sync
    PLATFORM=win32 pnpm run build-backend
else
    pnpm run version:sync
    pnpm run build-frontend
    pnpm run build-docs
    pnpm run build-repository-wheels
    PLATFORM=win32 pnpm run build-backend
fi

# Windows packaging runs on a Windows runner via the desktop Taskfile
# (wails3 generate syso + makensis). Cross-building NSIS from Linux is not
# supported; this script is intended for windows-latest CI jobs.
sh scripts/ci/setup-wails3.sh
cd desktop && task windows:package
cd "$ROOT"

mkdir -p dist
cp -f desktop/bin/ReticulumMeshChat*-win32-*.zip \
      desktop/bin/ReticulumMeshChatX-v*-win32-*-installer.exe dist/ 2>/dev/null || true
ls -1 dist/

# Verify the bundled backend manifest inside the staged package payload.
for backend_dir in desktop/bin/backend build/exe/win32-x64; do
    if [[ -f "$backend_dir/backend-manifest.json" || -d "$backend_dir" ]]; then
        node scripts/ci/github-verify-backend-manifest.mjs "$backend_dir" || true
    fi
done

# Ensure AppContainer/Landlock/Seccomp modules shipped in the frozen backend.
if [[ -d build/exe ]]; then
    bash scripts/ci/github-verify-frozen-sandbox.sh build/exe
    bash scripts/ci/github-verify-frozen-runtime.sh build/exe
    if ${PYTHON_CMD:-uv run python} -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('pycodec2') else 1)"; then
        bash scripts/ci/github-verify-frozen-codec2.sh build/exe
    else
        echo "pycodec2 not installed in the build environment, skipping frozen codec2 check"
    fi
    bash scripts/ci/github-verify-frozen-umsgpack.sh build/exe
    if ${PYTHON_CMD:-uv run python} -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('bleak') else 1)"; then
        bash scripts/ci/github-verify-frozen-bleak.sh build/exe
    else
        echo "bleak not installed in the build environment, skipping bleak bundle check"
    fi
fi

# Optional packaged smoke (manual / future CI job on a Windows runner):
#   MESHCHAT_APPCONTAINER=1  start the portable exe and assert
#   GET /api/v1/server/security reports appcontainer_active true.
