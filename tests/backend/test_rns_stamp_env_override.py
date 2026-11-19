# SPDX-License-Identifier: 0BSD

"""MESHCHAT_RNS_DISABLE_STAMPS restores the RNS 1.6.0 stamp defaults.

E2E stacks set it so loopback peers skip announce/path-request PoW.
"""

from unittest.mock import MagicMock

import RNS

import meshchatx.meshchat as meshchat_mod


def test_stamp_override_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MESHCHAT_RNS_DISABLE_STAMPS", raising=False)
    monkeypatch.setattr(RNS.Transport, "STAMP_DESTINATIONS", True)
    monkeypatch.setattr(RNS.Transport, "STAMP_PRS", True)
    meshchat_mod._apply_stamp_env_overrides()
    assert RNS.Transport.STAMP_DESTINATIONS is True
    assert RNS.Transport.STAMP_PRS is True


def test_stamp_override_opt_in(monkeypatch):
    monkeypatch.setenv("MESHCHAT_RNS_DISABLE_STAMPS", "1")
    monkeypatch.setattr(RNS.Transport, "STAMP_DESTINATIONS", True)
    monkeypatch.setattr(RNS.Transport, "STAMP_PRS", True)
    meshchat_mod._apply_stamp_env_overrides()
    assert RNS.Transport.STAMP_DESTINATIONS is False
    assert RNS.Transport.STAMP_PRS is False


def test_create_reticulum_runs_override(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        meshchat_mod,
        "_apply_stamp_env_overrides",
        lambda: calls.append(1),
    )
    monkeypatch.setattr(
        meshchat_mod, "_apply_interface_discovery_thresholds", lambda *a: None
    )
    monkeypatch.setattr(meshchat_mod.RNS, "Reticulum", MagicMock())
    (tmp_path / "config").write_text("[reticulum]\n")
    meshchat_mod._create_reticulum_instance(str(tmp_path))
    assert calls
