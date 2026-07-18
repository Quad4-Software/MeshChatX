# SPDX-License-Identifier: 0BSD
"""HostileMediumPack: hostile payloads and diagnostic redaction."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.bug_report_manager import BugReportManager
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
                                    ["__proto__", "constructor", "prototype", "ok", ""]
                                ),
                                st.text(min_size=0, max_size=80),
                            ),
                            "name": st.one_of(st.none(), st.text(max_size=200)),
                            "collapsed": st.one_of(
                                st.none(), st.booleans(), st.integers()
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


def test_eect_bug_report_redacts_secrets(tmp_path):
    with eect_scenario("hostile.bug_report.redacts_secrets") as (_s, _seed, _rng):
        full_hash = "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"

        class FakeLogs:
            def get_logs(self, **_kwargs):
                return [
                    {
                        "timestamp": 1.0,
                        "level": "ERROR",
                        "module": "meshchat",
                        "message": (
                            f"fail at /tmp/x for {full_hash} "
                            "user@example.com 203.0.113.9"
                        ),
                    },
                ]

            def get_total_count(self, **_kwargs):
                return 1

        class FakeDatabase:
            debug_logs = FakeLogs()

        class FakeApp:
            database = FakeDatabase()
            storage_dir = str(tmp_path)
            current_context = None

        manager = BugReportManager(FakeApp())
        preview = manager.preview_report({"limit": 5})
        assert_diagnostic_text_redacted(preview["log_text"])
        assert "/tmp/x" not in preview["log_text"]
        assert full_hash not in preview["log_text"]
        assert "user@example.com" not in preview["log_text"]
        assert "203.0.113.9" not in preview["log_text"]
        assert REDACTED in preview["log_text"]


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


def test_eect_rejects_decimal_hex_link_local_urls():
    from meshchatx.src.backend.http_url_guard import (
        UnsafeOutboundUrlError,
        normalize_libretranslate_http_service_base,
    )

    with eect_scenario("hostile.url.decimal_link_local") as (_s, _seed, _rng):
        for bad in (
            "http://2852039166/",
            "http://0xa9fea9fe/",
            "http://169.254.169.254/",
        ):
            with pytest.raises(UnsafeOutboundUrlError):
                normalize_libretranslate_http_service_base(bad)
