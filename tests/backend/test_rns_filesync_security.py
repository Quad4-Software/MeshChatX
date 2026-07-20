# SPDX-License-Identifier: 0BSD

"""Adversarial regression and Hypothesis fuzz coverage for RNS FileSync."""

from __future__ import annotations

import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler
from rns_filesync.paths import PathJailError, normalize_relpath

_TRAVERSAL_PAYLOADS = (
    "../etc/passwd",
    "..\\windows\\system32",
    "a/../../b",
    "/etc/passwd",
    "C:\\Windows\\System32",
    "a\x00b",
    "",
    ".",
    "..",
    "//evil",
    "\\\\evil",
    "foo/../../../etc/shadow",
    ".rns-filesync.db",
    "dir/.rns-xfer-temp",
)

_BAD_HASHES = (
    "",
    " ",
    "zz",
    "not-hex",
    "../aabb",
    "a" * 15,
    "g" * 32,
    "\x00" * 16,
    "' OR '1'='1",
    "../../identity",
    "а" * 32,
    "all",
)


@pytest.fixture
def handler(tmp_path):
    storage = tmp_path / "identity_a"
    storage.mkdir()
    identity = SimpleNamespace(hash=b"\xaa" * 16)
    return RnsFilesyncHandler(
        reticulum_instance=MagicMock(name="reticulum"),
        identity=identity,
        storage_dir=str(storage),
    )


def test_path_traversal_payloads_rejected_by_normalize():
    for payload in _TRAVERSAL_PAYLOADS:
        with pytest.raises(PathJailError):
            normalize_relpath(payload)


def test_download_rejects_path_traversal_before_service(handler):
    """Handler must jail paths itself, not wait for peer connectivity."""
    service = MagicMock()
    handler.service = service
    for payload in _TRAVERSAL_PAYLOADS:
        if not str(payload).strip():
            result = handler.download_file("bb" * 16, payload)
            assert result["ok"] is False
            assert result["error"] == "path is required"
            service.download_file.assert_not_called()
            continue
        service.reset_mock()
        result = handler.download_file("bb" * 16, payload)
        assert result["ok"] is False, payload
        assert "error" in result
        service.download_file.assert_not_called()


def test_download_and_browse_require_running(handler):
    assert handler.download_file("bb" * 16, "a.txt")["ok"] is False
    assert handler.browse_peer("bb" * 16)["ok"] is False
    assert handler.connect_peer("bb" * 16)["ok"] is False


def test_list_directories_rejects_traversal(handler):
    for payload in ("../etc", "/etc/passwd", handler.storage_dir + "/../"):
        result = handler.list_directories(payload)
        # parent of storage may resolve outside and fail jail
        if result.get("ok"):
            assert result["current"].startswith(handler.storage_dir)
        else:
            assert (
                "identity storage" in result["error"]
                or "not a directory" in result["error"]
            )


def test_create_directory_rejects_dotfiles_and_separators(handler):
    assert handler.create_directory(handler._root, ".hidden")["ok"] is False
    assert handler.create_directory(handler._root, "a/b")["ok"] is False
    assert handler.create_directory("/etc", "nope")["ok"] is False


@pytest.mark.parametrize("bad_hash", _BAD_HASHES)
def test_connect_rejects_bad_hashes(handler, bad_hash):
    handler.service = MagicMock()
    result = handler.connect_peer(bad_hash)
    assert result["ok"] is False
    assert "invalid" in result["error"] or "required" in result["error"]
    handler.service.connect_peer.assert_not_called()


@pytest.mark.parametrize("bad_hash", [h for h in _BAD_HASHES if h != "all"])
def test_acl_grant_rejects_bad_hashes(handler, bad_hash):
    result = handler.update_acl(
        identity_hash=bad_hash,
        perms=["read"],
        enforce=True,
    )
    assert result["ok"] is False
    assert "invalid" in result["error"]
    acl = handler.get_acl()
    assert bad_hash not in acl["rules"].get("read", [])
    assert "../escape" not in acl["rules"].get("read", [])


