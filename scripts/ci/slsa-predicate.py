#!/usr/bin/env python3
"""Emit a SLSA v1 provenance predicate JSON on stdout (stdin unused)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _source_uri() -> str:
    server = (
        os.environ.get("GITHUB_SERVER_URL") or os.environ.get("GITEA_SERVER_URL") or ""
    ).rstrip("/")
    repo = (
        os.environ.get("GITHUB_REPOSITORY") or os.environ.get("GITEA_REPOSITORY") or ""
    )
    if not server or not repo:
        return ""
    if server.startswith("https://") or server.startswith("http://"):
        return f"git+{server}/{repo}.git"
    return f"git+https://{server}/{repo}.git"


def _build_type() -> str:
    custom = os.environ.get("PROVENANCE_BUILD_TYPE")
    if custom:
        return custom
    server = (
        os.environ.get("GITHUB_SERVER_URL") or os.environ.get("GITEA_SERVER_URL") or ""
    ).rstrip("/")
    repo = (
        os.environ.get("GITHUB_REPOSITORY") or os.environ.get("GITEA_REPOSITORY") or ""
    )
    if server and repo:
        return f"{server}/{repo}/.gitea/workflows/build.yml"
    return "https://slsa.dev/provenance/v1"


def _builder_id() -> str:
    custom = os.environ.get("PROVENANCE_BUILDER_ID")
    if custom:
        return custom
    server = (
        os.environ.get("GITHUB_SERVER_URL") or os.environ.get("GITEA_SERVER_URL") or ""
    ).rstrip("/")
    if server:
        return f"{server}/actions"
    return "https://gitea.io/actions/runner"


def main() -> None:
    ref = os.environ.get("GITHUB_REF", "")
    sha = os.environ.get("GITHUB_SHA", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    workflow = os.environ.get("GITHUB_WORKFLOW", "")
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    internal = {}
    if workflow:
        internal["workflow"] = workflow

    predicate = {
        "buildDefinition": {
            "buildType": _build_type(),
            "externalParameters": {
                "source": _source_uri(),
                "ref": ref,
                "revision": sha,
            },
            "internalParameters": internal,
            "resolvedDependencies": [],
        },
        "runDetails": {
            "builder": {"id": _builder_id()},
            "metadata": {
                "invocationId": f"{run_id}-{attempt}",
                "startedOn": started,
            },
        },
    }
    print(json.dumps(predicate, separators=(",", ":")))


if __name__ == "__main__":
    main()
