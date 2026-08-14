# SPDX-License-Identifier: 0BSD

import io
import json
import os
import zipfile

import pytest

from meshchatx.src.backend.plugin_permissions import (
    collect_network_endpoints,
    declared_permission_ids,
    extract_urls_from_text,
    normalize_granted_permissions,
    requires_network_fetch,
    validate_declared_permissions,
)


def test_declared_permission_ids_and_validation():
    manifest = {
        "permissions": {
            "hooks": ["announce.received"],
            "managers": ["destinationPath.read"],
            "storage": "isolated",
            "network": "fetch",
        },
        "network": {"endpoints": ["https://example.com/api"]},
    }
    validate_declared_permissions(manifest)
    ids = declared_permission_ids(manifest)
    assert "hooks:announce.received" in ids
    assert "managers:destinationPath.read" in ids
    assert "storage:isolated" in ids
    assert "network:fetch" in ids


def test_unknown_permission_rejected():
    with pytest.raises(ValueError, match="unknown manager"):
        validate_declared_permissions(
            {"permissions": {"managers": ["not.a.real.capability"]}},
        )


def test_normalize_granted_subset():
    declared = ["hooks:announce.received", "network:fetch", "storage:isolated"]
    granted = normalize_granted_permissions(
        declared,
        ["network:fetch", "hooks:announce.received", "network:fetch", "x"],
    )
    assert granted == ["network:fetch", "hooks:announce.received"]


def test_extract_and_collect_network_endpoints(tmp_path):
    text = 'const url = "https://api.example.com/v1"; fetch("http://localhost/ignore");'
    assert extract_urls_from_text(text) == ["https://api.example.com/v1"]

    query = 'fetch("https://api.example.com/?x=127.0.0.1")'
    assert extract_urls_from_text(query) == ["https://api.example.com/?x=127.0.0.1"]
    userinfo = 'fetch("http://127.0.0.1:9337@example.com/v1")'
    assert extract_urls_from_text(userinfo) == ["http://127.0.0.1:9337@example.com/v1"]
    substring_host = 'fetch("https://notlocalhost.com/a"); fetch("https://127.0.0.1.example.com/")'
    extracted = extract_urls_from_text(substring_host)
    assert "https://notlocalhost.com/a" in extracted
    assert "https://127.0.0.1.example.com/" in extracted
    assert extract_urls_from_text('fetch("http://localhost/ignore")') == []
    assert extract_urls_from_text('fetch("http://127.0.0.1:9337/api/v1/plugins/x")') == []
    assert extract_urls_from_text('fetch("http://[::1]:8000/")') == []

    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "frontend").mkdir()
    (plugin_dir / "frontend" / "main.js").write_text(
        'fetch("https://translate.example.org/translate")',
        encoding="utf-8",
    )
    manifest = {
        "permissions": {"network": "fetch"},
        "network": {
            "endpoints": [
                "https://libretranslate.com/",
                "User-configured LibreTranslate instance URL",
            ],
        },
    }
    endpoints = collect_network_endpoints(manifest, str(plugin_dir))
    assert "https://libretranslate.com/" in endpoints
    assert "User-configured LibreTranslate instance URL" in endpoints
    assert any("translate.example.org" in item for item in endpoints)
    assert requires_network_fetch(manifest, endpoints) is True


def test_preview_and_install_with_denied_network(tmp_path):
    from meshchatx.src.backend.plugin_manager import PluginManager

    source = tmp_path / "src"
    source.mkdir()
    (source / "frontend").mkdir()
    (source / "frontend" / "main.js").write_text(
        'export async function activate(){ fetch("https://evil.example/x") }',
        encoding="utf-8",
    )
    manifest = {
        "id": "com.example.network-demo",
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "Network Demo",
        "frontend": {"entry": "frontend/main.js", "type": "js"},
        "permissions": {
            "hooks": ["announce.received"],
            "storage": "isolated",
            "network": "fetch",
        },
        "network": {"endpoints": ["https://evil.example/"]},
    }
    (source / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for root, _dirs, files in os.walk(source):
            for name in files:
                path = os.path.join(root, name)
                archive.write(path, os.path.relpath(path, source))
    payload = buf.getvalue()

    manager = PluginManager(str(tmp_path / "storage"))
    preview = manager.preview_from_zip_bytes(payload)
    assert preview["requires_network_fetch"] is True
    assert "network:fetch" in preview["permissions"]
    assert any("evil.example" in item for item in preview["network_endpoints"])

    installed = manager.install_from_zip_bytes(
        payload,
        granted_permissions=["hooks:announce.received", "storage:isolated"],
    )
    assert "network:fetch" not in installed["granted_permissions"]
    assert manager.network_fetch_allowed(installed["id"]) is False
    manager.enable(installed["id"])
    # storage was granted; network was denied
    manager.storage_set(installed["id"], "k", "v")
    assert manager.storage_get(installed["id"], "k") == "v"


def test_storage_denied_without_grant(tmp_path):
    from meshchatx.src.backend.plugin_manager import PluginManager

    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.storage-demo",
                "version": "1.0.0",
                "apiVersion": 1,
                "permissions": {"storage": "isolated"},
            },
        ),
        encoding="utf-8",
    )
    manager = PluginManager(str(tmp_path / "storage"))
    installed = manager.install_from_directory(str(source), granted_permissions=[])
    manager.enable(installed["id"])
    with pytest.raises(PermissionError):
        manager.storage_set(installed["id"], "k", "v")
