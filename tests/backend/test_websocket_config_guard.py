# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_MUTATOR_TYPES,
    WEBSOCKET_PUBLIC_TYPES,
    WEBSOCKET_READ_TYPES,
    sanitize_websocket_config_update,
    websocket_origin_allowed,
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


def test_websocket_type_requires_auth_unknown_type_requires_auth():
    assert websocket_type_requires_auth("not.a.real.type") is True


class _WsRequest:
    def __init__(
        self,
        *,
        host: str,
        scheme: str = "http",
        origin: str | None = None,
        remote: str = "127.0.0.1",
        forwarded_host: str | None = None,
    ):
        self.host = host
        self.scheme = scheme
        self.remote = remote
        self.headers = {}
        if origin is not None:
            self.headers["Origin"] = origin
        if forwarded_host is not None:
            self.headers["X-Forwarded-Host"] = forwarded_host


def test_websocket_origin_allows_missing_and_same_authority():
    assert websocket_origin_allowed(_WsRequest(host="127.0.0.1:8000")) is True
    assert (
        websocket_origin_allowed(
            _WsRequest(host="127.0.0.1:8000", origin="http://127.0.0.1:8000"),
        )
        is True
    )


def test_websocket_origin_rejects_cross_site_and_userinfo():
    req = _WsRequest(host="127.0.0.1:8000", origin="https://evil.example")
    assert websocket_origin_allowed(req) is False
    userinfo = _WsRequest(
        host="127.0.0.1:8000",
        origin="http://127.0.0.1:8000@evil.example",
    )
    assert websocket_origin_allowed(userinfo) is False


def test_websocket_origin_honors_forwarded_host_behind_trusted_proxy():
    req = _WsRequest(
        host="127.0.0.1:8000",
        scheme="https",
        origin="https://chat.example:443",
        remote="127.0.0.1",
        forwarded_host="chat.example",
    )
    assert websocket_origin_allowed(req, "127.0.0.1/32") is True
    untrusted = _WsRequest(
        host="127.0.0.1:8000",
        scheme="https",
        origin="https://chat.example",
        remote="203.0.113.9",
        forwarded_host="chat.example",
    )
    assert websocket_origin_allowed(untrusted, "127.0.0.1/32") is False
