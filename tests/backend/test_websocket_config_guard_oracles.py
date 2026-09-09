# SPDX-License-Identifier: 0BSD

"""Property and adversarial oracles for WebSocket origin and config guards."""

from urllib.parse import urlparse

import pytest
from hypothesis import HealthCheck, example, given, settings, strategies as st

from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_CONFIG_DENYLIST,
    _authority_host_port,
    sanitize_websocket_config_update,
    websocket_origin_allowed,
)


TRUSTED_IPS = {"127.0.0.1", "10.0.0.1"}


class _WsRequest:
    def __init__(
        self,
        *,
        host,
        scheme="http",
        origin=None,
        remote="127.0.0.1",
        forwarded_host=None,
    ):
        self.host = host
        self.scheme = scheme
        self.remote = remote
        self.headers = {}
        if origin is not None:
            self.headers["Origin"] = origin
        if forwarded_host is not None:
            self.headers["X-Forwarded-Host"] = forwarded_host


def _client_ip_allowed(remote, cidrs):
    return bool(cidrs) and remote in TRUSTED_IPS


@st.composite
def origin_pair(draw):
    scheme = draw(st.sampled_from(["http", "https"]))
    host = draw(st.sampled_from(["127.0.0.1", "localhost", "chat.example", "[::1]"]))
    port = draw(st.one_of(st.just(None), st.sampled_from([80, 443, 8000, 5173, 9337])))
    if port is None:
        return f"{scheme}://{host}", scheme, f"{host}{'' if port is None else ''}"
    return f"{scheme}://{host}:{port}", scheme, f"{host}:{port}"


@st.composite
def cross_origin(draw):
    scheme = draw(st.sampled_from(["http", "https"]))
    host = draw(st.sampled_from(["evil.example", "attacker.local", "other.test"]))
    return f"{scheme}://{host}"


@st.composite
def authority(draw):
    host = draw(st.sampled_from(["127.0.0.1", "chat.example", "[::1]", "localhost"]))
    port = draw(st.one_of(st.just(None), st.integers(min_value=1, max_value=65535)))
    if port is None:
        return host
    return f"{host}:{port}"


def _expected_origin_allowed(request, trusted_cidrs):
    origin = request.headers.get("Origin")
    if origin is None or not origin.strip():
        return True
    try:
        parsed = urlparse(origin.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    origin_host = (parsed.hostname or "").lower()
    if not origin_host:
        return False
    origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)

    default_port = 443 if request.scheme == "https" else 80
    candidates = [request.host]
    if trusted_cidrs and _client_ip_allowed(request.remote, trusted_cidrs):
        forwarded = request.headers.get("X-Forwarded-Host")
        if forwarded:
            candidates.insert(0, forwarded.split(",")[0].strip())

    for auth in candidates:
        if not auth:
            continue
        parsed_auth = _authority_host_port(auth, default_port)
        if parsed_auth and parsed_auth == (origin_host, origin_port):
            return True
    return False


@pytest.fixture(autouse=True)
def _patch_client_ip_allowed(monkeypatch):
    monkeypatch.setattr(
        "meshchatx.src.backend.ip_allowlist.client_ip_allowed",
        _client_ip_allowed,
    )


class TestWebSocketOriginOracle:
    @given(host=authority(), origin=origin_pair())
    @example(
        host="127.0.0.1:8000",
        origin=("http://127.0.0.1:8000", "http", "127.0.0.1:8000"),
    )
    @example(
        host="127.0.0.1:8000", origin=("https://evil.example", "https", "evil.example")
    )
    @example(
        host="127.0.0.1:8000",
        origin=(
            "http://127.0.0.1:8000@evil.example",
            "http",
            "127.0.0.1:8000@evil.example",
        ),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_origin_allowed_matches_reference_parser(self, host, origin):
        origin_url, scheme, _ = origin
        req = _WsRequest(host=host, scheme=scheme, origin=origin_url)
        expected = _expected_origin_allowed(req, None)
        assert websocket_origin_allowed(req, None) is expected

    @given(
        host=authority(),
        origin=origin_pair(),
        forwarded=authority(),
        remote=st.sampled_from(["127.0.0.1", "203.0.113.9"]),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_origin_allowed_honors_trusted_proxy_forwarded_host(
        self, host, origin, forwarded, remote
    ):
        origin_url, scheme, _ = origin
        req = _WsRequest(
            host=host,
            scheme=scheme,
            origin=origin_url,
            remote=remote,
            forwarded_host=forwarded,
        )
        expected = _expected_origin_allowed(req, "127.0.0.1/32")
        assert websocket_origin_allowed(req, "127.0.0.1/32") is expected

    @given(cross=cross_origin())
    @settings(max_examples=20, deadline=None)
    def test_cross_origin_rejected(self, cross):
        req = _WsRequest(host="127.0.0.1:8000", scheme="http", origin=cross)
        assert websocket_origin_allowed(req) is False

    @given(scheme=st.sampled_from(["file", "ftp", "ws", "wss", "data", "javascript"]))
    @settings(max_examples=10, deadline=None)
    def test_non_http_origin_rejected(self, scheme):
        req = _WsRequest(
            host="127.0.0.1:8000", scheme="http", origin=f"{scheme}://chat.example"
        )
        assert websocket_origin_allowed(req) is False


class TestSanitizeConfigOracle:
    @given(key=st.text(), value=st.text())
    @settings(max_examples=50, deadline=None)
    def test_denylist_keys_removed(self, key, value):
        payload = {key: value}
        for denied in WEBSOCKET_CONFIG_DENYLIST:
            payload[denied] = value
        sanitized = sanitize_websocket_config_update(payload)
        for denied in WEBSOCKET_CONFIG_DENYLIST:
            assert denied not in sanitized
