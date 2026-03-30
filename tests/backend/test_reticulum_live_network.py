"""
Optional live Reticulum smoke test.

Reticulum is a process-wide singleton; this test runs a short script in a
subprocess so it does not interfere with other tests.

Enable with: MESHCHAT_LIVE_RETICULUM=1

This does not replace multi-node mesh interoperability testing; it only
verifies that a default-config Reticulum instance can start and exit cleanly
in an isolated config directory (useful after RNS upgrades or OS changes).
"""

import os
import subprocess
import sys

import pytest

_RUN = os.environ.get("MESHCHAT_LIVE_RETICULUM") == "1"


@pytest.mark.integration
@pytest.mark.skipif(not _RUN, reason="Set MESHCHAT_LIVE_RETICULUM=1 to run live Reticulum subprocess smoke test")
def test_reticulum_subprocess_start_and_exit():
    script = r"""
import tempfile
import RNS

tmpdir = tempfile.mkdtemp(prefix="meshchat_rns_live_")
try:
    RNS.Reticulum(configdir=tmpdir, loglevel=RNS.LOG_ERROR)
finally:
    RNS.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr + result.stdout
