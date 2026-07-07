# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.websocket_config_guard import sanitize_websocket_config_update


def test_sanitize_websocket_config_update_strips_auth_keys():
    payload = {
        "display_name": "Peer",
        "auth_enabled": False,
        "auth_password_hash": "deadbeef",
        "theme": "dark",
    }

    sanitized = sanitize_websocket_config_update(payload)
    assert sanitized == {"display_name": "Peer", "theme": "dark"}


@pytest.mark.parametrize("payload", [None, [], "bad", 42])
def test_sanitize_websocket_config_update_rejects_non_dict(payload):
    assert sanitize_websocket_config_update(payload) == {}
