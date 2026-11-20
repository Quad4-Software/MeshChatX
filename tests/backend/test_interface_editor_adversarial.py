# SPDX-License-Identifier: 0BSD
"""Adversarial input for InterfaceEditor helpers: never raise, sanitize."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.interface_editor import (
    ALLOWED_INTERFACE_MODES,
    InterfaceEditor,
)


class TestSanitizeSectionName:
    @given(name=st.one_of(st.none(), st.text(max_size=200)))
    @settings(max_examples=200, deadline=2000)
    def test_never_raises_and_output_safe_for_configobj(self, name):
        out = InterfaceEditor.sanitize_interface_section_name(name)
        assert isinstance(out, str)
        assert "[" not in out
        assert "]" not in out
        assert "\n" not in out
        assert "\r" not in out
        assert len(out) <= 128

    @given(name=st.text(max_size=200))
    @settings(max_examples=100, deadline=2000)
    def test_idempotent(self, name):
        once = InterfaceEditor.sanitize_interface_section_name(name)
        assert InterfaceEditor.sanitize_interface_section_name(once) == once

    @pytest.mark.parametrize(
        "raw,expect_absent",
        [
            ("a[b]c", ["[", "]"]),
            ("a\nb", ["\n"]),
            ("a\rb", ["\r"]),
            ("  x  y  ", ["  "]),
        ],
    )
    def test_hostile_chars_removed(self, raw, expect_absent):
        out = InterfaceEditor.sanitize_interface_section_name(raw)
        for frag in expect_absent:
            assert frag not in out


class TestModeValidation:
    @given(
        mode=st.one_of(st.text(max_size=30), st.integers(), st.booleans(), st.none())
    )
    @settings(max_examples=150, deadline=2000)
    def test_never_raises(self, mode):
        InterfaceEditor.normalize_interface_mode(mode)

    @given(mode=st.text(max_size=30))
    @settings(max_examples=150, deadline=2000)
    def test_output_is_none_or_canonical(self, mode):
        out = InterfaceEditor.normalize_interface_mode(mode)
        assert out is None or out in ALLOWED_INTERFACE_MODES

    @pytest.mark.parametrize(
        "mode,expect",
        [
            ("full", "full"),
            ("gateway", "gateway"),
            ("gw", "gateway"),
            ("ap", "access_point"),
            ("accesspoint", "access_point"),
            ("ptp", "pointtopoint"),
            ("roaming", "roaming"),
            ("internal", "internal"),
            ("FULL", "full"),
            (" bogus ", None),
            ("", None),
            (None, None),
        ],
    )
    def test_mode_mapping(self, mode, expect):
        assert InterfaceEditor.normalize_interface_mode(mode) == expect


class TestImportedOptions:
    @given(
        opts=st.dictionaries(
            keys=st.text(max_size=20),
            values=st.one_of(
                st.text(max_size=30), st.integers(), st.booleans(), st.none()
            ),
            max_size=10,
        )
    )
    @settings(max_examples=200, deadline=3000)
    def test_sanitize_never_raises(self, opts):
        out = InterfaceEditor.sanitize_imported_rns_options(dict(opts))
        assert out is None or isinstance(out, str)

    def test_idempotent_on_accepted_input(self):
        opts = {"mode": "gw", "hop_limiter": 4, "recursive_prs": True}
        first = dict(opts)
        assert InterfaceEditor.sanitize_imported_rns_options(first) is None
        second = dict(first)
        assert InterfaceEditor.sanitize_imported_rns_options(second) is None
        assert first == second

    def test_mode_canonicalized_on_import(self):
        body = {"mode": "ap"}
        assert InterfaceEditor.sanitize_imported_rns_options(body) is None
        assert body["mode"] == "access_point"

    def test_bad_mode_rejected(self):
        body = {"mode": "admin"}
        err = InterfaceEditor.sanitize_imported_rns_options(body)
        assert isinstance(err, str)

    @given(
        v=st.one_of(
            st.text(max_size=20),
            st.integers(),
            st.floats(allow_nan=True),
            st.booleans(),
            st.none(),
        )
    )
    @settings(max_examples=100, deadline=2000)
    def test_gravity_never_raises(self, v):
        InterfaceEditor.sanitize_imported_rns_options({"gravity": v})
