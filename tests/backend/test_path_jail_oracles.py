# SPDX-License-Identifier: 0BSD

"""Oracles for path-jail / identity-isolation bugs across storage handlers."""

from __future__ import annotations

import json
import os
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend.bot_handler import BotHandler
from meshchatx.src.backend.database import Database, DatabaseRestoreError
from meshchatx.src.backend.rncp_handler import RNCPHandler
from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler
from meshchatx.src.backend.web_audio_bridge import WebAudioBridge


def test_rncp_safe_filename_rejects_dotdot():
    assert RNCPHandler._safe_received_filename(b"..") == "downloaded_file"
    assert RNCPHandler._safe_received_filename("../secret") == "secret"
    assert RNCPHandler._safe_received_filename("a/../../etc/passwd") == "passwd"
    assert RNCPHandler._safe_received_filename("ok.bin") == "ok.bin"


def test_rncp_path_under_dir_blocks_escape(tmp_path):
    handler = RNCPHandler(MagicMock(), MagicMock(), str(tmp_path))
    recv = tmp_path / "rncp_received"
    recv.mkdir()
    safe = handler._path_under_dir(str(recv), "file.bin")
    assert safe.startswith(str(recv.resolve()))
    with pytest.raises(PermissionError):
        handler._path_under_dir(str(recv), "../outside.bin")


def test_rncp_fetch_save_dir_jails_outside_storage(tmp_path):
    storage = tmp_path / "id"
    storage.mkdir()
    handler = RNCPHandler(MagicMock(), MagicMock(), str(storage))
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(PermissionError):
        handler._resolve_fetch_save_dir(str(outside))
    nested = handler._resolve_fetch_save_dir("rncp/custom")
    assert nested.startswith(str(storage.resolve()))


def test_filesync_rejects_identity_root_and_reserved(tmp_path):
    storage = tmp_path / "id"
    storage.mkdir()
    (storage / "identity").mkdir()
    (storage / "bots").mkdir()
    handler = RnsFilesyncHandler(
        MagicMock(),
        SimpleNamespace(hash=b"\x11" * 16),
        str(storage),
    )
    assert handler._resolve_sync_directory(str(storage)) is None
    assert handler._resolve_sync_directory(str(storage / "identity")) is None
    assert handler._resolve_sync_directory(str(storage / "bots")) is None
    ok = handler._resolve_sync_directory(str(storage / "filesync" / "custom"))
    assert ok is not None
    assert ok.endswith("filesync/custom") or ok.endswith("filesync\\custom")
    shared = tmp_path / "Documents" / "MeshChatX" / "11111111" / "sync"
    shared.mkdir(parents=True)
    external = handler._resolve_sync_directory(str(shared))
    assert external == str(shared.resolve())
    assert handler._resolve_sync_directory(str(tmp_path)) is None
    assert handler._resolve_sync_directory("/etc") is None


def test_collect_external_filesync_rw_roots(tmp_path):
    from meshchatx.src.backend.rns_filesync_handler import (
        collect_external_filesync_rw_roots,
    )

    storage = tmp_path / "storage"
    ident = storage / "identities" / ("ab" * 16)
    settings_dir = ident / "filesync"
    settings_dir.mkdir(parents=True)
    shared = tmp_path / "shared_out"
    shared.mkdir()
    (settings_dir / "settings.json").write_text(
        json.dumps({"sync_directory": str(shared)}),
        encoding="utf-8",
    )
    roots = collect_external_filesync_rw_roots(str(storage))
    assert str(shared.resolve()) in roots
    # Inside storage is ignored for extra Landlock RW.
    (settings_dir / "settings.json").write_text(
        json.dumps({"sync_directory": str(settings_dir / "sync")}),
        encoding="utf-8",
    )
    assert collect_external_filesync_rw_roots(str(storage)) == []
    # Forbidden hosts must not widen Landlock.
    home = os.path.realpath(os.path.expanduser("~"))
    (settings_dir / "settings.json").write_text(
        json.dumps({"sync_directory": home}),
        encoding="utf-8",
    )
    assert collect_external_filesync_rw_roots(str(storage)) == []
    (settings_dir / "settings.json").write_text(
        json.dumps({"sync_directory": "/etc/passwd"}),
        encoding="utf-8",
    )
    assert collect_external_filesync_rw_roots(str(storage)) == []


