"""Acceptance tests for ACL and sync decision policy."""

import pytest

from rns_filesync.inventory import decide_sync_action
from rns_filesync.permissions import PermissionStore

pytestmark = pytest.mark.acceptance


@pytest.mark.parametrize(
    ("local", "peer", "expected"),
    [
        (None, {"hash": "1", "size": 10}, "request_full"),
        ({"hash": "1", "size": 10}, {"hash": "1", "size": 10}, "skip"),
        ({"hash": "1", "size": 10}, {"hash": "2", "size": 10}, "request_delta"),
        ({"hash": "1", "size": 0}, {"hash": "2", "size": 0}, "request_full"),
        ({"hash": "1"}, None, "ignore"),
    ],
)
def test_sync_decision_matrix(local, peer, expected):
    assert decide_sync_action(local, peer) == expected


def test_acl_matrix():
    store = PermissionStore()
    reader = "11" * 16
    writer = "22" * 16
    store.add_rule(f"r:{reader}")
    store.add_rule(f"rwd:{writer}")

    assert store.check(reader, "read")
    assert not store.check(reader, "write")
    assert not store.check(reader, "delete")
    assert store.check(writer, "delete")
    assert not store.can_connect("33" * 16)
