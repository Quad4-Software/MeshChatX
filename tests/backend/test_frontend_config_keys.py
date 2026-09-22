# SPDX-License-Identifier: 0BSD

"""Regression: config keys emitted by frontend settings controls must persist.

The Svelte port drifted on a few keys; apply_config_update silently ignores
unknown keys while still returning 200, so these guards pin the contract.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_map_coordinate_format_round_trip(mock_app):
    await mock_app.update_config({"map_coordinate_format": "utm"})
    assert mock_app.config.map_coordinate_format.get() == "utm"

    # Invalid values are rejected, keeping the previous value.
    await mock_app.update_config({"map_coordinate_format": "bogus"})
    assert mock_app.config.map_coordinate_format.get() == "utm"


@pytest.mark.asyncio
async def test_map_mbtiles_dir_round_trip(mock_app):
    await mock_app.update_config({"map_mbtiles_dir": "/tmp/mbtiles"})
    assert mock_app.config.map_mbtiles_dir.get() == "/tmp/mbtiles"


@pytest.mark.asyncio
async def test_gitea_base_url_round_trip(mock_app):
    await mock_app.update_config({"gitea_base_url": "https://git.example.com"})
    assert mock_app.config.gitea_base_url.get() == "https://git.example.com"

    # Non-URL strings are normalized away rather than persisted verbatim.
    await mock_app.update_config({"gitea_base_url": "not a url"})
    assert mock_app.config.gitea_base_url.get() is None


@pytest.mark.asyncio
async def test_map_overlay_limits_round_trip(mock_app):
    await mock_app.update_config(
        {
            "map_overlay_max_bytes": 2 * 1024 * 1024,
            "map_overlay_max_features": 5000,
            "map_overlay_max_kmz_uncompressed_bytes": 4 * 1024 * 1024,
            "map_overlay_max_sources": 8,
        },
    )
    c = mock_app.config
    assert c.map_overlay_max_bytes.get() == 2 * 1024 * 1024
    assert c.map_overlay_max_features.get() == 5000
    assert c.map_overlay_max_kmz_uncompressed_bytes.get() == 4 * 1024 * 1024
    assert c.map_overlay_max_sources.get() == 8
