# SPDX-License-Identifier: 0BSD


import RNS

from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.plugin_rsg import create_rsg
from meshchatx.src.backend.plugin_signature import verify_wasm_signature
from meshchatx.src.backend.plugin_wasm_bundle import (
    append_wasm_signature,
    bundle_wasm,
    parse_wasm_bundle,
    wasm_payload_without_signature,
)


def _minimal_wasm():
    # empty module: magic + version
    return b"\x00asm\x01\x00\x00\x00"


def test_embed_parse_and_signature_strip():
    manifest = {
        "id": "com.example.wasm-bundle",
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "Wasm Bundle",
        "frontend": {"entry": "frontend/main.js", "type": "js"},
        "backend": {"entry": "backend/plugin.wasm", "type": "wasm"},
    }
    files = {"frontend/main.js": "export default {}"}
    bundled = bundle_wasm(_minimal_wasm(), manifest, files)
    parsed = parse_wasm_bundle(bundled)
    assert parsed.manifest["id"] == "com.example.wasm-bundle"
    assert parsed.files["frontend/main.js"] == "export default {}"

    identity = RNS.Identity()
    payload = wasm_payload_without_signature(bundled)
    signed = append_wasm_signature(bundled, create_rsg(payload, identity))
    info = verify_wasm_signature(signed)
    assert info.valid is True
    stripped = wasm_payload_without_signature(signed)
    assert stripped == payload


def test_preview_and_install_wasm_bundle(tmp_path):
    manifest = {
        "id": "com.example.wasm-bundle",
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "Wasm Bundle",
        "frontend": {"entry": "frontend/main.js", "type": "js"},
        "backend": {"entry": "backend/plugin.wasm", "type": "wasm"},
    }
    files = {"frontend/main.js": "export default {}"}
    bundled = bundle_wasm(_minimal_wasm(), manifest, files)
    manager = PluginManager(str(tmp_path))
    preview = manager.preview_from_wasm_bytes(bundled)
    assert preview["id"] == "com.example.wasm-bundle"
    assert preview["has_frontend"] is True
    installed = manager.install_from_wasm_bytes(bundled)
    assert installed["id"] == "com.example.wasm-bundle"
    assert (
        tmp_path / "plugins" / "installed" / "com.example.wasm-bundle" / "plugin.json"
    ).is_file()
