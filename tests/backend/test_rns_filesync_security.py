# SPDX-License-Identifier: 0BSD

"""Adversarial and Hypothesis fuzz coverage for RNS FileSync handler."""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rns_filesync_handler import RnsFilesyncHandler
from rns_filesync.paths import PathJailError, normalize_relpath
from rns_filesync.permissions import PermissionStore

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


def test_download_rejects_path_traversal(handler):
    handler.service = MagicMock()
    handler.service.download_file.side_effect = lambda peer, path: {
        "ok": False,
        "error": f"path jail: {path}",
    }
    for payload in _TRAVERSAL_PAYLOADS:
        result = handler.download_file("bb" * 16, payload)
        assert result["ok"] is False
        assert "error" in result


def test_download_and_browse_require_running(handler):
    assert handler.download_file("bb" * 16, "a.txt")["ok"] is False
    assert handler.browse_peer("bb" * 16)["ok"] is False
    assert handler.connect_peer("bb" * 16)["ok"] is False


@pytest.mark.parametrize("bad_hash", _BAD_HASHES)
def test_connect_rejects_or_handles_bad_hashes(handler, bad_hash):
    handler.service = MagicMock()
    handler.service.connect_peer.return_value = {"ok": False, "error": "bad peer"}
    result = handler.connect_peer(bad_hash)
    assert isinstance(result, dict)
    assert "ok" in result
    if not str(bad_hash).strip():
        assert result["ok"] is False


@pytest.mark.parametrize("bad_hash", _BAD_HASHES)
def test_acl_grant_handles_bad_hashes(handler, bad_hash):
    result = handler.update_acl(
        identity_hash=bad_hash,
        perms=["read"],
        enforce=True,
    )
    assert isinstance(result, dict)
    assert "ok" in result


def test_acl_enforce_denies_stranger_by_default_rules(handler):
    peer = "cc" * 16
    stranger = "dd" * 16
    handler.update_acl(identity_hash=peer, perms=["read"], enforce=True)
    acl = handler.get_acl()
    assert acl["enforce"] is True
    perms = PermissionStore()
    for rule_perm, targets in acl["rules"].items():
        for target in targets:
            short = {"read": "r", "write": "w", "delete": "d"}[rule_perm]
            perms.add_rule(f"{short}:{target}")
    assert perms.check(peer, "read") is True
    assert perms.check(stranger, "read") is False
    assert perms.check(stranger, "write") is False


def test_acl_rules_text_replace_does_not_leak_old_rules(handler):
    peer_a = "11" * 16
    peer_b = "22" * 16
    handler.update_acl(identity_hash=peer_a, perms=["read", "write"], enforce=True)
    handler.update_acl(
        rules_text=f"r:{peer_b}",
        replace=True,
        enforce=True,
    )
    acl = handler.get_acl()
    assert peer_a not in acl["rules"].get("read", [])
    assert peer_b in acl["rules"].get("read", [])
    assert peer_a not in acl["rules"].get("write", [])


def test_oversized_rules_text_does_not_raise(handler):
    huge = ("r:" + ("ab" * 16) + "\n") * 5000
    result = handler.update_acl(rules_text=huge, replace=True, enforce=True)
    assert result["ok"] is True
    assert isinstance(result["rules"], dict)


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

    assert "read" in ha.get_acl()["rules"]
    assert peer in ha.get_acl()["rules"]["read"]
    assert "write" in hb.get_acl()["rules"]
    assert peer in hb.get_acl()["rules"]["write"]
    assert peer not in ha.get_acl()["rules"].get("write", [])
    assert (storage_a / "filesync" / "acl.txt").is_file()
    assert (storage_b / "filesync" / "acl.txt").is_file()
    assert storage_a.resolve() != storage_b.resolve()


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
                assert isinstance(acl["rules"], dict)
                assert acl["enforce"] is True
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors
    final = handler.get_acl()
    assert final["enforce"] is True


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    path=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "S", "Z", "Cc"),
        ),
        min_size=0,
        max_size=400,
    ),
)
def test_download_path_fuzz_never_raises(handler, path):
    handler.service = MagicMock()
    handler.service.download_file.side_effect = lambda peer, p: {
        "ok": False,
        "error": "denied",
        "path": p,
    }
    result = handler.download_file("aa" * 16, path)
    assert isinstance(result, dict)
    assert "ok" in result


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    identity_hash=st.one_of(
        st.text(min_size=0, max_size=80),
        st.binary(min_size=0, max_size=40).map(lambda b: b.hex()),
        st.sampled_from(list(_BAD_HASHES)),
    ),
    perms=st.lists(
        st.sampled_from(["read", "write", "delete", "admin", "nope", ""]),
        max_size=6,
    ),
    enforce=st.booleans(),
    rules_text=st.one_of(st.none(), st.text(max_size=500)),
    replace=st.booleans(),
)
def test_acl_update_fuzz_never_raises(
    handler,
    identity_hash,
    perms,
    enforce,
    rules_text,
    replace,
):
    result = handler.update_acl(
        identity_hash=identity_hash,
        perms=perms,
        enforce=enforce,
        rules_text=rules_text,
        replace=replace,
    )
    assert isinstance(result, dict)
    assert "ok" in result


@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    sync_directory=st.one_of(
        st.none(),
        st.text(min_size=0, max_size=200),
        st.sampled_from(["", " ", "../escape", "/tmp/x", "~/.ssh"]),
    ),
    monitor=st.one_of(st.none(), st.booleans()),
    announce_interval=st.one_of(
        st.none(),
        st.integers(min_value=-10, max_value=10_000),
        st.text(max_size=20),
    ),
)
def test_settings_fuzz_never_raises(handler, sync_directory, monitor, announce_interval):
    result = handler.update_settings(
        sync_directory=sync_directory,
        monitor=monitor,
        announce_interval=announce_interval,
    )
    assert isinstance(result, dict)
    assert "ok" in result


@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(peer_id=st.text(min_size=0, max_size=100))
def test_disconnect_fuzz_never_raises(handler, peer_id):
    handler.service = MagicMock()
    result = handler.disconnect_peer(peer_id)
    assert isinstance(result, dict)
    assert "ok" in result


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
