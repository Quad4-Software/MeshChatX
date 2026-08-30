# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler


@pytest.fixture
def mock_identity():
    return SimpleNamespace(hash=b"\xaa" * 16)


@pytest.fixture
def handler(mock_identity, tmp_path):
    storage = tmp_path / "identity"
    storage.mkdir()
    return RnsFilesyncHandler(
        reticulum_instance=MagicMock(name="reticulum"),
        identity=mock_identity,
        storage_dir=str(storage),
    )


def test_default_status_not_running(handler, mock_identity):
    status = handler.get_status()
    assert status["running"] is False
    assert status["destination_hash"] is None
    assert status["identity_hash"] == mock_identity.hash.hex()
    assert status["sync_directory"].endswith("filesync/sync")
    assert "filesync" in status["config_directory"]
    assert status["storage_directory"] == handler.storage_dir


def test_list_directories_missing_sync_path_falls_back(handler):
    missing = f"{handler.storage_dir}/filesync/sync/does-not-exist-yet"
    result = handler.list_directories(missing)
    assert result["ok"] is True
    assert result["current"].startswith(handler.storage_dir)
    assert os.path.isdir(result["current"])


def test_list_directories_defaults_to_filesync_root(handler):
    nested = f"{handler.storage_dir}/filesync/photos"
    os.makedirs(nested, exist_ok=True)
    result = handler.list_directories()
    assert result["ok"] is True
    assert result["current"].endswith("filesync")
    names = {entry["name"] for entry in result["directories"]}
    assert "photos" in names or "sync" in names


def test_list_directories_rejects_outside_jail(handler):
    result = handler.list_directories("/tmp/outside")
    assert result["ok"] is False
    assert "identity storage" in result["error"]


def test_create_directory_under_filesync(handler):
    result = handler.create_directory(None, "shared")
    assert result["ok"] is True
    assert result["path"].endswith("filesync/shared")
    listed = handler.list_directories(handler._root)
    assert any(entry["name"] == "shared" for entry in listed["directories"])


def test_create_directory_rejects_traversal_name(handler):
    result = handler.create_directory(handler._root, "../escape")
    assert result["ok"] is False
    assert "invalid" in result["error"]


def test_update_settings_persists_sync_directory(handler):
    nested = f"{handler.storage_dir}/filesync/alt"
    result = handler.update_settings(sync_directory=nested, monitor=False)
    assert result["ok"] is True
    assert result["monitor"] is False
    status = handler.get_status()
    assert status["sync_directory"] == nested
    assert status["monitor"] is False


def test_acl_grant_and_persist(handler, tmp_path):
    peer = "bb" * 16
    result = handler.update_acl(
        identity_hash=peer,
        perms=["read", "write"],
        enforce=True,
    )
    assert result["ok"] is True
    assert result["enforce"] is True
    assert peer in result["rules"]["read"]
    assert peer in result["rules"]["write"]

    acl_path = tmp_path / "identity" / "filesync" / "acl.txt"
    assert acl_path.is_file()
    text = acl_path.read_text(encoding="utf-8")
    assert f"r:{peer}" in text
    assert f"w:{peer}" in text

    again = handler.get_acl()
    assert again["enforce"] is True
    assert peer in again["rules"]["read"]


def test_connect_requires_running(handler):
    result = handler.connect_peer("cc" * 16)
    assert result["ok"] is False
    assert "not running" in result["error"]