def test_acl_grant_accepts_all_alias(handler):
    result = handler.update_acl(identity_hash="all", perms=["read"], enforce=True)
    assert result["ok"] is True
    assert "all" in result["rules"]["read"]
    assert handler.get_acl()["rules"]["read"] == ["all"]


def test_acl_enforce_false_persists_across_reload(tmp_path):
    storage = tmp_path / "id"
    storage.mkdir()
    identity = SimpleNamespace(hash=b"\xaa" * 16)
    peer = "cc" * 16
    first = RnsFilesyncHandler(MagicMock(), identity, str(storage))
    first.update_acl(identity_hash=peer, perms=["read"], enforce=True)
    disabled = first.update_acl(enforce=False)
    assert disabled["ok"] is True
    assert disabled["enforce"] is False
    assert first.get_acl()["enforce"] is False
    assert peer in first.get_acl()["rules"]["read"]

    second = RnsFilesyncHandler(MagicMock(), identity, str(storage))
    acl = second.get_acl()
    assert acl["enforce"] is False
    assert peer in acl["rules"]["read"]


def test_acl_get_matches_update_result(handler):
    peer = "dd" * 16
    updated = handler.update_acl(
        identity_hash=peer, perms=["read", "write"], enforce=True
    )
    fetched = handler.get_acl()
    assert updated["enforce"] is True
    assert fetched["enforce"] is True
    assert fetched["rules"] == updated["rules"]
    assert peer in fetched["rules"]["read"]
    assert peer in fetched["rules"]["write"]


def test_sync_directory_cannot_escape_identity_storage(handler, tmp_path):
    outside = tmp_path / "other_identity" / "filesync" / "sync"
    outside.mkdir(parents=True)
    result = handler.update_settings(sync_directory=str(outside))
    assert result["ok"] is False
    assert "identity storage" in result["error"]

    nested = handler.storage_dir + "/filesync/custom"
    ok = handler.update_settings(sync_directory=nested)
    assert ok["ok"] is True
    assert ok["sync_directory"] == nested or ok["sync_directory"].endswith(
        "/filesync/custom",
    )

    # Identity root and reserved top-level trees must never be sync roots.
    root_reject = handler.update_settings(sync_directory=handler.storage_dir)
    assert root_reject["ok"] is False
    bots = os.path.join(handler.storage_dir, "bots")
    os.makedirs(bots, exist_ok=True)
    bots_reject = handler.update_settings(sync_directory=bots)
    assert bots_reject["ok"] is False


def test_start_rejects_escaped_sync_directory(handler, tmp_path):
    outside = tmp_path / "escape_me"
    outside.mkdir()
    with patch("meshchatx.src.backend.rns_filesync_handler.FileSyncService") as mocked:
        result = handler.start(sync_directory=str(outside))
        assert result["ok"] is False
        mocked.assert_not_called()


def test_teardown_clears_service_and_isolates_storage(tmp_path):
    storage_a = tmp_path / "a"
    storage_b = tmp_path / "b"
    storage_a.mkdir()
    storage_b.mkdir()
    identity_a = SimpleNamespace(hash=b"\xaa" * 16)
    identity_b = SimpleNamespace(hash=b"\xbb" * 16)
    ha = RnsFilesyncHandler(MagicMock(), identity_a, str(storage_a))
    hb = RnsFilesyncHandler(MagicMock(), identity_b, str(storage_b))
    peer = "ee" * 16
    ha.update_acl(identity_hash=peer, perms=["read"], enforce=True)
    hb.update_acl(identity_hash=peer, perms=["write"], enforce=True)

    svc = MagicMock()
    svc.get_status.return_value = {"running": True}
    ha.service = svc
    ha.teardown()
    assert ha.service is None
    svc.stop.assert_called()

    assert peer in ha.get_acl()["rules"]["read"]
    assert peer in hb.get_acl()["rules"]["write"]
    assert peer not in ha.get_acl()["rules"].get("write", [])
    assert (storage_a / "filesync" / "acl.txt").is_file()
    assert (storage_b / "filesync" / "acl.txt").is_file()


