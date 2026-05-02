# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.rngit_tool import _clamp_timeout
from meshchatx.src.backend.rnprobe_handler import RNProbeHandler


@patch.object(RNS.Reticulum, "MTU", 500)
def test_rnprobe_rejects_negative_probes():
    h = RNProbeHandler(MagicMock(), MagicMock())
    with pytest.raises(ValueError, match="probes"):
        h._validate_probe_params(16, None, 0, 0)
    with pytest.raises(ValueError, match="probes"):
        h._validate_probe_params(16, None, 0, 51)


@patch.object(RNS.Reticulum, "MTU", 500)
def test_rnprobe_rejects_oversized_payload():
    h = RNProbeHandler(MagicMock(), MagicMock())
    max_b = h._max_payload_bytes()
    with pytest.raises(ValueError, match="size"):
        h._validate_probe_params(max_b + 1, None, 0, 1)


@patch.object(RNS.Reticulum, "MTU", 500)
def test_rnprobe_accepts_max_payload():
    h = RNProbeHandler(MagicMock(), MagicMock())
    max_b = h._max_payload_bytes()
    h._validate_probe_params(max_b, None, 0, 1)


def test_rngit_clamp_timeout():
    assert _clamp_timeout(None, default=30.0, minimum=1.0, maximum=100.0) == 30.0
    assert _clamp_timeout(5000.0, default=30.0, minimum=1.0, maximum=100.0) == 100.0
    assert _clamp_timeout(0.5, default=30.0, minimum=1.0, maximum=100.0) == 1.0
    assert _clamp_timeout(50.0, default=30.0, minimum=1.0, maximum=100.0) == 50.0
