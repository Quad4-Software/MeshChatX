"""Exploratory stress tests using the two-peer TCP harness."""

from __future__ import annotations

import pytest

from tests.e2e.rns_helpers import TwoPeerHarness, wait_until

pytestmark = [pytest.mark.exploratory]


def test_many_small_files(tmp_path):
    h = TwoPeerHarness(tmp_path)
    for i in range(25):
        (h.dir_b / f"f{i}.txt").write_text(f"payload-{i}")
    h.start()
    try:
        assert wait_until(
            lambda: all((h.dir_a / f"f{i}.txt").is_file() for i in range(25)),
            timeout=120.0,
        )
    finally:
        h.stop()


def test_nested_and_empty(tmp_path):
    h = TwoPeerHarness(tmp_path)
    nested = h.dir_b / "sub" / "dir"
    nested.mkdir(parents=True)
    (nested / "empty").write_bytes(b"")
    (nested / "data").write_bytes(b"nested-data")
    h.start()
    try:
        assert wait_until(
            lambda: (h.dir_a / "sub" / "dir" / "data").is_file(),
            timeout=90.0,
        )
        assert (h.dir_a / "sub" / "dir" / "empty").is_file()
        assert (h.dir_a / "sub" / "dir" / "empty").stat().st_size == 0
    finally:
        h.stop()
