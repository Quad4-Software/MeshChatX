# SPDX-License-Identifier: 0BSD

import pytest


@pytest.mark.asyncio
async def test_websocket_config_set_ignores_auth_enabled(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set("existing-hash")

    client = object()
    await mock_app.on_websocket_data_received(
        client,
        {
            "type": "config.set",
            "config": {
                "display_name": "Updated Peer",
                "auth_enabled": False,
                "auth_password_hash": None,
            },
        },
    )

    assert mock_app.config.auth_enabled.get() is True
    assert mock_app.config.auth_password_hash.get() == "existing-hash"
    assert mock_app.config.display_name.get() == "Updated Peer"
