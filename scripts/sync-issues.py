#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Sync GitHub issues to rngit work documents over Reticulum.

rngit calls issues "work documents". They live on the repository node and
are addressed per repo: rns://<node>/<group>/<repo>. Each document has an
active or completed scope, signed content, and threaded comments.

This script maps GitHub issues onto them:

  - title:   "[GH#<number>] <title>" so dedup survives list truncation
  - content: issue body plus an attribution footer with the source URL
  - state:   open -> active, closed -> completed
  - comments: appended as work-document updates when --comments is passed,
    deduplicated with a "<!-- gh-comment:<id> -->" marker

Usage:

  scripts/sync-issues.py --dry-run
  scripts/sync-issues.py
  scripts/sync-issues.py --state all --comments
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field

GH_MARKER = "GH#"
GH_MARKER_RE = re.compile(r"\bGH#(\d+)\b")
GH_COMMENT_MARKER = "<!-- gh-comment:"
GH_COMMENT_MARKER_RE = re.compile(r"<!--\s*gh-comment:(\S+)\s*-->")

MAX_TITLE = 140


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable, no network)
# ---------------------------------------------------------------------------


def issue_title(issue: dict) -> str:
    number = issue["number"]
    title = str(issue.get("title") or "untitled").strip() or "untitled"
    title = title.replace("\n", " ").strip()
    out = f"[{GH_MARKER}{number}] {title}"
    return out[:MAX_TITLE]


def issue_content(issue: dict, repo: str) -> str:
    body = str(issue.get("body") or "").strip()
    number = issue["number"]
    author = (issue.get("author") or {}).get("login") or "unknown"
    state = str(issue.get("state") or "").lower()
    labels = (
        ", ".join(label.get("name", "") for label in issue.get("labels") or [])
        or "none"
    )
    url = issue.get("url") or f"https://github.com/{repo}/issues/{number}"
    created = (issue.get("createdAt") or "")[:10]
    parts = [
        body or "_(no description)_",
        "",
        "---",
        "",
        f"Synced from GitHub issue #{number}: {url}",
        f"Author: @{author} | State: {state} | Labels: {labels}",
    ]
    if created:
        parts.append(f"Created: {created}")
    return "\n".join(parts).strip() + "\n"


def comment_content(comment: dict) -> str:
    cid = str(comment.get("id") or comment.get("databaseId") or "0")
    author = (comment.get("author") or {}).get("login") or "unknown"
    created = (comment.get("createdAt") or "")[:19].replace("T", " ")
    body = str(comment.get("body") or "").strip()
    header = f"@{author}"
    if created:
        header += f" on {created}"
    return f"{GH_COMMENT_MARKER}{cid} -->\n**{header}:**\n\n{body}\n"


def doc_gh_number(doc: dict) -> int | None:
    m = GH_MARKER_RE.search(str(doc.get("title") or ""))
    return int(m.group(1)) if m else None


@dataclass
class Plan:
    creates: list = field(default_factory=list)
    completes: list = field(default_factory=list)
    activates: list = field(default_factory=list)
    comments: list = field(default_factory=list)


def plan_sync(issues: list, docs: list) -> Plan:
    """Map GitHub issue state onto rngit work document state.

    issues: gh issue list JSON items (number, title, state, ...)
    docs:   rngit list result items across all scopes (id, title, _scope)
    """
    existing = {}
    for doc in docs:
        n = doc_gh_number(doc)
        if n is not None:
            existing[n] = doc

    plan = Plan()
    for issue in issues:
        num = issue["number"]
        gh_open = str(issue.get("state") or "").lower() in ("open", "opened")
        doc = existing.get(num)
        if doc is None:
            plan.creates.append(issue)
            if not gh_open:
                # create first, complete after we know the doc id
                plan.completes.append({"after_create": num})
            continue
        doc_scope = doc.get("_scope", "active")
        if gh_open and doc_scope == "completed":
            plan.activates.append(doc)
        elif not gh_open and doc_scope == "active":
            plan.completes.append(doc)
    return plan


def missing_comments(gh_comments: list, doc_comments: list) -> list:
    """Return GitHub comments not yet present as work-doc updates."""
    seen = set()
    for c in doc_comments or []:
        m = GH_COMMENT_MARKER_RE.search(str(c.get("content") or ""))
        if m:
            seen.add(m.group(1))
    out = []
    for c in gh_comments or []:
        cid = str(c.get("id") or c.get("databaseId") or "0")
        if cid not in seen:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# rngit client wrapper (one Reticulum link for the whole run)
