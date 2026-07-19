# SPDX-License-Identifier: 0BSD

"""Regression tests for HIGH/CRITICAL path jail and client-IP fixes."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.app_security_settings import (
    get_trusted_proxy_cidrs,
    save_app_security_settings,
)
from meshchatx.src.backend.database import Database
from meshchatx.src.backend.identity_manager import IdentityManager
from meshchatx.src.backend.meshchat_utils import normalize_identity_storage_hash
from meshchatx.src.backend.plugin_guard import PluginSecurityError
from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.rncp_handler import RNCPHandler
from meshchatx.src.path_utils import (
    is_path_within_dir,
    request_client_ip,
    resolve_path_under_dir,
    safe_path_under_dir,
)


def test_normalize_identity_storage_hash_rejects_traversal():
    assert normalize_identity_storage_hash("../../tmp/target") == ""
    assert normalize_identity_storage_hash("not-a-hash") == ""
    assert normalize_identity_storage_hash("ab" * 16) == "ab" * 16


def test_delete_identity_rejects_path_traversal(tmp_path):
    manager = IdentityManager(str(tmp_path))
    victim = tmp_path / "victim_dir"
    victim.mkdir()
    marker = victim / "keep.txt"
    marker.write_text("safe")
    with pytest.raises(ValueError, match="Invalid identity hash"):
        manager.delete_identity("../../victim_dir", current_identity_hash=None)
    assert marker.exists()


def test_delete_identity_removes_only_canonical_dir(tmp_path):
    manager = IdentityManager(str(tmp_path))
    identity_hash = "cd" * 16
    target = tmp_path / "identities" / identity_hash
    target.mkdir(parents=True)
    (target / "identity").write_bytes(b"x")
    assert manager.delete_identity(identity_hash, current_identity_hash=None) is True
    assert not target.exists()


def test_backup_delete_rejects_prefix_collision_and_traversal(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.initialize()
    storage = str(tmp_path)
    backup_dir = os.path.join(storage, "database-backups")
    old_dir = os.path.join(storage, "database-backups_old")
    os.makedirs(backup_dir, exist_ok=True)
    os.makedirs(old_dir, exist_ok=True)
    secret = os.path.join(old_dir, "secret.zip")
    with open(secret, "wb") as handle:
        handle.write(b"PK")
    with pytest.raises(ValueError, match="Invalid path"):
        db.delete_snapshot_or_backup(
            storage,
            "../database-backups_old/secret.zip",
            is_backup=True,
        )
    assert os.path.exists(secret)
    db.close_all()


def test_safe_path_under_dir_collapses_traversal_to_basename(tmp_path):
    active = tmp_path / "identities" / ("aa" * 16) / "database-backups"
    other = tmp_path / "identities" / ("bb" * 16) / "database-backups"
    active.mkdir(parents=True)
    other.mkdir(parents=True)
    secret = other / "secret.zip"
    secret.write_bytes(b"PK")
    # Basename collapse must not resolve to the other identity's file.
    resolved = safe_path_under_dir(
        str(active),
        "../../" + ("bb" * 16) + "/database-backups/secret.zip",
    )
    assert resolved == os.path.realpath(str(active / "secret.zip"))
    assert resolved != os.path.realpath(str(secret))


def test_resolve_path_under_dir_allows_nested_safe_path(tmp_path):
    nested = tmp_path / "snapshots"
    nested.mkdir()
    target = nested / "snap.zip"
    target.write_bytes(b"PK")
    resolved = resolve_path_under_dir(str(nested), "snap.zip")
    assert resolved == os.path.realpath(str(target))
    assert resolve_path_under_dir(str(nested), "../outside.zip") is None


def test_plugin_backend_entry_rejects_absolute_and_traversal(tmp_path):
    manager = PluginManager(str(tmp_path))
    with pytest.raises(ValueError, match="backend.entry is invalid"):
        manager._validate_manifest(
            {
                "id": "com.example.evil",
                "name": "evil",
                "version": "1.0.0",
                "apiVersion": 1,
                "backend": {"type": "python", "entry": "/tmp/evil.py"},
            },
        )
    with pytest.raises(ValueError, match="backend.entry is invalid"):
        manager._validate_manifest(
            {
                "id": "com.example.evil2",
                "name": "evil2",
                "version": "1.0.0",
                "apiVersion": 1,
                "backend": {"type": "wasm", "entry": "../escape.wasm"},
            },
        )


def test_plugin_python_entry_path_jails_to_install_tree(tmp_path):
    manager = PluginManager(str(tmp_path))
    install = tmp_path / "installed" / "com.example.ok"
    install.mkdir(parents=True)
    entry = install / "backend.py"
    entry.write_text("x = 1\n")
    outside = tmp_path / "outside.py"
    outside.write_text("x = 2\n")
    record = MagicMock()
    record.install_path = str(install)
    record.manifest = {"backend": {"type": "python", "entry": "backend.py"}}
    assert manager._python_entry_path(record) == os.path.realpath(str(entry))
    record.manifest = {"backend": {"type": "python", "entry": str(outside)}}
    with pytest.raises(PluginSecurityError):
        manager._python_entry_path(record)


def test_plugin_wasm_resolve_does_not_delete_outside_install(tmp_path):
    manager = PluginManager(str(tmp_path))
    install = tmp_path / "installed" / "com.example.wasm"
    install.mkdir(parents=True)
    victim = tmp_path / "victim.txt"
    victim.write_text("do-not-delete")
    record = MagicMock()
    record.id = "com.example.wasm"
    record.install_path = str(install)
    record.manifest = {"backend": {"type": "wasm", "entry": str(victim)}}
    with pytest.raises(PluginSecurityError):
        manager._resolve_backend_wasm_path(record)
    assert victim.exists()


@pytest.mark.asyncio
async def test_rncp_send_path_jails_and_blocks_identity(tmp_path):
    handler = RNCPHandler(MagicMock(), MagicMock(), str(tmp_path))
    allowed = tmp_path / "payload.bin"
    allowed.write_bytes(b"data")
    identity_file = tmp_path / "identity"
    identity_file.write_bytes(b"secret-key")
    outside = tmp_path.parent / "outside-rncp.bin"
    outside.write_bytes(b"nope")

    assert handler._resolve_send_path(str(allowed)).endswith("payload.bin")
    with pytest.raises(PermissionError, match="identity private key"):
        handler._resolve_send_path(str(identity_file))
    with pytest.raises(PermissionError, match="send jail"):
        handler._resolve_send_path(str(outside))


def test_request_client_ip_ignores_xff_without_trusted_proxy():
    req = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.9"},
        remote="10.0.0.1",
    )
    assert request_client_ip(req) == "10.0.0.1"
    assert request_client_ip(req, trusted_proxy_cidrs="") == "10.0.0.1"


def test_request_client_ip_honors_xff_from_trusted_proxy():
    req = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.2"},
        remote="127.0.0.1",
    )
    assert request_client_ip(req, trusted_proxy_cidrs="127.0.0.1/32") == "203.0.113.9"


def test_request_client_ip_ignores_xff_from_untrusted_remote():
    req = SimpleNamespace(
        headers={"X-Forwarded-For": "203.0.113.9"},
        remote="198.51.100.1",
    )
    assert request_client_ip(req, trusted_proxy_cidrs="127.0.0.1/32") == "198.51.100.1"


def test_trusted_proxy_cidrs_env_override(tmp_path, monkeypatch):
    save_app_security_settings(str(tmp_path), {"trusted_proxy_cidrs": "10.0.0.1/32"})
    monkeypatch.setenv("MESHCHAT_TRUSTED_PROXIES", "127.0.0.1/32")
    assert get_trusted_proxy_cidrs(str(tmp_path)) == "127.0.0.1/32"


def test_is_path_within_dir_prefix_collision():
    assert not is_path_within_dir(
        "/tmp/storage/database-backups_old/x.zip",
        "/tmp/storage/database-backups",
    )


def test_resolve_database_restore_path_jails(mock_app, tmp_path):
    storage = tmp_path / "idstorage"
    snaps = storage / "snapshots"
    snaps.mkdir(parents=True)
    good = snaps / "ok.zip"
    good.write_bytes(b"PK")
    evil = tmp_path / "evil.zip"
    evil.write_bytes(b"PK")
    mock_app.storage_path = str(storage)
    assert mock_app._resolve_database_restore_path("ok.zip") == os.path.realpath(
        str(good)
    )
    assert mock_app._resolve_database_restore_path(str(evil)) is None
    assert mock_app._resolve_database_restore_path(str(good)) == os.path.realpath(
        str(good)
    )
