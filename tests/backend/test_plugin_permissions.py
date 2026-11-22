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
    granted_allows_python_backend,
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


def test_map_permission_ids():
    validate_declared_permissions({"permissions": {"map": "read"}})
    assert declared_permission_ids({"permissions": {"map": "read"}}) == ["map:read"]
    assert declared_permission_ids({"permissions": {"map": "write"}}) == ["map:write"]
    assert declared_permission_ids({"permissions": {"map": "read-write"}}) == [
        "map:read",
        "map:write",
    ]
    assert declared_permission_ids({"permissions": {"map": "none"}}) == []
    assert declared_permission_ids({}) == []


def test_unknown_map_permission_rejected():
    with pytest.raises(ValueError, match="unknown map permission"):
        validate_declared_permissions({"permissions": {"map": "admin"}})
    with pytest.raises(ValueError):
        declared_permission_ids({"permissions": {"map": "admin"}})


def test_normalize_granted_subset():
    declared = ["hooks:announce.received", "network:fetch", "storage:isolated"]
    granted = normalize_granted_permissions(
        declared,
        ["network:fetch", "hooks:announce.received", "network:fetch", "x"],
    )
    assert granted == ["network:fetch", "hooks:announce.received"]


def test_python_backend_permission_is_default_denied():
    manifest = {"backend": {"type": "python", "entry": "backend/main.py"}}
    declared = declared_permission_ids(manifest)
    assert declared == ["backend:python"]
    assert normalize_granted_permissions(declared, None) == []
    assert not granted_allows_python_backend(None)
    assert not granted_allows_python_backend([])
    granted = normalize_granted_permissions(declared, ["backend:python"])
    assert granted == ["backend:python"]
    assert granted_allows_python_backend(granted)


def test_extract_and_collect_network_endpoints(tmp_path):
    text = 'const url = "https://api.example.com/v1"; fetch("http://localhost/ignore");'
    assert extract_urls_from_text(text) == ["https://api.example.com/v1"]

    query = 'fetch("https://api.example.com/?x=127.0.0.1")'
    assert extract_urls_from_text(query) == ["https://api.example.com/?x=127.0.0.1"]
    userinfo = 'fetch("http://127.0.0.1:9337@example.com/v1")'
    assert extract_urls_from_text(userinfo) == ["http://127.0.0.1:9337@example.com/v1"]
    substring_host = (
        'fetch("https://notlocalhost.com/a"); fetch("https://127.0.0.1.example.com/")'
    )
    extracted = extract_urls_from_text(substring_host)
    assert "https://notlocalhost.com/a" in extracted
    assert "https://127.0.0.1.example.com/" in extracted
    assert extract_urls_from_text('fetch("http://localhost/ignore")') == []
    assert (
        extract_urls_from_text('fetch("http://127.0.0.1:9337/api/v1/plugins/x")') == []
    )
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
                "https://translate.example.com/",
                "User-configured translation instance URL",
            ],
        },
    }
    endpoints = collect_network_endpoints(manifest, str(plugin_dir))
    assert "https://translate.example.com/" in endpoints
    assert "User-configured translation instance URL" in endpoints
    assert any("translate.example.org" in item for item in endpoints)
    assert requires_network_fetch(manifest, endpoints) is True


def test_host_root_uses_real_host_from_userinfo_url(tmp_path):
    """Userinfo URLs must derive the real host root, not a loopback decoy."""
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "main.js").write_text(
        'fetch("http://127.0.0.1:9337@example.com/v1")',
        encoding="utf-8",
    )
    endpoints = collect_network_endpoints({}, str(plugin_dir))
    assert "http://127.0.0.1:9337@example.com/v1" in endpoints
    assert "https://example.com/" in endpoints
    assert "https://127.0.0.1/" not in endpoints


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
    # storage was granted. Network was denied
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


def test_new_hook_and_manager_permissions_validate():
    manifest = {
        "permissions": {
            "hooks": [
                "lxmf.message.created",
                "lxmf.message.deleted",
                "lxmf.message.state",
                "lxmf.delivery",
                "lxmf.telemetry",
                "file.transfer.progress",
                "file.download.started",
                "file.download.cancelled",
                "shell.session",
                "shell.output",
                "rrc.message",
            ],
            "managers": [
                "status.read",
                "contacts.read",
                "nodes.read",
                "conversations.list",
                "messages.read",
                "message.send",
                "telemetry.read",
            ],
        },
    }
    validate_declared_permissions(manifest)
    ids = declared_permission_ids(manifest)
    assert "hooks:lxmf.message.created" in ids
    assert "hooks:shell.output" in ids
    assert "managers:message.send" in ids
    assert "managers:telemetry.read" in ids


def test_clipboard_permission_modes():
    assert declared_permission_ids({"permissions": {"clipboard": "read"}}) == [
        "clipboard:read",
    ]
    assert declared_permission_ids({"permissions": {"clipboard": "write"}}) == [
        "clipboard:write",
    ]
    assert declared_permission_ids({"permissions": {"clipboard": "read-write"}}) == [
        "clipboard:read",
        "clipboard:write",
    ]
    validate_declared_permissions({"permissions": {"clipboard": "read-write"}})
    with pytest.raises(ValueError, match="unknown clipboard"):
        validate_declared_permissions({"permissions": {"clipboard": "admin"}})


