# SPDX-License-Identifier: 0BSD

"""Property and adversarial oracles for plugin permission and URL helpers."""

from urllib.parse import urlparse

import pytest
from hypothesis import example, given, settings, strategies as st

from meshchatx.src.backend.plugin_permissions import (
    _host_root,
    _is_external_http_url,
    _is_http_url,
    extract_urls_from_text,
)


_LOOPBACK = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _is_external_oracle(value):
    if not isinstance(value, str):
        return False
    lower = value.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return False
    try:
        parsed = urlparse(value)
    except (ValueError, UnicodeError):
        return True
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return True
    hostname = (parsed.hostname or "").lower().strip("[]")
    if not hostname:
        return True
    return hostname not in _LOOPBACK


@st.composite
def url_string(draw, include_userinfo=False):
    scheme = draw(st.sampled_from(["http", "https"]))
    host = draw(st.sampled_from(["example.com", "api.test", "localhost", "127.0.0.1", "[::1]"]))
    port = draw(st.one_of(st.just(None), st.sampled_from([80, 443, 8080, 9337])))
    path = draw(st.sampled_from(["", "/v1", "/x?y=1"]))
    if include_userinfo and draw(st.booleans()):
        userinfo = f"{draw(st.sampled_from(['127.0.0.1:9337', 'admin']))}@"
    else:
        userinfo = ""
    if port is None:
        return f"{scheme}://{userinfo}{host}{path}"
    return f"{scheme}://{userinfo}{host}:{port}{path}"


class TestExternalHttpUrlOracle:
    @given(value=st.text() | url_string())
    @example(value="")
    @example(value="http://")
    @example(value="http://127.0.0.1:9337@example.com/v1")
    @example(value="https://localhost/api")
    @example(value="https://example.com")
    @example(value="ftp://example.com")
    @example(value="not a url")
    @settings(max_examples=200, deadline=None)
    def test_is_external_http_url_matches_reference_oracle(self, value):
        expected = _is_external_oracle(value)
        assert _is_external_http_url(value) is expected

    @given(value=st.text())
    @settings(max_examples=50, deadline=None)
    def test_is_http_url_matches_prefix_oracle(self, value):
        lower = value.lower() if isinstance(value, str) else ""
        expected = lower.startswith("http://") or lower.startswith("https://")
        assert _is_http_url(value) is expected


class TestHostRootOracle:
    @given(url=url_string(include_userinfo=True))
    @example(url="http://127.0.0.1:9337@example.com/v1")
    @example(url="https://api.example.com:8080/path")
    @example(url="http://localhost/ignore")
    @example(url="ftp://example.com/ignore")
    @example(url="not a url")
    @settings(max_examples=100, deadline=None)
    def test_host_root_derives_real_host(self, url):
        root = _host_root(url)
        if root is None:
            # Determine whether the reference oracle also rejects this URL.
            try:
                parsed = urlparse(url)
            except (ValueError, UnicodeError):
                return
            if parsed.scheme.lower() not in ("http", "https"):
                return
            hostname = parsed.hostname
            if not hostname or "." not in hostname:
                return
            assert False, f"_host_root should have produced https://{hostname.lower()}/"
        assert root.startswith("https://")
        assert root.endswith("/")
        # The root must not carry path or userinfo.
        from urllib.parse import urlparse as up
        parsed = up(root)
        assert parsed.scheme == "https"
        assert parsed.path == "/"
        assert parsed.username is None


class TestExtractUrlsOracle:
    @given(urls=st.lists(url_string(), min_size=0, max_size=6))
    @settings(max_examples=30, deadline=None)
    def test_extract_urls_are_all_external_http(self, urls):
        text = " ".join(f'fetch("{u}");' for u in urls)
        extracted = extract_urls_from_text(text)
        for url in extracted:
            assert _is_http_url(url)
            assert _is_external_http_url(url)

    @given(prefix=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8))
    @settings(max_examples=50, deadline=None)
    def test_extract_urls_never_includes_loopback_decoy(self, prefix):
        # A decoy like 127.0.0.1 as a substring in the hostname must not be skipped.
        text = f'fetch("https://{prefix}127.0.0.1{prefix}.example.com/api");'
        extracted = extract_urls_from_text(text)
        assert any("example.com" in u for u in extracted)
