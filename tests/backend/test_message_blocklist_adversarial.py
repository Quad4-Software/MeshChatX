# SPDX-License-Identifier: 0BSD
"""Properties for message blocklist normalize/match/export roundtrip."""


import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.message_blocklist import (
    _validate_regex_pattern,
    build_export_document,
    first_matching_blocklist_entry,
    normalize_message_blocklist,
    parse_import_document,
)

# Patterns whose evaluation is super-linear (nested quantifiers or
# overlapping alternation inside a quantified group). stdlib re has no
# timeout, so these must be rejected at validation time.
REDOS_PATTERNS = [
    r"(x+x+)+y",
    r"(a+)+$",
    r"(\w+)*$",
    r"(a|a)+$",
    r"(a|aa)+$",
    r"(.*)*$",
    r"([a-zA-Z]+)*$",
    r"(x+x+)+",
    r"(a*)*c",
]


class TestRegexReDoS:
    @pytest.mark.parametrize("pattern", REDOS_PATTERNS)
    def test_pathological_patterns_rejected(self, pattern):
        assert _validate_regex_pattern(pattern) is None

    @pytest.mark.parametrize(
        "pattern",
        [r"spam\d+", r"free\s+money", r"(buy|cheap)\s+(now|here)", r"\bbtc\b", r"a+x"],
    )
    def test_normal_patterns_accepted(self, pattern):
        assert _validate_regex_pattern(pattern) == pattern

    def test_rejected_pattern_dropped_from_entries(self):
        data = normalize_message_blocklist(
            {"entries": [{"text": r"(x+x+)+y", "match_mode": "regex"}]}
        )
        assert data["entries"] == []

    def test_redos_never_reaches_match(
        self,
    ):
        bl = normalize_message_blocklist(
            {
                "match_message": True,
                "entries": [{"text": r"(x+x+)+y", "match_mode": "regex"}],
            }
        )
        assert first_matching_blocklist_entry(bl, "", message_haystack="x" * 60) is None


class TestNormalizeIdempotent:
    @given(
        scope=st.one_of(st.none(), st.text(max_size=20)),
        text=st.text(max_size=60),
        mode=st.sampled_from(["substring", "regex", "other", None]),
        enabled=st.booleans(),
    )
    @settings(max_examples=100, deadline=3000)
    def test_normalize_idempotent(self, scope, text, mode, enabled):
        data = {
            "scope": scope,
            "entries": [{"text": text, "match_mode": mode, "enabled": enabled}],
        }
        once = normalize_message_blocklist(data)
        twice = normalize_message_blocklist(once)
        assert once == twice

    def test_entry_id_stable_across_normalize(self):
        data = {"entries": [{"text": "spam", "id": "abc123"}]}
        once = normalize_message_blocklist(data)
        twice = normalize_message_blocklist(once)
        assert once["entries"][0]["id"] == twice["entries"][0]["id"] == "abc123"


class TestExportImportRoundtrip:
    def test_export_import_preserves_semantics(self):
        bl = normalize_message_blocklist(
            {
                "scope": "everyone",
                "match_peer_fields": True,
                "match_message": True,
                "entries": [
                    {"text": "spam phrase", "match_mode": "substring", "enabled": True},
                    {"text": r"bad\d+", "match_mode": "regex", "enabled": False},
                ],
            }
        )
        doc = build_export_document(bl)
        imported = parse_import_document(doc)
        assert imported["scope"] == bl["scope"]
        assert imported["match_peer_fields"] == bl["match_peer_fields"]
        assert imported["match_message"] == bl["match_message"]
        assert [e["text"] for e in imported["entries"]] == [
            e["text"] for e in bl["entries"]
        ]

    def test_merge_dedups_by_text(self):
        base = normalize_message_blocklist(
            {"entries": [{"text": "Spam", "match_mode": "substring"}]}
        )
        doc = {
            "schema": "meshchatx.message_blocklist",
            "version": 1,
            "entries": [
                {"text": "spam", "match_mode": "substring"},
                {"text": "new term", "match_mode": "substring"},
            ],
        }
        merged = parse_import_document(doc, merge=True, existing=base)
        texts = [e["text"].lower() for e in merged["entries"]]
        assert texts == ["spam", "new term"]


class TestMatchingSemantics:
    def test_case_insensitive_substring(self):
        bl = normalize_message_blocklist(
            {"match_message": True, "entries": [{"text": "SPAM"}]}
        )
        assert (
            first_matching_blocklist_entry(bl, "", message_haystack="you spam me")
            is not None
        )

    def test_disabled_entry_never_matches(self):
        bl = normalize_message_blocklist(
            {"match_message": True, "entries": [{"text": "spam", "enabled": False}]}
        )
        assert first_matching_blocklist_entry(bl, "", message_haystack="spam") is None

    def test_regex_match(self):
        bl = normalize_message_blocklist(
            {
                "match_message": True,
                "entries": [{"text": r"\bfree\s+money\b", "match_mode": "regex"}],
            }
        )
        assert (
            first_matching_blocklist_entry(bl, "", message_haystack="Free money now")
            is not None
        )
