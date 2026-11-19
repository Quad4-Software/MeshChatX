# SPDX-License-Identifier: 0BSD

"""Pin the Android packaging path for the geo-wasm artifact.

The map's Go MGRS/UTM/OLC WASM module is built by scripts/build-geo-wasm.mjs
into meshchatx/src/frontend/public/vendor/geo-wasm, copied into the vite
outDir (meshchatx/public) at frontend build time, and shipped inside the APK
because android/app/build.gradle syncs the whole meshchatx/ tree into
app/src/main/python. If any link in that chain is dropped the map silently
loses local coordinate conversion on Android.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_geo_wasm_build_outputs_into_frontend_public_vendor():
    script = _read("scripts/build-geo-wasm.mjs")
    assert "public" in script and "vendor" in script and "geo-wasm" in script
    assert '"geo.wasm"' in script
    assert '"wasm_exec.js"' in script
    assert "integrity.json" in script


def test_android_frontend_build_depends_on_geo_wasm():
    taskfile = _read("Taskfile.yml")
    frontend_block = re.search(
        r"build:frontend:.*?deps:\s*\[([^\]]+)\]", taskfile, re.DOTALL
    )
    assert frontend_block, "Taskfile build:frontend deps not found"
    assert "build:geo-wasm" in frontend_block.group(1)

    prepare_block = re.search(
        r"android:prepare:.*?deps:\s*\[([^\]]+)\]", taskfile, re.DOTALL
    )
    assert prepare_block, "Taskfile android:prepare deps not found"
    assert re.search(r"build:(fe|frontend)", prepare_block.group(1))


def test_android_gradle_syncs_frontend_public_tree():
    gradle = _read("android/app/build.gradle")
    assert 'new File(repoRoot, "meshchatx")' in gradle
    sync_block = re.search(
        r'syncMeshchatPython.*?from\(meshchatSourceDir\)', gradle, re.DOTALL
    )
    assert sync_block, (
        "syncMeshchatPython no longer copies the meshchatx tree; "
        "public/vendor/geo-wasm would be missing from the APK"
    )


def test_backend_serves_wasm_mime_type():
    meshchat = _read("meshchatx/meshchat.py")
    assert 'mimetypes.add_type("application/wasm", ".wasm")' in meshchat


def test_csp_permits_wasm_eval():
    middleware = _read("meshchatx/src/backend/http/middleware.py")
    assert "wasm-unsafe-eval" in middleware
