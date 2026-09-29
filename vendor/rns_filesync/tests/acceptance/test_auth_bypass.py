"""Adversarial tests for ACL bypasses, path escapes, and malicious protocol."""

from __future__ import annotations

import io
import threading
from types import SimpleNamespace

import pytest

from rns_filesync import protocol
from rns_filesync.paths import PathJailError, normalize_relpath, resolve_under_root
from rns_filesync.permissions import PermissionStore
from rns_filesync.transfer import (
    MAX_DELTA_BLOCK_NUM,
    apply_delta_blocks,
    commit_received_file,
    write_bytes_atomic,
)

pytestmark = [pytest.mark.acceptance, pytest.mark.unit]


class _FakeLink:
    def __init__(self, identity_hash: bytes | None):
        self._identity = None
        if identity_hash is not None:
            self._identity = SimpleNamespace(hash=identity_hash)
        self.destination = SimpleNamespace(hash=b"\x11" * 16)
        self.torn_down = False
        self.packets: list[bytes] = []

    def get_remote_identity(self):
        return self._identity

    def teardown(self):
        self.torn_down = True


def _service_with_acl(tmp_path, rules: list[str]):
    from rns_filesync.service import FileSyncService

    sync = tmp_path / "sync"
    sync.mkdir()
    (sync / "secret.txt").write_text("top-secret")
    perms = PermissionStore()
    for rule in rules:
        perms.add_rule(rule)
    identity = SimpleNamespace(hash=b"\xaa" * 16)
    svc = FileSyncService(
        identity=identity,
        sync_directory=str(sync),
        permissions=perms,
    )
    svc.inventory.scan()
    svc.inventory.save()
    # Avoid real RNS Packet sends.
    svc._send = lambda link, payload: link.packets.append(payload)
    return svc, sync


def test_read_only_peer_cannot_pull_file_list(tmp_path):
    reader = b"\x01" * 16
    svc, _sync = _service_with_acl(tmp_path, [f"r:{reader.hex()}"])
    # Peer with no write should not drive inbound sync, and stranger cannot list.
    stranger = _FakeLink(b"\x02" * 16)
    before = len(stranger.packets)
    svc._send_file_list(stranger)
    assert len(stranger.packets) == before

    allowed = _FakeLink(reader)
    svc._send_file_list(allowed)
    assert len(allowed.packets) == 1
    msg = protocol.decode_message(allowed.packets[0])
    assert msg["type"] == protocol.MSG_FILE_LIST
    assert "secret.txt" in msg["files"]


def test_read_only_peer_cannot_push_file_list_or_update(tmp_path):
    reader = b"\x01" * 16
    svc, sync = _service_with_acl(tmp_path, [f"r:{reader.hex()}"])
    link = _FakeLink(reader)
    svc._handle_file_list(
        {
            "type": "file_list",
            "files": {"evil.txt": {"hash": "a" * 64, "size": 1, "mtime": 1}},
        },
        link,
    )
    assert not (sync / "evil.txt").exists()
    svc._handle_file_update(
        {"path": "evil.txt", "info": {"hash": "b" * 64, "size": 1}},
        link,
    )
    assert "evil.txt" not in svc._incoming


def test_unidentified_peer_denied_when_acl_on(tmp_path):
    svc, _sync = _service_with_acl(tmp_path, ["r:all"])
    link = _FakeLink(None)
    assert not svc._require_perm(link, "read")
    assert not svc._require_perm(link, "write")
    before = len(link.packets)
    svc._send_file_list(link)
    assert len(link.packets) == before
    svc._handle_file_request({"path": "secret.txt"}, link)
    assert len(link.packets) == before


def test_blocked_identity_cannot_connect_or_read(tmp_path):
    peer = b"\x03" * 16
    svc, _sync = _service_with_acl(tmp_path, ["r:all"])
    svc.permissions.block(peer)
    assert not svc.permissions.can_connect(peer)
    link = _FakeLink(peer)
    svc._send_file_list(link)
    assert link.packets == []


def test_delete_requires_delete_perm(tmp_path):
    writer = b"\x04" * 16
    svc, sync = _service_with_acl(tmp_path, [f"rw:{writer.hex()}"])
    link = _FakeLink(writer)
    svc._handle_file_deletion({"path": "secret.txt"}, link)
    assert (sync / "secret.txt").exists()


def test_path_traversal_payloads_rejected():
    payloads = [
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
    ]
    for payload in payloads:
        with pytest.raises(PathJailError):
            normalize_relpath(payload)


def test_symlink_escape_blocked(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = root / "escape"
    try:
        link.symlink_to(tmp_path)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(PathJailError):
        resolve_under_root(str(root), "escape/outside.txt")


def test_commit_rejects_missing_hash(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    with pytest.raises(ValueError, match="missing content hash"):
        commit_received_file(
            str(root),
            "x.bin",
            mode="full",
            resource_data=io.BytesIO(b"data"),
            expected_hash=None,
            require_hash=True,
        )


def test_commit_rejects_hash_mismatch_and_removes(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    with pytest.raises(ValueError, match="hash mismatch"):
        commit_received_file(
            str(root),
            "x.bin",
            mode="full",
            resource_data=io.BytesIO(b"data"),
            expected_hash="0" * 64,
            require_hash=True,
        )
    assert not (root / "x.bin").exists()


def test_delta_block_num_cap(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    write_bytes_atomic(str(root), "f.bin", b"abc")
    with pytest.raises(PathJailError):
        apply_delta_blocks(
            str(root),
            "f.bin",
            [MAX_DELTA_BLOCK_NUM + 1],
            io.BytesIO(b"x" * 10),
        )
    with pytest.raises(PathJailError):
        apply_delta_blocks(str(root), "f.bin", [-1], io.BytesIO(b"x"))
    with pytest.raises(PathJailError):
        apply_delta_blocks(str(root), "f.bin", [True], io.BytesIO(b"x"))  # type: ignore[list-item]


def test_malicious_file_list_paths_ignored(tmp_path):
    writer = b"\x05" * 16
    svc, sync = _service_with_acl(tmp_path, [f"rwd:{writer.hex()}"])
    link = _FakeLink(writer)
    svc._handle_file_list(
        {
            "files": {
                "../escape.txt": {"hash": "a" * 64, "size": 1, "mtime": 1},
                "/etc/passwd": {"hash": "b" * 64, "size": 1, "mtime": 1},
                "ok.txt": {"hash": "c" * 64, "size": 1, "mtime": 1},
            },
        },
        link,
    )
    assert "../escape.txt" not in svc._incoming
    assert "/etc/passwd" not in svc._incoming
    assert "ok.txt" in svc._incoming
    assert not (sync / "escape.txt").exists()


def test_acl_none_overrides_all():
    store = PermissionStore()
    store.add_rule("r:all")
    store.add_rule("r:none")
    assert not store.check("ab" * 16, "read")


def test_permission_race_concurrent_checks():
    store = PermissionStore()
    peer = "ab" * 16
    store.add_rule(f"rw:{peer}")
    errors: list[Exception] = []

    def reader():
        try:
            for _ in range(200):
                assert store.check(peer, "read")
                assert not store.check("cd" * 16, "read")
        except Exception as exc:
            errors.append(exc)

    def writer():
        try:
            for i in range(200):
                store.add_rule(f"r:{i:032x}")
                store.block(f"{(i + 1):032x}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=reader) for _ in range(4)]
    threads += [threading.Thread(target=writer) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert store.check(peer, "write")
