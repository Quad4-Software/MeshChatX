# SPDX-License-Identifier: 0BSD

import pytest

from meshchatx.src.backend.http_url_guard import UnsafeOutboundUrlError, normalize_loopback_http_service_base


def test_normalize_loopback_localhost():
    assert normalize_loopback_http_service_base("http://localhost:5000") == "http://localhost:5000"


def test_normalize_loopback_strip_path():
    assert normalize_loopback_http_service_base("https://127.0.0.1:5000/v1") == "https://127.0.0.1:5000"


def test_normalize_loopback_ipv6():
    assert normalize_loopback_http_service_base("http://[::1]:8080/") == "http://[::1]:8080"


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
