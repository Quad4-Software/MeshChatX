# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.http_url_guard import (
    UnsafeOutboundUrlError,
    normalize_loopback_http_service_base,
)


def test_normalize_loopback_localhost():
    assert (
        normalize_loopback_http_service_base("http://localhost:5000")
        == "http://localhost:5000"
    )


def test_normalize_loopback_strip_path():
    assert (
        normalize_loopback_http_service_base("https://127.0.0.1:5000/v1")
        == "https://127.0.0.1:5000"
    )


def test_normalize_loopback_ipv6():
    assert (
        normalize_loopback_http_service_base("http://[::1]:8080/")
        == "http://[::1]:8080"
    )


@pytest.mark.parametrize(
    "bad",
    [
        "http://192.168.1.1:5000",
        "http://example.com",
        "ftp://127.0.0.1:1",
        "http://127.0.0.1.evil.com",
        "http://user:pass@127.0.0.1:1",
    ],
)
def test_normalize_rejects_non_loopback(bad):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_loopback_http_service_base(bad)


@pytest.mark.parametrize(
    "edge",
    [
        "http://127.0.0.1:5000/",
        "http://127.0.0.1:5000",
        "https://[::1]:8080/foo",
        "http://localhost:3000/",
    ],
)
def test_normalize_accepts_loopback_variants(edge):
    out = normalize_loopback_http_service_base(edge)
    assert out.startswith("http://") or out.startswith("https://")
    assert ".." not in out


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "ws://127.0.0.1:1",
        "http+unix://%2Ftmp%2Fs.sock",
        "http://127.0.0.1%0d%0a.evil.com:80/",
    ],
)
def test_normalize_rejects_scheme_or_crlf_injection(bad):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_loopback_http_service_base(bad)
