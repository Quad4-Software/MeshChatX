# SPDX-License-Identifier: 0BSD
"""HostileMediumPack: hostile payloads and diagnostic redaction."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.favourites_layout import (
    MAX_SECTIONS,
    normalize_favourites_layout,
)
from meshchatx.src.backend.log_redaction import REDACTED, redact_diagnostic_text
from tests.backend.eect.asserts import assert_diagnostic_text_redacted
from tests.backend.eect.harness import eect_scenario

pytestmark = pytest.mark.eect


@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@given(
    raw=st.one_of(
        st.none(),
        st.integers(),
        st.text(max_size=80),
        st.lists(st.integers(), max_size=20),
        st.dictionaries(
            keys=st.text(min_size=0, max_size=40),
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.text(max_size=40),
                st.lists(st.text(max_size=20), max_size=8),
            ),
            max_size=12,
        ),
        st.fixed_dictionaries(
            {
                "sections": st.lists(
                    st.fixed_dictionaries(
                        {
                            "id": st.one_of(
                                st.none(),
                                st.sampled_from(
                                    ["__proto__", "constructor", "prototype", "ok", ""],
                                ),
                                st.text(min_size=0, max_size=80),
                            ),
                            "name": st.one_of(st.none(), st.text(max_size=200)),
                            "collapsed": st.one_of(
                                st.none(),
                                st.booleans(),
                                st.integers(),
                            ),
                        },
                    ),
                    max_size=MAX_SECTIONS + 5,
                ),
                "sectionOrder": st.lists(st.text(max_size=40), max_size=20),
                "favouritesBySection": st.dictionaries(
                    keys=st.text(max_size=40),
                    values=st.lists(st.text(max_size=80), max_size=30),
                    max_size=10,
                ),
            },
        ),
    ),
)
def test_eect_favourites_layout_fuzz_never_raises(raw):
    with eect_scenario("hostile.favourites.layout_fuzz") as (_s, _seed, _rng):
        out = normalize_favourites_layout(raw)
        assert out is None or (
            isinstance(out, dict)
            and isinstance(out.get("sections"), list)
            and isinstance(out.get("sectionOrder"), list)
            and isinstance(out.get("favouritesBySection"), dict)
        )


def test_eect_redact_helper_strips_secrets():
    full_hash = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
    out = redact_diagnostic_text(
        f"fail at /tmp/x for {full_hash} user@example.com 203.0.113.9",
    )
    assert_diagnostic_text_redacted(out)
    assert "/tmp/x" not in out
    assert full_hash not in out
    assert "user@example.com" not in out
    assert "203.0.113.9" not in out
    assert REDACTED in out


def test_eect_redact_helper_preserves_short_hash_prefix():
    short = "aabbccddeeff00112233445566778899"
    out = redact_diagnostic_text(f"peer {short} ok")
    assert short in out


def test_eect_favourites_rejects_null_bytes():
    with eect_scenario("hostile.favourites.null_bytes") as (_s, _seed, _rng):
        layout = normalize_favourites_layout(
            {
                "sections": [
                    {"id": "bad\x00id", "name": "x"},
                    {"id": "ok", "name": "y"},
                ],
                "favouritesBySection": {"ok": ["a\x00b", "c" * 32]},
            },
        )
        assert layout is not None
        assert [s["id"] for s in layout["sections"]] == ["ok"]
        assert layout["favouritesBySection"]["ok"] == ["c" * 32]


def test_eect_plugin_paths_reject_escape_forms():
    from meshchatx.src.backend.plugin_guard import (
        PluginSecurityError,
        _zip_entry_is_safe,
        normalize_asset_path,
    )

    with eect_scenario("hostile.plugin.path_escape") as (_s, _seed, _rng):
        for bad in ("../x", "/etc/passwd", "C:/Windows/x", "a/\x00/b"):
            with pytest.raises(PluginSecurityError):
                normalize_asset_path(bad)
        assert _zip_entry_is_safe("ok.wasm") is True
        assert _zip_entry_is_safe("C:/x") is False
        assert _zip_entry_is_safe("../x") is False


def test_eect_overlay_paths_reject_escape_forms():
    from meshchatx.src.backend.map_overlay_sources import (
        OverlaySourceParseError,
        _safe_repo_relpath,
    )

    with eect_scenario("hostile.overlay.path_escape") as (_s, _seed, _rng):
        assert _safe_repo_relpath("layers/a.geojson") == "layers/a.geojson"
        for bad in ("../x", "/x", "C:/Windows/x", "a\x00b", "~/.ssh/id"):
            with pytest.raises(OverlaySourceParseError):
                _safe_repo_relpath(bad)
