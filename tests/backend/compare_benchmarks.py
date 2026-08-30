# SPDX-License-Identifier: 0BSD
"""Smart benchmark regression gate for CI.

github-action-benchmark only supports a single ratio threshold. Sub-millisecond
SQLite ops on shared runners routinely swing 2-3x from scheduler noise, so a
flat ratio alert is useless. This script:

1. Loads current suite JSON (customSmallerIsBetter) and the cached baseline.
2. Applies noise-floor, absolute-delta, and adaptive-ratio heuristics.
3. Writes a human-readable summary and exits non-zero only on real regressions.
4. Optionally updates the baseline cache when the run is clean (or always when
   --update-baseline is set), so the next push compares against a stable
   median rather than a single noisy sample.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _REPO_ROOT)

from tests.backend.benchmarking_utils import (
    parse_extra_stats,
    should_alert_regression,
)

# Must stay present in comprehensive suite runs. Gate fails if a full-suite
# baseline is missing any of these from the current JSON.
REQUIRED_BENCHES = frozenset(
    {
        "Database Initialization",
        "Message Upsert (Batch of 100)",
        "Get 100 Conversations List",
        "Get Conversations Slim List (handler)",
        "Get Conversations Unread Filter (handler)",
        "Mark Conversation As Read",
        "Get Messages for Conversation (offset 500)",
        "Log Telephone Call",
        "Get Call History List",
        "Notification Add + Unread Count",
        "Missed Call Unread Count by Type",
        "Dismiss Missed Call Notifications",
        "Config Get (50 keys)",
        "Get Contacts List",
    },
)


def _is_full_suite_baseline(previous):
    """True when previous looks like the comprehensive suite, not a unit fixture."""
    return "Database Initialization" in previous


def _load_entries(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # github-action-benchmark external-data shape
        if "entries" in data and isinstance(data["entries"], dict):
            # Prefer the first suite key (usually the tool name)
            for _suite, entries in data["entries"].items():
                if isinstance(entries, list) and entries:
                    # Prefer the newest commit's last values: entries are
                    # historical lists of {commit, date, tool, benches}
                    latest = entries[-1]
                    benches = latest.get("benches") or latest.get("benchmarks")
                    if isinstance(benches, list):
                        return benches
                    if isinstance(latest, list):
                        return latest
        if "benches" in data and isinstance(data["benches"], list):
            return data["benches"]
    raise ValueError(f"Unrecognized benchmark JSON shape in {path}")


def _index_by_name(entries):
    out = {}
    for entry in entries:
        name = entry.get("name")
        if not name:
            continue
        out[name] = entry
    return out


def _value_ms(entry):
    return float(entry["value"])


def compare(
    current_path,
    previous_path,
    *,
    noise_floor_ms=0.5,
    min_abs_delta_ms=1.5,
    summary_path=None,
):
    current = _index_by_name(_load_entries(current_path))
    previous = {}
    if previous_path and os.path.isfile(previous_path):
        try:
            previous = _index_by_name(_load_entries(previous_path))
        except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
            print(
                f"WARNING: could not load previous baseline ({exc}); treating as first run",
            )
            previous = {}

    rows = []
    alerts = []
    improvements = []
    skipped = []
    coverage_alerts = []
    enforce_coverage = _is_full_suite_baseline(previous)

    for name in sorted(current):
        cur = current[name]
        cur_ms = _value_ms(cur)
        cur_stats = parse_extra_stats(cur.get("extra", ""))
        prev = previous.get(name)
        if prev is None:
            rows.append(
                {
                    "name": name,
                    "current": cur_ms,
                    "previous": None,
                    "ratio": None,
                    "status": "new",
                    "detail": "no previous baseline",
                },
            )
            continue

        prev_ms = _value_ms(prev)
        prev_stats = parse_extra_stats(prev.get("extra", ""))
        ratio = cur_ms / prev_ms if prev_ms > 0 else None
        alert, detail = should_alert_regression(
            cur_ms,
            prev_ms,
            noise_floor_ms=noise_floor_ms,
            min_abs_delta_ms=min_abs_delta_ms,
            current_cv=cur_stats.get("cv"),
            previous_cv=prev_stats.get("cv"),
        )
        if alert:
            status = "REGRESSION"
            alerts.append(name)
        elif (
            ratio is not None
            and ratio < 0.85
            and (prev_ms - cur_ms) >= min_abs_delta_ms
        ):
            status = "improved"
            improvements.append(name)
        elif (
            "noise floor" in detail
            or "abs delta" in detail
            or "within adaptive" in detail
        ):
            status = "noise"
            skipped.append(name)
        else:
            status = "ok"

        rows.append(
            {
                "name": name,
                "current": cur_ms,
                "previous": prev_ms,
                "ratio": ratio,
                "status": status,
                "detail": detail,
            },
        )

    missing = sorted(set(previous) - set(current))
    coverage_seen = set()
    for name in missing:
        detail = "present in baseline only"
        status = "removed"
        if enforce_coverage:
            coverage_alerts.append(name)
            coverage_seen.add(name)
            if name in REQUIRED_BENCHES:
                status = "MISSING"
                detail = "required bench absent from current suite"
            else:
                status = "REMOVED"
                detail = "dropped from suite vs full baseline"
        rows.append(
            {
                "name": name,
                "current": None,
                "previous": _value_ms(previous[name]),
                "ratio": None,
                "status": status,
                "detail": detail,
            },
        )

    check_required = enforce_coverage or (
        not previous and "Database Initialization" in current
    )
    if check_required:
        for name in sorted(REQUIRED_BENCHES - set(current) - coverage_seen):
            coverage_alerts.append(name)
            rows.append(
                {
                    "name": name,
                    "current": None,
                    "previous": (
                        _value_ms(previous[name]) if name in previous else None
                    ),
                    "ratio": None,
                    "status": "MISSING",
                    "detail": "required bench absent from current suite",
                },
            )

    lines = [
        "MeshChatX Backend Benchmark Gate",
        f"Current:  {current_path}",
        f"Previous: {previous_path or '(none)'}",
        f"Noise floor: {noise_floor_ms} ms | Min abs delta: {min_abs_delta_ms} ms",
        f"Coverage enforce: {'yes' if check_required else 'no'}",
        "",
        f"{'Benchmark':42} {'Curr':>10} {'Prev':>10} {'Ratio':>8}  Status",
        "-" * 90,
    ]
    for row in rows:
        cur_s = f"{row['current']:.3f}" if row["current"] is not None else "-"
        prev_s = f"{row['previous']:.3f}" if row["previous"] is not None else "-"
        ratio_s = f"{row['ratio']:.2f}x" if row["ratio"] is not None else "-"
        lines.append(
            f"{row['name'][:42]:42} {cur_s:>10} {prev_s:>10} {ratio_s:>8}  "
            f"{row['status']}",
        )
        if row["status"] in {"REGRESSION", "REMOVED", "MISSING"}:
            lines.append(f"  -> {row['detail']}")

    lines.append("-" * 90)
    lines.append(
        f"Regressions: {len(alerts)} | Improvements: {len(improvements)} | "
        f"Noise-skipped: {len(skipped)} | New: "
        f"{sum(1 for r in rows if r['status'] == 'new')} | "
        f"Coverage: {len(coverage_alerts)}",
    )
    if alerts or coverage_alerts:
        parts = []
        if alerts:
            parts.append("regressions: " + ", ".join(alerts))
        if coverage_alerts:
            parts.append("coverage: " + ", ".join(coverage_alerts))
        lines.append("ALERT: " + " | ".join(parts))
    else:
        lines.append("No actionable regressions.")

    text = "\n".join(lines) + "\n"
    print(text, end="")
    if summary_path:
        os.makedirs(os.path.dirname(summary_path) or ".", exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(text)
        # Also append to GitHub job summary when available
        gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if gh_summary:
            with open(gh_summary, "a", encoding="utf-8") as f:
                f.write("## Benchmark gate\n\n```\n")
                f.write(text)
                f.write("```\n")

    return 1 if (alerts or coverage_alerts) else 0, rows


def update_baseline(
    current_path,
    baseline_path,
    suite_name="MeshChatX Backend Benchmarks",
):
    """Write/merge current results into github-action-benchmark external-data JSON."""
    current_entries = _load_entries(current_path)
    os.makedirs(os.path.dirname(baseline_path) or ".", exist_ok=True)

    commit = os.environ.get("GITHUB_SHA", "local")
    date_ms = int(datetime.now(UTC).timestamp() * 1000)
    record = {
        "commit": {
            "id": commit,
            "message": os.environ.get("BENCHMARK_COMMIT_MESSAGE", "benchmark run"),
            "timestamp": datetime.now(UTC).isoformat(),
            "url": "",
        },
        "date": date_ms,
        "tool": "customSmallerIsBetter",
        "benches": current_entries,
    }

    data = {"lastUpdate": date_ms, "repoUrl": "", "entries": {suite_name: []}}
    if os.path.isfile(baseline_path):
        try:
            with open(baseline_path, encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and "entries" in existing:
                data = existing
        except (OSError, json.JSONDecodeError):
            pass

    entries = data.setdefault("entries", {}).setdefault(suite_name, [])
    # Keep a short history so cache stays small; compare uses the latest.
    entries.append(record)
    data["entries"][suite_name] = entries[-20:]
    data["lastUpdate"] = date_ms

    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Baseline updated: {baseline_path} ({len(current_entries)} metrics)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Smart CI benchmark regression gate")
    parser.add_argument("--current", required=True, help="Current bench JSON path")
    parser.add_argument(
        "--previous",
        default=None,
        help="Previous baseline JSON (github-action-benchmark external-data or flat list)",
    )
    parser.add_argument(
        "--baseline-out",
        default=None,
        help="If set, write/update baseline cache at this path after a clean run",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Always update baseline even when regressions are found",
    )
    parser.add_argument("--noise-floor-ms", type=float, default=0.5)
    parser.add_argument("--min-abs-delta-ms", type=float, default=1.5)
    parser.add_argument("--summary", default=None, help="Write text summary to PATH")
    parser.add_argument(
        "--suite-name",
        default="MeshChatX Backend Benchmarks",
        help="Suite key inside external-data JSON",
    )
    args = parser.parse_args(argv)

    code, _rows = compare(
        args.current,
        args.previous,
        noise_floor_ms=args.noise_floor_ms,
        min_abs_delta_ms=args.min_abs_delta_ms,
        summary_path=args.summary,
    )

    should_update = args.baseline_out and (args.update_baseline or code == 0)
    if should_update:
        update_baseline(args.current, args.baseline_out, suite_name=args.suite_name)
    elif args.baseline_out and code != 0:
        print(
            "Baseline not updated (regressions present). Re-run with --update-baseline to force.",
        )

    return code


if __name__ == "__main__":
    raise SystemExit(main())
