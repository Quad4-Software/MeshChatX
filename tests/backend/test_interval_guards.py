# SPDX-License-Identifier: 0BSD

"""Minimum interval guards on the app wide announce and propagation sync.

Sub-minute intervals turn announces and mailbox syncs into mesh wide
traffic storms, so the settings API clamps them and logs a warning. These
tests pin the clamp, the disable path, and the warning.
"""

import logging

import pytest

from meshchatx.src.backend.constants import MIN_ANNOUNCE_INTERVAL_SECONDS


@pytest.fixture
def restore_intervals(mock_app):
    config = mock_app.config
    original_announce = config.auto_announce_interval_seconds.get()
    original_enabled = config.auto_announce_enabled.get()
    original_sync = (
        config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
    )
    yield
    config.auto_announce_interval_seconds.set(original_announce)
    config.auto_announce_enabled.set(original_enabled)
    config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.set(original_sync)


@pytest.mark.asyncio
async def test_auto_announce_interval_clamped_to_minimum(
    mock_app, restore_intervals, caplog
):
    with caplog.at_level(logging.WARNING, logger="meshchatx"):
        await mock_app.update_config({"auto_announce_interval_seconds": 5})
    assert (
        mock_app.config.auto_announce_interval_seconds.get()
        == MIN_ANNOUNCE_INTERVAL_SECONDS
    )
    assert mock_app.config.auto_announce_enabled.get() is True
    assert "below the" in caplog.text


@pytest.mark.asyncio
async def test_auto_announce_interval_zero_disables(mock_app, restore_intervals):
    await mock_app.update_config({"auto_announce_interval_seconds": 0})
    assert mock_app.config.auto_announce_interval_seconds.get() == 0
    assert mock_app.config.auto_announce_enabled.get() is False


@pytest.mark.asyncio
async def test_auto_announce_interval_above_minimum_kept(mock_app, restore_intervals):
    await mock_app.update_config({"auto_announce_interval_seconds": 3600})
    assert mock_app.config.auto_announce_interval_seconds.get() == 3600
    assert mock_app.config.auto_announce_enabled.get() is True


@pytest.mark.asyncio
async def test_propagation_sync_interval_clamped_to_minimum(
    mock_app,
    restore_intervals,
    caplog,
):
    with caplog.at_level(logging.WARNING, logger="meshchatx"):
        await mock_app.update_config(
            {"lxmf_preferred_propagation_node_auto_sync_interval_seconds": 5},
        )
    assert (
        mock_app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
        == MIN_ANNOUNCE_INTERVAL_SECONDS
    )
    assert "below the" in caplog.text


@pytest.mark.asyncio
async def test_negative_intervals_normalize_to_disabled(mock_app, restore_intervals):
    await mock_app.update_config({"auto_announce_interval_seconds": -5})
    assert mock_app.config.auto_announce_interval_seconds.get() == 0
    assert mock_app.config.auto_announce_enabled.get() is False

    await mock_app.update_config(
        {"lxmf_preferred_propagation_node_auto_sync_interval_seconds": -5},
    )
    assert (
        mock_app.config.lxmf_preferred_propagation_node_auto_sync_interval_seconds.get()
        == 0
    )
