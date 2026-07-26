# SPDX-License-Identifier: 0BSD

"""Oracle: WebSocket mutators rejected in demo mode."""

from __future__ import annotations

import pytest

from meshchatx.src.backend.demo_mode import demo_mode_active
from meshchatx.src.backend.websocket_config_guard import WEBSOCKET_MUTATOR_TYPES


@pytest.mark.parametrize("msg_type", sorted(WEBSOCKET_MUTATOR_TYPES))
def test_demo_mode_blocks_ws_mutator_types(mock_app, msg_type):
    mock_app.demo_mode = True
    assert demo_mode_active(mock_app) is True
    assert msg_type in WEBSOCKET_MUTATOR_TYPES
