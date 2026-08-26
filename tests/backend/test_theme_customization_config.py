# SPDX-License-Identifier: 0BSD

"""Theme customization config persistence."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_theme_customization_config_round_trip(mock_app):
    await mock_app.update_config(
        {
            "theme_preset": "nord",
        }
    )
    assert mock_app.config.theme_preset.get() == "nord"

    await mock_app.update_config(
        {
            "theme": "system",
            "theme_preset": "solarized",
            "accent_color": "#aabbcc",
            "custom_canvas_color": "#010203",
            "custom_surface_color": "#040506",
        }
    )

    c = mock_app.config
    assert c.theme.get() == "system"
    assert c.theme_preset.get() == "solarized"
    assert c.accent_color.get() == "#aabbcc"
    assert c.custom_canvas_color.get() == "#010203"
    assert c.custom_surface_color.get() == "#040506"

    await mock_app.update_config(
        {
            "theme": "invalid",
            "theme_preset": "invalid",
            "accent_color": "not-a-color",
            "custom_canvas_color": "",
            "custom_surface_color": None,
        }
    )

    assert c.theme.get() == "light"
    assert c.theme_preset.get() == "default"
    assert c.accent_color.get() is None
    assert c.custom_canvas_color.get() is None
    assert c.custom_surface_color.get() is None
