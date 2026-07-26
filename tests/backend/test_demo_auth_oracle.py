# SPDX-License-Identifier: 0BSD

"""Oracle: auth bypass env and demo password seeding."""

from __future__ import annotations

import os
from unittest.mock import patch

import bcrypt


def test_auth_bypass_disables_auth_enabled(mock_app):
    with patch.dict(os.environ, {"MESHCHAT_AUTH_BYPASS": "1"}, clear=False):
        mock_app.auth_enabled_initial = True
        mock_app.config.auth_enabled.set(True)
        assert mock_app.auth_enabled is False


def test_demo_mode_seeds_password_hash(mock_app):
    mock_app.demo_mode = True
    mock_app.auth_enabled_initial = True
    mock_app.config.auth_password_hash.set(None)
    with patch.dict(os.environ, {"MESHCHAT_DEMO_AUTH_PASSWORD": "demo"}, clear=False):
        mock_app._apply_demo_mode_runtime()
    stored = mock_app.config.auth_password_hash.get()
    assert stored is not None
    assert bcrypt.checkpw(b"demo", stored.encode("utf-8"))
