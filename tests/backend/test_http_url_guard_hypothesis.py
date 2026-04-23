# SPDX-License-Identifier: 0BSD

"""Property tests for outbound loopback URL normalization."""

from urllib.parse import urlparse

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.http_url_guard import (
    UnsafeOutboundUrlError,
    normalize_loopback_http_service_base,
)


@settings(max_examples=200, deadline=None)
@given(s=st.text(max_size=4000))
def test_normalize_loopback_only_raises_safe_error_or_returns_origin(s):
    try:
        out = normalize_loopback_http_service_base(s)
    except UnsafeOutboundUrlError:
        return
    except Exception as e:
        raise AssertionError(f"unexpected exception: {type(e).__name__}: {e}") from e

    assert isinstance(out, str)
    parsed = urlparse(out)
    assert parsed.scheme in ("http", "https")
    assert parsed.netloc
    assert "@" not in parsed.netloc
    host = (parsed.hostname or "").lower().strip("[]")
    assert host in ("127.0.0.1", "localhost", "::1")
    assert parsed.path in ("", "/")
    assert parsed.query == ""
    assert parsed.fragment == ""


@settings(max_examples=80, deadline=None)
@given(s=st.one_of(st.none(), st.binary(min_size=0, max_size=256)))
def test_normalize_loopback_rejects_non_string(s):
    with pytest.raises(UnsafeOutboundUrlError):
        normalize_loopback_http_service_base(s)
