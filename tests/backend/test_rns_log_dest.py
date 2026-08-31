# SPDX-License-Identifier: 0BSD
"""Oracle: RNS log destination prefers rotating Python logging when a log dir exists."""

from __future__ import annotations

import logging

from meshchatx import meshchat as meshchat_mod


def test_resolve_rns_logdest_defaults_to_callback_when_log_dir(monkeypatch):
    monkeypatch.delenv("MESHCHAT_RNS_LOG_DEST", raising=False)
    monkeypatch.setattr(meshchat_mod, "log_dir", "/tmp/meshchat-logs")
    assert (
        meshchat_mod._resolve_rns_logdest() is meshchat_mod._rns_log_to_python_logging
    )


def test_resolve_rns_logdest_stdout_override(monkeypatch):
    monkeypatch.setenv("MESHCHAT_RNS_LOG_DEST", "stdout")
    monkeypatch.setattr(meshchat_mod, "log_dir", "/tmp/meshchat-logs")
    assert meshchat_mod._resolve_rns_logdest() is None


def test_rns_log_to_python_logging_writes_info(caplog):
    with caplog.at_level(logging.INFO, logger="meshchatx.rns"):
        meshchat_mod._rns_log_to_python_logging("[12:00:00] Notice test-line")
    assert any("test-line" in r.getMessage() for r in caplog.records)
