# SPDX-License-Identifier: 0BSD

import time
from unittest.mock import MagicMock

import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def flood_app(mock_app):
    mock_app._lxmf_incoming_timestamps = []
    mock_app._flood_protection_current_cost = None
    mock_app._flood_protection_last_bump_time = 0
    mock_app.current_context.config.lxmf_flood_protection_enabled.set(True)
    mock_app.current_context.config.lxmf_flood_threshold_per_minute.set(5)
    mock_app.current_context.config.lxmf_flood_max_stamp_cost.set(12)
    mock_app.current_context.config.lxmf_inbound_stamp_cost.set(2)
    mock_app.current_context.config.block_all_from_strangers.set(False)
    mock_app.current_context.local_lxmf_destination = MagicMock()
    mock_app.current_context.local_lxmf_destination.hash = b"\x01" * 16
    mock_app.current_context.message_router = MagicMock()
    mock_app.current_context.config.display_name.set("Peer")
    return mock_app


def test_lxmf_flood_protection_raises_stamp_cost_when_threshold_exceeded(flood_app):
    now = time.time()
    flood_app._lxmf_incoming_timestamps = [now - index for index in range(6)]

    flood_app._check_lxmf_flood_protection()

    assert flood_app.current_context.config.lxmf_inbound_stamp_cost.get() == 4
    flood_app.current_context.message_router.set_inbound_stamp_cost.assert_called_once()


def test_lxmf_flood_protection_steps_down_after_cooldown(flood_app):
    now = time.time()
    flood_app._lxmf_incoming_timestamps = [now - 120]
    flood_app._flood_protection_current_cost = 2
    flood_app._flood_protection_last_bump_time = now - 120
    flood_app.current_context.config.lxmf_inbound_stamp_cost.set(6)
    flood_app.current_context.config.lxmf_flood_cooldown_seconds.set(30)

    flood_app._check_lxmf_flood_protection()

    assert flood_app.current_context.config.lxmf_inbound_stamp_cost.get() == 5


def test_lxmf_flood_protection_disabled_is_noop(flood_app):
    flood_app.current_context.config.lxmf_flood_protection_enabled.set(False)
    flood_app._lxmf_incoming_timestamps = [time.time()] * 20
    flood_app.current_context.config.lxmf_inbound_stamp_cost.set(2)

    flood_app._check_lxmf_flood_protection()

    assert flood_app.current_context.config.lxmf_inbound_stamp_cost.get() == 2
    flood_app.current_context.message_router.set_inbound_stamp_cost.assert_not_called()


def test_lxmf_flood_protection_skips_when_block_strangers_enabled(flood_app):
    flood_app.current_context.config.block_all_from_strangers.set(True)
    flood_app._lxmf_incoming_timestamps = [time.time()] * 20
    flood_app.current_context.config.lxmf_inbound_stamp_cost.set(2)

    flood_app._check_lxmf_flood_protection()

    flood_app.current_context.message_router.set_inbound_stamp_cost.assert_not_called()