def test_plugin_fetch_url_validation():
    from meshchatx.src.backend.plugin_permissions import (
        is_allowed_plugin_fetch_url,
    )

    assert is_allowed_plugin_fetch_url("https://example.com/api")
    assert is_allowed_plugin_fetch_url("http://example.com:8080/path?q=1")
    assert not is_allowed_plugin_fetch_url("ftp://example.com/file")
    assert not is_allowed_plugin_fetch_url("file:///etc/passwd")
    assert not is_allowed_plugin_fetch_url("http://localhost/admin")
    assert not is_allowed_plugin_fetch_url("http://127.0.0.1:8000/x")
    assert not is_allowed_plugin_fetch_url("http://[::1]/x")
    assert not is_allowed_plugin_fetch_url("http://192.168.1.1/")
    assert not is_allowed_plugin_fetch_url("http://10.0.0.5/")
    assert not is_allowed_plugin_fetch_url("http://user:pass@example.com/")
    assert not is_allowed_plugin_fetch_url("")
    assert not is_allowed_plugin_fetch_url("x" * 3000)
    assert not is_allowed_plugin_fetch_url(None)


def _storage_plugin(tmp_path, granted):
    from meshchatx.src.backend.plugin_manager import PluginManager

    source = tmp_path / "src"
    source.mkdir(exist_ok=True)
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
    installed = manager.install_from_directory(str(source), granted_permissions=granted)
    manager.enable(installed["id"])
    return manager, installed["id"]


def test_storage_delete_list_clear_roundtrip(tmp_path):
    manager, plugin_id = _storage_plugin(
        tmp_path,
        ["storage:isolated"],
    )
    manager.storage_set(plugin_id, "a", "1")
    manager.storage_set(plugin_id, "b", "2")
    assert sorted(manager.storage_list(plugin_id)) == ["a", "b"]
    assert manager.storage_delete(plugin_id, "a") is True
    assert manager.storage_delete(plugin_id, "a") is False
    assert manager.storage_get(plugin_id, "a") is None
    assert manager.storage_clear(plugin_id) == 1
    assert manager.storage_list(plugin_id) == []


def test_storage_ops_denied_without_grant(tmp_path):
    manager, plugin_id = _storage_plugin(tmp_path, [])
    with pytest.raises(PermissionError):
        manager.storage_list(plugin_id)
    with pytest.raises(PermissionError):
        manager.storage_delete(plugin_id, "k")
    with pytest.raises(PermissionError):
        manager.storage_clear(plugin_id)


def test_plugin_fetch_url_validation_edge_cases():
    from meshchatx.src.backend.plugin_permissions import (
        is_allowed_plugin_fetch_url,
    )

    # Trailing-dot and bracketed loopback forms.
    assert not is_allowed_plugin_fetch_url("http://localhost./")
    assert not is_allowed_plugin_fetch_url("http://127.0.0.1./")
    # CGNAT, benchmarking, and reserved ranges are not globally routable.
    assert not is_allowed_plugin_fetch_url("http://100.64.0.1/")
    assert not is_allowed_plugin_fetch_url("http://198.18.0.1/")
    assert not is_allowed_plugin_fetch_url("http://240.0.0.1/")
    assert not is_allowed_plugin_fetch_url("http://[::ffff:127.0.0.1]/")
    assert not is_allowed_plugin_fetch_url("http://[::ffff:10.0.0.1]/")
    assert not is_allowed_plugin_fetch_url("http://[fe80::1]/")
    assert not is_allowed_plugin_fetch_url("http://[fc00::1]/")
    # NAT64 well-known prefix is "global" per is_global even when the
    # embedded IPv4 destination is loopback or private.
    assert not is_allowed_plugin_fetch_url("http://[64:ff9b::7f00:1]/")
    assert not is_allowed_plugin_fetch_url("http://[64:ff9b::a00:1]/")
    assert is_allowed_plugin_fetch_url("http://[64:ff9b::808:808]/")
    # Documentation ranges are not global either; conservative is fine.
    assert not is_allowed_plugin_fetch_url("http://192.0.2.1/")
    # Public literals still pass.
    assert is_allowed_plugin_fetch_url("https://1.1.1.1/dns-query")
    assert is_allowed_plugin_fetch_url("https://[2606:4700:4700::1111]/")
    # Non-dotted IP forms pass the literal stage; the DNS-resolution check
    # in the fetch route is what rejects them.
    assert is_allowed_plugin_fetch_url("http://2130706433/")


@pytest.mark.asyncio
async def test_plugin_fetch_host_resolves_public(monkeypatch):
    import socket

    from meshchatx.src.backend.plugin_permissions import (
        plugin_fetch_host_resolves_public,
    )

    def fake_getaddrinfo(host, port, *args, **kwargs):
        mapping = {
            "public.example.com": [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))
            ],
            "private.example.com": [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", port))
            ],
            "mixed.example.com": [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port)),
            ],
            "decimal-ip.example.com": [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))
            ],
            "nat64-private.example.com": [
                (
                    socket.AF_INET6,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("64:ff9b::7f00:1", port, 0, 0),
                )
            ],
            "nat64-public.example.com": [
                (
                    socket.AF_INET6,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("64:ff9b::808:808", port, 0, 0),
                )
            ],
        }
        if host not in mapping:
            raise socket.gaierror("name or service not known")
        return mapping[host]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    assert await plugin_fetch_host_resolves_public("https://public.example.com/")
    assert not await plugin_fetch_host_resolves_public("https://private.example.com/")
    # One bad answer poisons the whole hostname.
    assert not await plugin_fetch_host_resolves_public("https://mixed.example.com/")
    assert not await plugin_fetch_host_resolves_public(
        "https://decimal-ip.example.com/"
    )
    assert not await plugin_fetch_host_resolves_public(
        "https://nat64-private.example.com/"
    )
    assert await plugin_fetch_host_resolves_public("https://nat64-public.example.com/")
    assert not await plugin_fetch_host_resolves_public("https://nonexistent.invalid/")