# ---------------------------------------------------------------------------


class RngitError(RuntimeError):
    pass


class RngitWorkClient:
    def __init__(
        self, remote, rnsconfig=None, rngit_config=None, identity=None, verbosity=0
    ):
        import RNS
        from RNS.Utilities.rngit.server import ReticulumGitClient

        self._RNS = RNS
        RNS.Reticulum(configdir=rnsconfig, verbosity=verbosity)
        self.client = ReticulumGitClient(
            configdir=rngit_config, verbosity=verbosity, identitypath=identity
        )
        self.remote = remote
        _, group, repo = self.client.parse_remote_url(remote)
        self.repo_path = f"{group}/{repo}"

    def connect(self, timeout=None):
        try:
            self.client.connect_remote(self.remote)
        except SystemExit as e:
            raise RngitError(f"connect failed ({e})") from e
        limit = self.client.link_timeout if timeout is None else timeout
        waited = 0.0
        while (
            not self.client.link_ready
            and not self.client.link_failed
            and waited < limit
        ):
            time.sleep(self.client.wait_sleep)
            waited += self.client.wait_sleep
        if not self.client.link_ready:
            raise RngitError("link establishment failed")

    def close(self):
        link = getattr(self.client, "link", None)
        if link is not None:
            link.teardown()

    def request(self, operation, timeout=120, **kw):
        data = {self.client.IDX_REPOSITORY: self.repo_path, "operation": operation}
        data.update(kw)
        try:
            response, _metadata = self.client.send_request(
                self.client.PATH_WORK, data, timeout=timeout
            )
        except SystemExit as e:
            raise RngitError(f"request {operation} failed ({e})") from e
        if not response:
            raise RngitError(f"request {operation}: no response")
        status = response[0]
        if status != 0:
            raise RngitError(
                f"request {operation}: remote error: {response[1:].decode('utf-8', 'replace')}"
            )
        if len(response) > 1:
            from RNS.vendor import umsgpack

            return umsgpack.unpackb(response[1:])
        return {}

    def list_docs(self):
        result = self.request("list", scope="all")
        docs = []
        for scope in ("active", "completed", "proposed"):
            for doc in result.get(scope, []) or []:
                doc["_scope"] = scope
                docs.append(doc)
        return docs

    def view_doc(self, doc_id, scope="active"):
        return self.request("view", doc_id=doc_id, scope=scope)

    def create_doc(self, title, content):
        # the node strips content before validating the signature, so sign
        # the stripped form exactly as it will verify it
        content = content.strip()
        signature = self.client.identity.sign(content.encode("utf-8"))
        if not signature:
            raise RngitError("could not sign work document")
        return self.request(
            "create",
            title=title.strip(),
            content=content,
            format="markdown",
            signature=signature,
            timeout=600,
        )

    def edit_doc(self, doc_id, title, content, scope="active"):
        content = content.strip()
        signature = self.client.identity.sign(content.encode("utf-8"))
        if not signature:
            raise RngitError("could not sign work document")
        return self.request(
            "edit",
            doc_id=doc_id,
            scope=scope,
            title=title.strip(),
            content=content,
            signature=signature,
            timeout=600,
        )

    def delete_doc(self, doc_id, scope="active"):
        # note: node-side delete in rns 1.5.2 fails with "Remote error" for
        # documents that have no <id>.allowed perms file, because the handler
        # returns early when unlinking that optional file raises. complete the
        # doc instead of deleting when this fails.
        return self.request("delete", doc_id=doc_id, scope=scope)

    def comment(self, doc_id, content, scope="active"):
        return self.request(
            "comment",
            doc_id=doc_id,
            scope=scope,
            content=content,
            format="markdown",
            timeout=600,
        )

    def complete(self, doc_id):
        return self.request("complete", doc_id=doc_id)

    def activate(self, doc_id):
        return self.request("activate", doc_id=doc_id)


# ---------------------------------------------------------------------------
# GitHub side
# ---------------------------------------------------------------------------


