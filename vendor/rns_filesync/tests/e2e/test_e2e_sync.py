"""End-to-end sync tests over two Reticulum processes linked by TCP."""

from __future__ import annotations

import pytest

from tests.e2e.rns_helpers import TwoPeerHarness, wait_until

pytestmark = [pytest.mark.e2e]


@pytest.fixture
def harness(tmp_path):
    h = TwoPeerHarness(tmp_path)
    # Seed file before connect so initial exchange pulls it.
    (h.dir_b / "seed.txt").write_bytes(b"seed")
    h.start()
    yield h
    h.stop()


def test_e2e_full_file_sync(harness):
    # seed.txt should arrive via connect-time exchange
    assert wait_until(lambda: (harness.dir_a / "seed.txt").is_file(), timeout=45.0)
    assert (harness.dir_a / "seed.txt").read_bytes() == b"seed"

    harness.b_write("hello.txt", b"hello-filesync-e2e", broadcast=True)
    assert wait_until(
        lambda: (
            (harness.dir_a / "hello.txt").is_file()
            and (harness.dir_a / "hello.txt").read_bytes() == b"hello-filesync-e2e"
        ),
        timeout=45.0,
    )


def test_e2e_modify_uses_delta_path(tmp_path):
    from rns_filesync.constants import BLOCK_SIZE

    h = TwoPeerHarness(tmp_path)
    original = b"X" * (BLOCK_SIZE + 100)
    (h.dir_b / "big.bin").write_bytes(original)
    h.start()
    try:
        assert wait_until(lambda: (h.dir_a / "big.bin").is_file(), timeout=60.0)
        modified = b"Y" * BLOCK_SIZE + original[BLOCK_SIZE:]
        h.b_write("big.bin", modified, broadcast=True)
        assert wait_until(
            lambda: (
                (h.dir_a / "big.bin").is_file()
                and (h.dir_a / "big.bin").read_bytes() == modified
            ),
            timeout=60.0,
        )
    finally:
        h.stop()


def test_e2e_delete_propagates(tmp_path):
    h = TwoPeerHarness(tmp_path)
    (h.dir_b / "gone.txt").write_text("temp")
    h.start()
    try:
        assert wait_until(lambda: (h.dir_a / "gone.txt").is_file(), timeout=45.0)
        h.b_delete("gone.txt")
        assert wait_until(lambda: not (h.dir_a / "gone.txt").exists(), timeout=45.0)
    finally:
        h.stop()
