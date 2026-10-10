# SPDX-License-Identifier: 0BSD

"""Display name updates through the settings API.

Clearing the profile name used to be silently dropped: the settings UI
reported a save while the old name came back. An empty value now resets
to the default name, the same fallback identity creation and switching
use, and the value is trimmed before it is stored.
"""

import pytest

from meshchatx.src.backend.constants import DEFAULT_DISPLAY_NAME


@pytest.fixture
def restore_display_name(mock_app):
    original = mock_app.config.display_name.get()
    yield
    mock_app.config.display_name.set(original)


@pytest.mark.asyncio
async def test_display_name_saves_and_trims(mock_app, restore_display_name):
    await mock_app.update_config({"display_name": "  Ivan  "})
    assert mock_app.config.display_name.get() == "Ivan"


@pytest.mark.asyncio
async def test_empty_display_name_resets_to_default(mock_app, restore_display_name):
    await mock_app.update_config({"display_name": "Ivan"})
    assert mock_app.config.display_name.get() == "Ivan"

    await mock_app.update_config({"display_name": ""})
    assert mock_app.config.display_name.get() == DEFAULT_DISPLAY_NAME


@pytest.mark.asyncio
async def test_whitespace_display_name_resets_to_default(
    mock_app,
    restore_display_name,
):
    await mock_app.update_config({"display_name": "Ivan"})
    await mock_app.update_config({"display_name": "   "})
    assert mock_app.config.display_name.get() == DEFAULT_DISPLAY_NAME


@pytest.mark.asyncio
async def test_non_string_display_name_resets_to_default(
    mock_app,
    restore_display_name,
):
    await mock_app.update_config({"display_name": "Ivan"})
    await mock_app.update_config({"display_name": None})
    assert mock_app.config.display_name.get() == DEFAULT_DISPLAY_NAME
