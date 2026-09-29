"""Unit tests for inventory and sync decisions."""

import os

import pytest

from rns_filesync.constants import BLOCK_SIZE
from rns_filesync.inventory import (
    Inventory,
    decide_sync_action,
    differing_block_nums,
    hash_blocks,
    hash_file,
)

pytestmark = pytest.mark.unit


def test_hash_file(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"hello")
    assert hash_file(str(path)) == hash_file(str(path))
    assert len(hash_file(str(path))) == 64


def test_hash_blocks(tmp_path):
    data = b"a" * (BLOCK_SIZE + 10)
    path = tmp_path / "b.bin"
    path.write_bytes(data)
    blocks = hash_blocks(str(path))
    assert len(blocks) == 2
    assert blocks[0]["num"] == 0
    assert blocks[1]["size"] == 10


def test_differing_block_nums():
    local = [{"num": 0, "hash": "aa"}, {"num": 1, "hash": "bb"}]
    assert differing_block_nums(local, ["aa"]) == [1]
    assert differing_block_nums(local, ["aa", "bb"]) == []


def test_decide_sync_action():
    assert decide_sync_action(None, {"hash": "a"}) == "request_full"
    assert decide_sync_action({"hash": "a"}, {"hash": "a"}) == "skip"
    assert (
        decide_sync_action({"hash": "a", "size": 10}, {"hash": "b"}) == "request_delta"
    )
    assert decide_sync_action({"hash": "a"}, None) == "ignore"


def test_inventory_scan_and_db(tmp_path):
    sync = tmp_path / "sync"
    sync.mkdir()
    (sync / "f.txt").write_text("one")
    inv = Inventory(str(sync))
    found = inv.scan()
    assert "f.txt" in found
    inv.save()
    inv2 = Inventory(str(sync))
    assert inv2.load() == 1
    assert inv2.get("f.txt")["hash"] == found["f.txt"]["hash"]


def test_inventory_mtime_fast_path(tmp_path):
    sync = tmp_path / "sync"
    sync.mkdir()
    path = sync / "f.txt"
    path.write_text("one")
    inv = Inventory(str(sync))
    first = inv.scan()
    # Second scan should reuse hash when size+mtime unchanged
    second = inv.scan()
    assert first["f.txt"]["hash"] == second["f.txt"]["hash"]
    path.write_text("two")
    # Ensure mtime changes on some filesystems
    os.utime(path, None)
    third = inv.scan()
    assert third["f.txt"]["hash"] != first["f.txt"]["hash"]