@patch("meshchatx.src.backend.rns_filesync_handler.FileSyncService")
def test_start_stop_and_teardown(mock_service_cls, handler):
    service = MagicMock()
    service.start.return_value = "dd" * 16
    service.get_status.return_value = {
        "running": True,
        "sync_directory": handler._sync_directory,
        "identity_hash": "aa" * 16,
        "destination_hash": "dd" * 16,
        "peers": 0,
        "files": 0,
        "whitelist": False,
        "monitor": True,
    }
    service.list_peers.return_value = [{"peer_id": "ee" * 16, "status": 1}]
    service.list_files.return_value = [{"path": "a.txt", "size": 1}]
    service.connect_peer.return_value = {"ok": True, "peer_id": "ee" * 16}
    service.browse_peer.return_value = [{"path": "remote.txt", "size": 2}]
    service.download_file.return_value = {"ok": True, "path": "remote.txt"}
    mock_service_cls.return_value = service

    started = handler.start(monitor=True, announce_interval=120)
    assert started["ok"] is True
    assert started["destination_hash"] == "dd" * 16
    mock_service_cls.assert_called_once()
    kwargs = mock_service_cls.call_args.kwargs
    assert kwargs["own_reticulum"] is False
    assert kwargs["reticulum"] is handler.reticulum
    service.start.assert_called_once()

    assert handler.list_peers()[0]["peer_id"] == "ee" * 16
    assert handler.list_files()[0]["path"] == "a.txt"
    assert handler.connect_peer("ee" * 16)["ok"] is True
    assert handler.browse_peer("ee" * 16)["ok"] is True
    assert handler.download_file("ee" * 16, "remote.txt")["ok"] is True
    assert handler.announce_now()["ok"] is True
    assert handler.disconnect_peer("ee" * 16)["ok"] is True

    stopped = handler.stop()
    assert stopped["ok"] is True
    assert stopped["running"] is False
    service.stop.assert_called()
    assert handler.service is None

    service.stop.reset_mock()
    handler.service = service
    handler.teardown()
    service.stop.assert_called()
    assert handler.service is None


def test_settings_reject_sync_dir_change_while_running(handler):
    handler.service = MagicMock()
    handler.service.get_status.return_value = {"running": True}
    result = handler.update_settings(sync_directory="/tmp/other")
    assert result["ok"] is False
    assert "stop filesync" in result["error"]


def test_list_tree_while_stopped(handler):
    sync = handler._sync_directory
    nested = os.path.join(sync, "docs")
    os.makedirs(nested, exist_ok=True)
    with open(os.path.join(sync, "hello.txt"), "w", encoding="utf-8") as handle:
        handle.write("hi")
    with open(os.path.join(nested, "note.md"), "w", encoding="utf-8") as handle:
        handle.write("note")

    root = handler.list_tree()
    assert root["ok"] is True
    assert root["current"] == ""
    names = {entry["name"] for entry in root["entries"]}
    assert "hello.txt" in names
    assert "docs" in names
    assert handler.service is None

    nested_list = handler.list_tree("docs")
    assert nested_list["ok"] is True
    assert nested_list["current"] == "docs"
    assert any(e["name"] == "note.md" for e in nested_list["entries"])


def test_manager_upload_mkdir_delete_roundtrip(handler):
    mk = handler.manager_mkdir("photos")
    assert mk["ok"] is True
    assert mk["path"] == "photos"

    uploaded = handler.manager_upload(
        filename="shot.jpg",
        data=b"jpeg-bytes",
        subdir="photos",
    )
    assert uploaded["ok"] is True
    assert uploaded["path"] == "photos/shot.jpg"
    assert uploaded["size"] == len(b"jpeg-bytes")

    tree = handler.list_tree("photos")
    assert any(e["name"] == "shot.jpg" for e in tree["entries"])

    content = handler.manager_content("photos/shot.jpg")
    assert content["ok"] is True
    assert content["filename"] == "shot.jpg"
    with open(content["abspath"], "rb") as handle:
        assert handle.read() == b"jpeg-bytes"

    deleted = handler.manager_delete("photos/shot.jpg")
    assert deleted["ok"] is True
    assert not os.path.exists(
        os.path.join(handler._sync_directory, "photos", "shot.jpg"),
    )

    empty = handler.manager_delete("photos")
    assert empty["ok"] is True


def test_manager_delete_refuses_nonempty_dir(handler):
    handler.manager_mkdir("keep")
    handler.manager_upload(filename="a.txt", data=b"x", subdir="keep")
    result = handler.manager_delete("keep")
    assert result["ok"] is False
    assert "not empty" in result["error"]
    assert os.path.isdir(os.path.join(handler._sync_directory, "keep"))


def test_manager_skips_dotfiles_in_tree(handler):
    sync = handler._sync_directory
    with open(os.path.join(sync, ".secret"), "w", encoding="utf-8") as handle:
        handle.write("nope")
    with open(os.path.join(sync, ".rns-filesync.db"), "w", encoding="utf-8") as handle:
        handle.write("{}")
    with open(os.path.join(sync, "visible.txt"), "w", encoding="utf-8") as handle:
        handle.write("yes")
    tree = handler.list_tree()
    names = {e["name"] for e in tree["entries"]}
    assert "visible.txt" in names
    assert ".secret" not in names
    assert ".rns-filesync.db" not in names
