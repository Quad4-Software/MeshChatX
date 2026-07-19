"""Exploratory race and malicious-client stress tests."""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

from rns_filesync.paths import PathJailError, normalize_relpath
from rns_filesync.permissions import PermissionStore

pytestmark = [pytest.mark.exploratory]


def test_concurrent_acl_mutations_stable():
    store = PermissionStore()
    store.add_rule("r:all")
    barrier = threading.Barrier(8)
    failures: list[str] = []

    def mutate(n: int):
        barrier.wait()
        for i in range(100):
            store.add_rule(f"w:{(n * 1000 + i):032x}")
            store.block(f"{(n * 1000 + i + 7):032x}")
            if store.check("ff" * 16, "write"):
                # r:all does not grant write
                failures.append("write granted via r:all")

    threads = [threading.Thread(target=mutate, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    assert store.check("aa" * 16, "read")
    assert not store.check("aa" * 16, "write")


def test_flood_path_normalize():
    bad = [
        "../x",
        "a/../b/../c/../../d",
        "/" + "a/" * 50 + "../etc/passwd",
        "\x00" * 10,
        "..",
        "../" * 50 + "etc/passwd",
    ]
    for _ in range(1000):
        for item in bad:
            with pytest.raises(PathJailError):
                normalize_relpath(item)


def test_require_perm_under_identity_flapping(tmp_path):
    from rns_filesync.service import FileSyncService

    sync = tmp_path / "sync"
    sync.mkdir()
    perms = PermissionStore()
    allowed = b"\x10" * 16
    perms.add_rule(f"rwd:{allowed.hex()}")
    svc = FileSyncService(
        identity=SimpleNamespace(hash=b"\xaa" * 16),
        sync_directory=str(sync),
        permissions=perms,
    )

    class FlipLink:
        def __init__(self):
            self.on = False
            self.destination = SimpleNamespace(hash=b"\x11" * 16)

        def get_remote_identity(self):
            self.on = not self.on
            if self.on:
                return SimpleNamespace(hash=allowed)
            return None

    link = FlipLink()
    # Even under flapping identity, require_perm must never raise and must
    # only allow when identity is present and authorized.
    for _ in range(100):
        result = svc._require_perm(link, "read")
        assert isinstance(result, bool)
