# SPDX-License-Identifier: 0BSD
"""Acceptance-style harness checks for EECT failure banners."""

from __future__ import annotations

import pytest

from tests.backend.eect.catalog import get_scenario
from tests.backend.eect.harness import (
    eect_scenario,
    format_failure_banner,
    resolve_seed,
)

pytestmark = pytest.mark.eect


def test_failure_banner_includes_scenario_seed_gate():
    scenario = get_scenario("hostile.bug_report.redacts_secrets")
    banner = format_failure_banner(scenario, 42, detail="boom")
    assert "scenario_id: hostile.bug_report.redacts_secrets" in banner
    assert "gate:        gate3-hostile-medium" in banner
    assert "seed:        42" in banner
    assert "MESHCHAT_EECT_SEED=42" in banner
    assert "taxonomy:    security_surface" in banner


def test_eect_scenario_rewrites_assertion(monkeypatch):
    monkeypatch.setenv("MESHCHAT_EECT_SEED", "7")
    assert resolve_seed() == 7
    with pytest.raises(AssertionError) as caught:
        with eect_scenario("path.direct.blocks_when_unavailable"):
            assert False, "forced"
    msg = str(caught.value)
    assert "EECT FAILURE" in msg
    assert "path.direct.blocks_when_unavailable" in msg
    assert "MESHCHAT_EECT_SEED=7" in msg