def fetch_issues(repo, state="open", limit=500, with_comments=False):
    fields = [
        "number",
        "title",
        "state",
        "body",
        "labels",
        "author",
        "url",
        "createdAt",
        "closedAt",
    ]
    if with_comments:
        fields.append("comments")
    out = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            ",".join(fields),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout or "[]")


def default_repo():
    out = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True,
        text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        raise RngitError("could not resolve GitHub repo, pass --repo")
    return out.stdout.strip()


def default_remote():
    out = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        m = re.search(r"rns://[0-9a-fA-F]+/\S+/\S+", line)
        if m:
            return m.group(0)
    raise RngitError("no rns:// git remote found, pass --remote")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Sync GitHub issues to rngit work documents"
    )
    ap.add_argument("--repo", default=None, help="GitHub repo (default: current)")
    ap.add_argument(
        "--remote", default=None, help="rns:// remote (default: current rns remote)"
    )
    ap.add_argument(
        "--state",
        default="open",
        choices=["open", "closed", "all"],
        help="issue state filter",
    )
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument(
        "--comments",
        action="store_true",
        help="also sync issue comments as doc updates",
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="show the plan without touching the node"
    )
    ap.add_argument(
        "--rnsconfig", default=None, help="Reticulum config dir (default ~/.reticulum)"
    )
    ap.add_argument(
        "--rngit-config", default=None, help="rngit config dir (default ~/.rngit)"
    )
    ap.add_argument(
        "--identity",
        default=None,
        help="client identity path (default ~/.rngit/client_identity)",
    )
    ap.add_argument("-v", "--verbose", action="count", default=0)
    args = ap.parse_args(argv)

    repo = args.repo or default_repo()
    remote = args.remote or default_remote()

    issues = fetch_issues(
        repo, state=args.state, limit=args.limit, with_comments=args.comments
    )
    print(f"{len(issues)} GitHub issues ({args.state}) from {repo}")

    client = RngitWorkClient(
        remote,
        rnsconfig=args.rnsconfig,
        rngit_config=args.rngit_config,
        identity=args.identity,
        verbosity=args.verbose,
    )
    print(f"connecting to {remote} ...")
    client.connect()
    print("link established")

    try:
        docs = client.list_docs()
        print(f"{len(docs)} existing work documents on node")
        plan = plan_sync(issues, docs)

        if args.dry_run:
            for issue in plan.creates:
                print(f"would create: {issue_title(issue)}")
            for item in plan.completes:
                ref = item.get("id") or f"new GH#{item.get('after_create')}"
                print(f"would complete: doc {ref}")
            for doc in plan.activates:
                print(f"would re-activate: doc #{doc['id']}")
            print(
                f"dry run: {len(plan.creates)} creates, "
                f"{len(plan.completes)} completes, {len(plan.activates)} activates"
            )
            return 0

        created_ids = {}
        for issue in plan.creates:
            num = issue["number"]
            result = client.create_doc(issue_title(issue), issue_content(issue, repo))
            doc_id = result.get("id")
            scope = result.get("scope", "active")
            created_ids[num] = (doc_id, scope)
            print(f"created #{doc_id}: {issue_title(issue)}")

        for item in plan.completes:
            doc_id = item.get("id") if isinstance(item, dict) and "id" in item else None
            if doc_id is None and isinstance(item, dict) and "after_create" in item:
                doc_id = created_ids.get(item["after_create"], (None,))[0]
            if doc_id is None:
                continue
            client.complete(doc_id)
            print(f"completed doc #{doc_id}")

        for doc in plan.activates:
            client.activate(doc["id"])
            print(f"re-activated doc #{doc['id']}")

        if args.comments:
            for issue in issues:
                gh_comments = issue.get("comments") or []
                if not gh_comments:
                    continue
                num = issue["number"]
                doc_id, scope = created_ids.get(num, (None, None))
                if doc_id is None:
                    for doc in docs:
                        if doc_gh_number(doc) == num:
                            doc_id, scope = doc["id"], doc["_scope"]
                            break
                if doc_id is None:
                    continue
                doc = client.view_doc(doc_id, scope=scope)
                for c in missing_comments(gh_comments, doc.get("comments", [])):
                    client.comment(doc_id, comment_content(c), scope=scope)
                    print(f"  comment on doc #{doc_id} (GH#{num})")

        print(
            f"done: {len(plan.creates)} created, "
            f"{len(plan.completes)} completed, "
            f"{len(plan.activates)} re-activated"
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
