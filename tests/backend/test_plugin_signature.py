# SPDX-License-Identifier: 0BSD

import io
import json
import zipfile

import pytest
import RNS

from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.plugin_rsg import create_rsg
from meshchatx.src.backend.plugin_signature import (
    PRIMARY_SIGNATURE_FILE,
    build_canonical_zip,
    canonical_dir_payload,
    require_valid_signature,
    verify_dir_signature,
    verify_zip_signature,
    write_dir_signature,
)


def _write_plugin_dir(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "com.example.signed",
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "Signed",
        "frontend": {"entry": "frontend/main.js", "type": "js"},
    }
    (path / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    frontend = path / "frontend"
    frontend.mkdir()
    (frontend / "main.js").write_text("export default {}", encoding="utf-8")


def test_canonical_dir_zip_roundtrip(tmp_path):
    plugin_dir = tmp_path / "plugin"
    _write_plugin_dir(plugin_dir)
    payload = canonical_dir_payload(str(plugin_dir))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = sorted(archive.namelist())
    assert "frontend/main.js" in names
    assert "plugin.json" in names
    assert PRIMARY_SIGNATURE_FILE not in names


def test_unsigned_ok_invalid_blocks(tmp_path):
    plugin_dir = tmp_path / "plugin"
    _write_plugin_dir(plugin_dir)
    info = verify_dir_signature(str(plugin_dir))
    assert info.present is False
    require_valid_signature(info)

    write_dir_signature(str(plugin_dir), b"x" * 70)
    bad = verify_dir_signature(str(plugin_dir))
    assert bad.present is True
    assert bad.valid is False
    with pytest.raises(ValueError, match="invalid plugin signature"):
        require_valid_signature(bad)


def test_signed_dir_and_zip_install(tmp_path):
    plugin_dir = tmp_path / "plugin"
    _write_plugin_dir(plugin_dir)
    identity = RNS.Identity()
    payload = canonical_dir_payload(str(plugin_dir))
    write_dir_signature(str(plugin_dir), create_rsg(payload, identity))
    info = verify_dir_signature(str(plugin_dir))
    assert info.valid is True

    entries = {
        "plugin.json": (plugin_dir / "plugin.json").read_bytes(),
        "frontend/main.js": (plugin_dir / "frontend" / "main.js").read_bytes(),
    }
    # Sign zip using zip canonical payload without signature file.
    from meshchatx.src.backend.plugin_signature import (
        canonical_zip_payload_from_bytes,
        embed_signature_in_zip_bytes,
    )

    unsigned_zip = build_canonical_zip(entries)
    signed_zip = embed_signature_in_zip_bytes(
        unsigned_zip,
        create_rsg(canonical_zip_payload_from_bytes(unsigned_zip), identity),
    )
    zip_info = verify_zip_signature(signed_zip)
    assert zip_info.valid is True

    manager = PluginManager(str(tmp_path / "storage"))
    installed = manager.install_from_zip_bytes(signed_zip)
    assert installed["id"] == "com.example.signed"
    assert installed["signature"]["valid"] is True

    bad_zip = embed_signature_in_zip_bytes(unsigned_zip, b"y" * 80)
    with pytest.raises(ValueError, match="invalid plugin signature"):
        manager.install_from_zip_bytes(bad_zip)