def test_filesync_manager_resolve_never_leaves_sync_root(tmp_path):
    storage = tmp_path / "id"
    storage.mkdir()
    (storage / "identity").mkdir()
    outside = tmp_path / "OUTSIDE"
    outside.mkdir()
    (outside / "secret.txt").write_text("x", encoding="utf-8")
    handler = RnsFilesyncHandler(
        MagicMock(),
        SimpleNamespace(hash=b"\x22" * 16),
        str(storage),
    )
    sync_root = handler._sync_root()
    payloads = [
        "../identity",
        "../../OUTSIDE/secret.txt",
        str(outside / "secret.txt"),
        str(storage / "identity"),
        "/etc/passwd",
        "ok/inside.txt",
    ]
    for payload in payloads:
        abspath, err = handler._resolve_manager_path(payload, allow_root=False)
        if abspath is not None:
            assert abspath == sync_root or abspath.startswith(sync_root + os.sep)
            assert err is None
        else:
            assert err is not None
    root_abs, root_err = handler._resolve_manager_path("", allow_root=True)
    assert root_err is None
    assert root_abs == sync_root


def test_restore_rejects_bad_backup_without_wiping_live_db(tmp_path):
    db_path = tmp_path / "main.db"
    db = Database(str(db_path))
    db.initialize()
    assert db_path.is_file()
    assert Database._looks_like_sqlite(str(db_path))

    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a sqlite database")

    with pytest.raises(DatabaseRestoreError, match="not a valid SQLite"):
        db.restore_database(str(bad))

    assert db_path.is_file()
    assert Database._looks_like_sqlite(str(db_path))
    db.close_all()


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows")
def test_backup_skips_symlink_files_outside_identity(tmp_path):
    identity = tmp_path / "identity"
    identity.mkdir()
    outside = tmp_path / "OUTSIDE"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("leaked", encoding="utf-8")
    link = identity / "secret.txt"
    link.symlink_to(secret)

    db_path = identity / "database.db"
    db = Database(str(db_path))
    db.initialize()
    backup = db.backup_database(str(identity))
    db.close_all()

    with zipfile.ZipFile(backup["path"], "r") as zf:
        names = zf.namelist()
    assert "secret.txt" not in names


def test_bot_delete_refuses_rmtree_outside_bots_dir(tmp_path):
    identity = tmp_path / "id"
    identity.mkdir()
    outside = tmp_path / "precious"
    outside.mkdir()
    marker = outside / "keep.txt"
    marker.write_text("do not delete", encoding="utf-8")

    handler = BotHandler(str(identity))
    bot_id = "evilbot"
    handler.bots_state = [
        {
            "id": bot_id,
            "template_id": "echo",
            "name": "Evil",
            "storage_dir": str(outside),
            "enabled": False,
            "pid": None,
        },
    ]
    handler.stop_bot = MagicMock()
    handler._save_state = MagicMock()

    assert handler.delete_bot(bot_id) is True
    assert marker.is_file()
    assert marker.read_text(encoding="utf-8") == "do not delete"


def test_web_audio_push_drops_without_active_call():
    tele_mgr = SimpleNamespace(telephone=None, is_voicemail_session_active=False)
    bridge = WebAudioBridge(tele_mgr, config_manager=None, force_enabled=True)
    bridge.tx_source = MagicMock()
    bridge.push_client_frame(b"\x00\x01")
    bridge.tx_source.push_pcm.assert_not_called()
