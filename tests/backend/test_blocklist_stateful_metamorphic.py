# SPDX-License-Identifier: 0BSD
"""Metamorphic: export -> import -> export is a fixed point for blocklists."""

import pytest

from meshchatx.src.backend.message_blocklist import (
    build_export_document,
    normalize_message_blocklist,
    parse_import_document,
)


def _doc(entry_dicts, **kw):
    return normalize_message_blocklist({"entries": entry_dicts, **kw})


class TestExportImportFixedPoint:
    @pytest.mark.parametrize(
        "entries",
        [
            [{"text": "spam"}],
            [{"text": "re+", "match_mode": "regex", "enabled": False}],
            [{"text": "a" * 500}],  # over-length term gets truncated
            [{"text": "  padded  "}, {"text": "second", "enabled": False}],
            [{"text": "dup"}, {"text": "DUP"}],  # case variants both kept
        ],
    )
    def test_export_import_export_roundtrip(self, entries):
        doc1 = build_export_document(_doc(entries))
        reimported = parse_import_document(doc1)
        assert reimported is not None
        doc2 = build_export_document(reimported)
        assert doc1 == doc2

    def test_import_merge_no_duplicate_terms(self):
        existing = _doc([{"text": "Alpha"}, {"text": "beta"}])
        incoming = build_export_document(_doc([{"text": "BETA"}, {"text": "gamma"}]))
        merged = parse_import_document(incoming, merge=True, existing=existing)
        texts = [e["text"] for e in merged["entries"]]
        assert texts == ["Alpha", "beta", "gamma"]

    def test_import_merge_is_idempotent(self):
        existing = _doc([{"text": "one"}])
        incoming = build_export_document(_doc([{"text": "two"}, {"text": "THREE"}]))
        m1 = parse_import_document(incoming, merge=True, existing=existing)
        m2 = parse_import_document(incoming, merge=True, existing=m1)
        assert build_export_document(m1) == build_export_document(m2)


class TestImportRejectsGarbage:
    @pytest.mark.parametrize(
        "doc",
        [
            None,
            "not a dict",
            [],
            {"schema": "other.schema"},
            {"version": 999},
            {"version": "abc"},
            {"entries": [{"text": 0}]},  # falsy text normalizes away -> empty ok
        ],
    )
    def test_no_crash(self, doc):
        out = parse_import_document(doc)
        if out is not None:
            # If accepted, must be fully normalized and re-exportable.
            build_export_document(out)
