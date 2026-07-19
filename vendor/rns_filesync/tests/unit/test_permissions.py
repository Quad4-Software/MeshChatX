"""Unit tests for rngit-style permissions."""

import pytest

from rns_filesync.permissions import PermissionStore

pytestmark = pytest.mark.unit


def test_open_when_empty():
    store = PermissionStore()
    assert not store.enabled
    assert store.check(b"\x00" * 16, "write")
    assert store.can_connect(b"\x00" * 16)


def test_rule_enforces_deny_by_default():
    store = PermissionStore()
    peer = "ab" * 16
    assert store.add_rule(f"rw:{peer}")
    assert store.enabled
    assert store.check(peer, "read")
    assert store.check(peer, "write")
    assert not store.check(peer, "delete")
    assert store.can_connect(peer)
    assert not store.can_connect("cd" * 16)
    assert not store.check("cd" * 16, "read")


def test_all_and_none_targets():
    store = PermissionStore()
    store.add_rule("r:all")
    assert store.check("ff" * 16, "read")
    assert not store.check("ff" * 16, "write")

    store2 = PermissionStore()
    store2.add_rule("w:none")
    assert store2.enabled
    assert not store2.check("aa" * 16, "write")


def test_admin_and_aliases():
    store = PermissionStore()
    store.set_alias("alice", "ab" * 16)
    store.add_rule("adm:alice")
    assert store.check("ab" * 16, "delete")
    assert store.can_connect("ab" * 16)


def test_blocked():
    store = PermissionStore()
    store.add_rule("r:all")
    store.block("ab" * 16)
    assert not store.check("ab" * 16, "read")
    assert not store.can_connect("ab" * 16)


def test_load_allowed_file(tmp_path):
    path = tmp_path / "share.allowed"
    path.write_text("# comment\nr:all\nw:" + ("aa" * 16) + "\n")
    store = PermissionStore()
    assert store.load_file(str(path)) == 2
    assert store.check("ff" * 16, "read")
    assert store.check("aa" * 16, "write")


def test_legacy_hash_line(tmp_path):
    path = tmp_path / "legacy"
    path.write_text(("aa" * 16) + " read,write\n")
    store = PermissionStore()
    assert store.load_file(str(path)) == 1
    assert store.check("aa" * 16, "write")


def test_access_csv():
    store = PermissionStore()
    assert store.load_access_value("r:all, w:" + ("bb" * 16)) == 2
    assert store.check("cc" * 16, "read")
    assert store.check("bb" * 16, "write")
