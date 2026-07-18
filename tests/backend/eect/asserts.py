# SPDX-License-Identifier: 0BSD
"""Shared oracles for EECT packs."""

from __future__ import annotations

from typing import Any


def assert_no_unexpected_http_500(status: int, body: Any = None) -> None:
    """EECT HTTP oracle: unexpected 500s fail; 4xx/503 are recoverable."""
    if status == 500:
        raise AssertionError(f"unexpected HTTP 500 body={body!r}")


def assert_recoverable_missing_path(exc: BaseException) -> None:
    """Direct send without path must surface TimeoutError, not an opaque crash."""
    assert isinstance(exc, TimeoutError), f"expected TimeoutError, got {type(exc)}"
    msg = str(exc).lower()
    assert "path" in msg, f"TimeoutError should mention path: {exc}"


def assert_identity_paths_isolated(path_a: str, path_b: str) -> None:
    assert path_a != path_b
    assert "identities" in path_a.replace("\\", "/")
    assert "identities" in path_b.replace("\\", "/")
    assert path_a.rstrip("/\\").endswith("database.db") or "database.db" in path_a
    assert path_b.rstrip("/\\").endswith("database.db") or "database.db" in path_b


def assert_preview_capped(content: str | None, max_chars: int = 240) -> None:
    if content is None:
        return
    assert len(content) <= max_chars, f"preview len {len(content)} > {max_chars}"


def assert_diagnostic_text_redacted(text: str) -> None:
    """Oracle: diagnostic dumps must not keep raw absolute paths or full 32-byte hex hashes."""
    lower = text.lower()
    assert "/tmp/" not in lower
    assert "\\users\\" not in lower
    assert "/home/" not in lower
    assert "/users/" not in lower
    # Full 32-byte hex destination/identity hash (64 hex chars)
    import re

    full_hashes = re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", lower)
    assert not full_hashes, f"unredacted full hashes remain: {full_hashes[:3]}"
