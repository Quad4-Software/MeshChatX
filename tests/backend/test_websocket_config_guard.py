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
        "privacy_mode_enabled": False,
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
        forwarded_proto: str | None = None,
        forwarded_port: str | None = None,
    ):
        self.host = host
        self.scheme = scheme
        self.remote = remote
        self.headers = {}
        if origin is not None:
            self.headers["Origin"] = origin
        if forwarded_host is not None:
            self.headers["X-Forwarded-Host"] = forwarded_host
        if forwarded_proto is not None:
            self.headers["X-Forwarded-Proto"] = forwarded_proto
        if forwarded_port is not None:
            self.headers["X-Forwarded-Port"] = forwarded_port


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


def test_websocket_origin_allows_vite_dev_proxy_via_forwarded_host():
    """Task dev: browser Origin is :5173, Vite changeOrigin makes Host :8000."""
    req = _WsRequest(
        host="127.0.0.1:8000",
        scheme="https",
        origin="http://127.0.0.1:5173",
        remote="127.0.0.1",
        forwarded_host="127.0.0.1:5173",
    )
    assert websocket_origin_allowed(req, "127.0.0.1/32") is True
    assert websocket_origin_allowed(req, "") is False


def test_websocket_origin_honors_forwarded_proto_for_tls_terminating_proxy():
    """TLS-terminating proxy: backend sees http, browser Origin is https.

    Without X-Forwarded-Proto the portless forwarded host parses with the
    http default (80) and the https Origin (443) is always rejected.
    """
    req = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="https://chat.example",
        remote="127.0.0.1",
        forwarded_host="chat.example",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(req, "127.0.0.1/32") is True

    # Host preserved by the proxy and no X-Forwarded-Host also works.
    host_only = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="https://chat.example",
        remote="127.0.0.1",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(host_only, "127.0.0.1/32") is True

    # Untrusted peers cannot inject the scheme.
    untrusted = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="https://chat.example",
        remote="203.0.113.9",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(untrusted, "127.0.0.1/32") is False


def test_websocket_origin_honors_forwarded_port_for_custom_proxy_port():
    req = _WsRequest(
        host="chat.example:8443",
        scheme="http",
        origin="https://chat.example:8443",
        remote="127.0.0.1",
        forwarded_host="chat.example",
        forwarded_proto="https",
        forwarded_port="8443",
    )
    assert websocket_origin_allowed(req, "127.0.0.1/32") is True

    # Bogus ports are ignored and the proto default still applies.
    bad_port = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="https://chat.example",
        remote="127.0.0.1",
        forwarded_port="not-a-port",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(bad_port, "127.0.0.1/32") is True


def test_websocket_origin_forwarded_proto_does_not_widen_other_origins():
    """A trusted proxy asserting https must not admit http origins."""
    req = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="http://chat.example.evil.test",
        remote="127.0.0.1",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(req, "127.0.0.1/32") is False

    # http origin on an https-forwarded request is still a mismatch.
    req2 = _WsRequest(
        host="chat.example",
        scheme="http",
        origin="http://chat.example",
        remote="127.0.0.1",
        forwarded_proto="https",
    )
    assert websocket_origin_allowed(req2, "127.0.0.1/32") is False
