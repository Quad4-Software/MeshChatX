# SPDX-License-Identifier: 0BSD
"""Metamorphic properties for normalize_relpath: jail, idempotence, never raise."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.path_utils import PathJailError, normalize_relpath

SEGMENTS = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789.-_ /\\",
    max_size=12,
)


class TestNormalizeRelpath:
    @given(st.lists(SEGMENTS, max_size=8))
    @settings(max_examples=200, deadline=3000)
    def test_output_is_jailed(self, segments):
        raw = "/".join(segments) or "x"
        try:
            out = normalize_relpath(raw)
        except PathJailError:
            return
        # Any accepted result must be inside the jail: no escapes, not
        # absolute, no stray traversal segments.
        assert not out.startswith("/")
        assert "\\" not in out
        parts = out.split("/")
        assert ".." not in parts
        assert all(p not in ("", ".") for p in parts)

    @given(st.lists(SEGMENTS, max_size=8))
    @settings(max_examples=200, deadline=3000)
    def test_idempotent(self, segments):
        raw = "/".join(segments) or "x"
        try:
            once = normalize_relpath(raw)
        except PathJailError:
            return
        assert normalize_relpath(once) == once

    @pytest.mark.parametrize(
        "raw",
        [
            "..",
            "../x",
            "a/../../b",
            "..\\x",
            "a\\..\\b",
            "/etc/passwd",
            "\\absolute",
            "a//b",
            "./a",
            "a/./b",
            "",
            ".",
            " ",
            "a/",
            "a\x00b",
        ],
    )
    def test_explicit_inputs(self, raw):
        try:
            out = normalize_relpath(raw)
        except PathJailError:
            return
        assert ".." not in out.split("/")
        assert not out.startswith("/")
        assert "\x00" not in out

    def test_dotdot_only_variants_rejected(self):
        for raw in ("..", "../", "../..", "..\\", "..\\..", "a/../../.."):
            with pytest.raises(PathJailError):
                normalize_relpath(raw)
