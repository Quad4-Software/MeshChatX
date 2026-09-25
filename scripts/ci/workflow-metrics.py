#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Summarize workflow run durations and failure rates over the last N days.

Writes a markdown table to $GITHUB_STEP_SUMMARY (falls back to stdout).
Requires the gh CLI authenticated against $GITHUB_REPOSITORY.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta


def gh(endpoint: str) -> list[dict]:
    out = subprocess.run(
        [shutil.which("gh") or "gh", "api", "--paginate", endpoint],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        print(f"gh api failed for {endpoint}: {out.stderr.strip()}", file=sys.stderr)
        return []
    # --paginate concatenates JSON page objects; parse them one at a time.
    pages: list[dict] = []
    decoder = json.JSONDecoder()
    text = out.stdout
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        idx = end
        if isinstance(obj, dict):
            pages.append(obj)
    return pages


def parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def fmt_duration(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m{secs:02d}s"


def main() -> int:
    days = int(os.environ.get("METRICS_DAYS", "7"))
    repo = os.environ["GITHUB_REPOSITORY"]
    out_path = os.environ.get("GITHUB_STEP_SUMMARY")
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")

    lines = [
        f"# CI metrics (last {days} days, since {since})",
        "",
        "| Workflow | Runs | Failures | Success rate | Median duration |",
        "|---|---|---|---|---|",
    ]

    workflows: list[str] = []
    for page in gh(f"repos/{repo}/actions/workflows"):
        for wf in page.get("workflows") or []:
            path = wf.get("path")
            if path:
                workflows.append(str(path).rsplit("/", 1)[-1])

    for wf_id in sorted(set(workflows)):
        runs = []
        for page in gh(
            f"repos/{repo}/actions/workflows/{wf_id}/runs?created=%3E%3D{since}&per_page=100",
        ):
            runs.extend(page.get("workflow_runs") or [])

        total = len(runs)
        fails = sum(
            1
            for r in runs
            if r.get("conclusion") in ("failure", "timed_out", "cancelled")
        )
        durs = []
        for run in runs:
            if run.get("conclusion") != "success":
                continue
            started = parse_ts(run.get("run_started_at") or "")
            finished = parse_ts(run.get("updated_at") or "")
            if started and finished and finished > started:
                durs.append((finished - started).total_seconds())
        durs.sort()
        median = durs[len(durs) // 2] if durs else 0.0
        rate = (100.0 * (total - fails) / total) if total else 100.0
        name = wf_id.rsplit(".", 1)[0]
        lines.append(
            f"| `{name}` | {total} | {fails} | {rate:.0f}% | {fmt_duration(median)} |",
        )

    report = "\n".join(lines) + "\n"
    if out_path:
        with open(out_path, "a", encoding="utf-8") as handle:
            handle.write(report)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
