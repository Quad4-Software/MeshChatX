# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.http_url_guard import (
    UnsafeOutboundUrlError,
    normalize_loopback_http_service_base,
    normalize_libretranslate_http_service_base,
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


def test_normalize_libretranslate_public_https():
    assert normalize_libretranslate_http_service_base(
        "https://libretranslate.com/path"
    ) == ("https://libretranslate.com")


def test_normalize_libretranslate_remote_host_port_strip_path():
    assert normalize_libretranslate_http_service_base(
        "http://superfishy.example:5002/languages",
    ) == ("http://superfishy.example:5002")


def test_normalize_libretranslate_private_and_loopback_ips():
    assert normalize_libretranslate_http_service_base("http://10.20.30.40:5123/") == (
        "http://10.20.30.40:5123"
    )
    assert normalize_libretranslate_http_service_base("http://127.0.0.1:5000") == (
        "http://127.0.0.1:5000"
    )


@pytest.mark.parametrize(
    "bad",
    [
        "http://169.254.169.254/latest",
        "http://239.255.0.1:5000/",
        "http://0.0.0.0/",
        "http://240.0.0.1:1",
    ],
)
def test_normalize_libretranslate_rejects_ssrf_lit_ips(bad):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_libretranslate_http_service_base(bad)


@pytest.mark.parametrize(
    "bad",
    [
        "ftp://example.com/",
        "http://user:pass@192.168.1.1:5000",
    ],
)
def test_normalize_libretranslate_rejects_scheme_or_creds(bad):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_libretranslate_http_service_base(bad)


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "http+unix://%2Ftmp%2Fs.sock"],
)
def test_normalize_libretranslate_rejects_scheme_or_empty(bad):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_libretranslate_http_service_base(bad)


def test_normalize_libretranslate_rejects_encoded_crlf_in_host():
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_libretranslate_http_service_base(
            "http://127.0.0.1%0d%0a.evil.com:80/"
        )
