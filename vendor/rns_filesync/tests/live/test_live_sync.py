"""Compatibility live markers (TCP harness + host config presence)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e.rns_helpers import ThreePeerHarness, TwoPeerHarness, wait_until

pytestmark = [pytest.mark.live]


def test_live_two_peer_tcp(tmp_path):
    h = TwoPeerHarness(tmp_path)
    (h.dir_b / "live.txt").write_text("live-ok")
    h.start()
    try:
        assert wait_until(
            lambda: (
                (h.dir_a / "live.txt").is_file()
                and (h.dir_a / "live.txt").read_text() == "live-ok"
            ),
            timeout=90.0,
        )
    finally:
        h.stop()


@pytest.mark.timeout(180)
def test_live_three_peer_tcp_fanout(tmp_path):
    h = ThreePeerHarness(tmp_path)
    (h.dir_hub / "hub-live.txt").write_text("three-ok")
    h.start()
    try:
        assert wait_until(
            lambda: (
                (h.dir_a / "hub-live.txt").is_file()
                and (h.dir_b / "hub-live.txt").is_file()
            ),
            timeout=90.0,
        )
        h.leaf_a_write("fan.txt", b"a-to-b-via-hub", broadcast=True)
        assert wait_until(
            lambda: (
                (h.dir_hub / "fan.txt").is_file()
                and (h.dir_b / "fan.txt").is_file()
                and (h.dir_b / "fan.txt").read_bytes() == b"a-to-b-via-hub"
            ),
            timeout=90.0,
        )
    finally:
        h.stop()


def test_live_real_config_available():
    override = os.environ.get("RNS_FILESYNC_LIVE_CONFIG")
    path = Path(override) if override else Path.home() / ".reticulum"
    if not (path / "config").is_file():
        pytest.skip("no real Reticulum config")
    assert (path / "config").is_file()
