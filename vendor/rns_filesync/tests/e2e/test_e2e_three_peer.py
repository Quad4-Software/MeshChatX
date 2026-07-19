"""Three-peer sync: hub fan-out and multi-link behavior."""

from __future__ import annotations

import pytest

from tests.e2e.rns_helpers import ThreePeerHarness, wait_until

pytestmark = [pytest.mark.e2e]


@pytest.fixture
def three(tmp_path):
    h = ThreePeerHarness(tmp_path)
    (h.dir_hub / "seed.txt").write_bytes(b"hub-seed")
    h.start()
    yield h
    h.stop()


def test_e2e_three_peer_hub_seed_reaches_both_leaves(three):
    assert wait_until(lambda: (three.dir_a / "seed.txt").is_file(), timeout=60.0)
    assert wait_until(lambda: (three.dir_b / "seed.txt").is_file(), timeout=60.0)
    assert (three.dir_a / "seed.txt").read_bytes() == b"hub-seed"
    assert (three.dir_b / "seed.txt").read_bytes() == b"hub-seed"


def test_e2e_three_peer_leaf_write_fans_out_via_hub(three):
    assert wait_until(lambda: (three.dir_a / "seed.txt").is_file(), timeout=60.0)
    assert wait_until(lambda: (three.dir_b / "seed.txt").is_file(), timeout=60.0)

    three.leaf_a_write("from-a.txt", b"leaf-a-payload", broadcast=True)
    assert wait_until(
        lambda: (
            (three.dir_hub / "from-a.txt").is_file()
            and (three.dir_hub / "from-a.txt").read_bytes() == b"leaf-a-payload"
        ),
        timeout=60.0,
    )
    assert wait_until(
        lambda: (
            (three.dir_b / "from-a.txt").is_file()
            and (three.dir_b / "from-a.txt").read_bytes() == b"leaf-a-payload"
        ),
        timeout=90.0,
    )


def test_e2e_three_peer_both_leaves_receive_hub_update(tmp_path):
    h = ThreePeerHarness(tmp_path)
    h.start()
    try:
        h.hub_write("broadcast.txt", b"to-both-leaves", broadcast=True)
        assert wait_until(
            lambda: (
                (h.dir_a / "broadcast.txt").is_file()
                and (h.dir_a / "broadcast.txt").read_bytes() == b"to-both-leaves"
            ),
            timeout=60.0,
        )
        assert wait_until(
            lambda: (
                (h.dir_b / "broadcast.txt").is_file()
                and (h.dir_b / "broadcast.txt").read_bytes() == b"to-both-leaves"
            ),
            timeout=60.0,
        )
    finally:
        h.stop()
