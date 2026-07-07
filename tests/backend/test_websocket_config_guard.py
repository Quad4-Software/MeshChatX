# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_MUTATOR_TYPES,
    WEBSOCKET_PUBLIC_TYPES,
    WEBSOCKET_READ_TYPES,
    sanitize_websocket_config_update,
    websocket_type_requires_auth,
)


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


def test_websocket_mutator_manifest_is_disjoint_from_public_and_read_types():
    assert WEBSOCKET_MUTATOR_TYPES.isdisjoint(WEBSOCKET_PUBLIC_TYPES)
    assert WEBSOCKET_MUTATOR_TYPES.isdisjoint(WEBSOCKET_READ_TYPES)


def test_websocket_type_requires_auth_unknown_type_is_not_mutator():
    assert websocket_type_requires_auth("not.a.real.type") is False
