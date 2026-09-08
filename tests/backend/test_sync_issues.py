# SPDX-License-Identifier: 0BSD
"""Oracles for scripts/sync-issues.py pure helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync-issues.py"
spec = importlib.util.spec_from_file_location("sync_issues", SCRIPT)
sync = importlib.util.module_from_spec(spec)
sys.modules.setdefault("sync_issues", sync)
spec.loader.exec_module(sync)


def _issue(number, state="open", title="Some bug", body="body text", comments=None):
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "labels": [{"name": "bug"}],
        "author": {"login": "octocat"},
        "url": f"https://github.com/x/y/issues/{number}",
        "createdAt": "2026-09-08T21:00:00Z",
        "comments": comments or [],
    }


def test_issue_title_has_gh_marker():
    t = sync.issue_title(_issue(94, title="Broken thing"))
    assert t == "[GH#94] Broken thing"


def test_issue_title_truncates_and_strips_newlines():
    t = sync.issue_title(_issue(7, title="line\nbreak " + "x" * 300))
    assert "\n" not in t
    assert len(t) <= sync.MAX_TITLE


def test_issue_content_carries_attribution():
    c = sync.issue_content(_issue(94), "Quad4-Software/MeshChatX")
    assert "GH#" not in c
    assert "github.com/x/y/issues/94" in c
    assert "@octocat" in c
    assert "bug" in c
    assert "body text" in c


def test_comment_content_marker():
    c = sync.comment_content(
        {
            "id": 123,
            "author": {"login": "a"},
            "createdAt": "2026-09-08T00:00:00Z",
            "body": "hi",
        }
    )
    assert "gh-comment:123" in c
    assert "@a" in c
    assert "hi" in c


def test_doc_gh_number_parses_marker():
    assert sync.doc_gh_number({"title": "[GH#42] whatever"}) == 42
    assert sync.doc_gh_number({"title": "no marker"}) is None
    assert sync.doc_gh_number({"title": None}) is None


def test_plan_creates_missing_docs():
    issues = [_issue(1), _issue(2, state="closed")]
    plan = sync.plan_sync(issues, [])
    assert [i["number"] for i in plan.creates] == [1, 2]
    # closed issue must be completed after creation
    assert plan.completes == [{"after_create": 2}]
    assert plan.activates == []


def test_plan_skips_existing_matching_state():
    docs = [
        {"id": 10, "title": "[GH#1] Some bug", "_scope": "active"},
        {"id": 11, "title": "[GH#2] Other", "_scope": "completed"},
    ]
    issues = [_issue(1), _issue(2, state="closed")]
    plan = sync.plan_sync(issues, docs)
    assert plan.creates == []
    assert plan.completes == []
    assert plan.activates == []


def test_plan_reconciles_state_mismatch():
    docs = [
        {"id": 10, "title": "[GH#1] Some bug", "_scope": "completed"},
        {"id": 11, "title": "[GH#2] Other", "_scope": "active"},
    ]
    issues = [_issue(1), _issue(2, state="closed")]
    plan = sync.plan_sync(issues, docs)
    assert plan.creates == []
    assert [d["id"] for d in plan.activates] == [10]
    assert [d["id"] for d in plan.completes] == [11]


def test_missing_comments_dedup_by_marker():
    gh = [{"id": 1, "body": "a"}, {"id": 2, "body": "b"}]
    existing = [{"content": "<!-- gh-comment:1 -->\n**@x:** a"}]
    out = sync.missing_comments(gh, existing)
    assert [c["id"] for c in out] == [2]


def test_missing_comments_empty_inputs():
    assert sync.missing_comments([], []) == []
    assert sync.missing_comments([{"id": 9}], []) == [{"id": 9}]