def test_concurrent_acl_mutations_stable(handler):
    peer = "ff" * 16
    errors: list[BaseException] = []

    def worker(idx: int):
        try:
            for i in range(40):
                handler.update_acl(
                    identity_hash=peer,
                    perms=["read"] if (idx + i) % 2 == 0 else ["write"],
                    enforce=True,
                )
                acl = handler.get_acl()
                assert acl["enforce"] is True
                assert peer in acl["rules"]["read"] or peer in acl["rules"]["write"]
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(path=st.sampled_from(list(_TRAVERSAL_PAYLOADS) + ["ok.txt", "dir/file.bin"]))
def test_download_path_oracle(handler, path):
    service = MagicMock()
    service.download_file.return_value = {"ok": True, "path": path}
    handler.service = service
    result = handler.download_file("aa" * 16, path)
    assert isinstance(result, dict)
    assert "ok" in result
    if not str(path).strip():
        assert result["ok"] is False
        service.download_file.assert_not_called()
        return
    try:
        normalize_relpath(path)
    except PathJailError:
        assert result["ok"] is False
        service.download_file.assert_not_called()
    else:
        assert result["ok"] is True
        service.download_file.assert_called_once()


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    identity_hash=st.one_of(
        st.sampled_from(list(_BAD_HASHES)),
        st.from_regex(r"[0-9a-f]{32}", fullmatch=True),
        st.text(min_size=0, max_size=40),
    ),
    perms=st.lists(
        st.sampled_from(["read", "write", "delete", "admin", "nope", ""]),
        max_size=6,
    ),
)
def test_acl_hash_oracle(handler, identity_hash, perms):
    effective_perms = perms if perms else ["read"]
    result = handler.update_acl(
        identity_hash=identity_hash,
        perms=effective_perms,
        enforce=True,
    )
    assert isinstance(result, dict)
    assert "ok" in result
    cleaned = str(identity_hash or "").strip().lower().replace(":", "")
    valid = cleaned == "all" or (
        len(cleaned) == 32 and all(c in "0123456789abcdef" for c in cleaned)
    )
    if not valid:
        assert result["ok"] is False
        return
    if not any(p in ("read", "write", "delete") for p in effective_perms):
        assert result["ok"] is False
        return
    assert result["ok"] is True
    assert result["rules"] == handler.get_acl()["rules"]


@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    sync_directory=st.sampled_from(
        [
            "",
            " ",
            "../escape",
            "/tmp/x",
            "~/.ssh",
            "filesync/nested",
            "filesync/../filesync/ok",
        ],
    ),
)
def test_settings_path_oracle(handler, sync_directory):
    before = handler.get_status()["sync_directory"]
    result = handler.update_settings(sync_directory=sync_directory)
    assert isinstance(result, dict)
    if result["ok"]:
        assert result["sync_directory"].startswith(handler.storage_dir)
    else:
        assert handler.get_status()["sync_directory"] == before


@patch("meshchatx.src.backend.rns_filesync_handler.FileSyncService")
def test_start_with_malicious_interval_rejected(mock_service_cls, handler):
    result = handler.start(announce_interval=1)
    assert result["ok"] is False
    mock_service_cls.assert_not_called()


@patch("meshchatx.src.backend.rns_filesync_handler.FileSyncService")
def test_start_wires_callbacks_and_reuses_host_reticulum(mock_service_cls, handler):
    service = MagicMock()
    service.start.return_value = "ab" * 16
    service.get_status.return_value = {
        "running": True,
        "sync_directory": handler._sync_directory,
        "identity_hash": "aa" * 16,
        "destination_hash": "ab" * 16,
        "peers": 0,
        "files": 0,
        "whitelist": False,
        "monitor": True,
    }
    mock_service_cls.return_value = service
    result = handler.start()
    assert result["ok"] is True
    assert mock_service_cls.call_args.kwargs["own_reticulum"] is False
    assert service.on_error is not None
    assert service.on_sync_progress is not None
