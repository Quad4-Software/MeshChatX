"""Unit tests for path jail."""

import os

import pytest

from rns_filesync.paths import (
    PathJailError,
    normalize_relpath,
    relative_to_root,
    resolve_under_root,
)

pytestmark = pytest.mark.unit


def test_normalize_relpath_ok():
    assert normalize_relpath("a/b.txt") == os.path.normpath("a/b.txt")


def test_normalize_rejects_absolute():
    with pytest.raises(PathJailError):
        normalize_relpath("/etc/passwd")


def test_normalize_rejects_traversal():
    with pytest.raises(PathJailError):
        normalize_relpath("../secret")
    with pytest.raises(PathJailError):
        normalize_relpath("a/../../b")


def test_normalize_rejects_null():
    with pytest.raises(PathJailError):
        normalize_relpath("a\x00b")


def test_resolve_under_root(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    nested = root / "dir"
    nested.mkdir()
    target = nested / "file.txt"
    target.write_text("x")
    resolved = resolve_under_root(str(root), "dir/file.txt")
    assert resolved == str(target.resolve())


def test_resolve_blocks_escape(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope")
    with pytest.raises(PathJailError):
        resolve_under_root(str(root), "../outside.txt")


def test_relative_to_root(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    path = root / "x.bin"
    path.write_bytes(b"1")
    assert relative_to_root(str(root), str(path)) == "x.bin"
