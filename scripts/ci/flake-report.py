#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Aggregate JUnit XML results across runs into a flakiness report.

Reads every *.xml under the given directory, groups testcases by name,
and reports pass/fail counts so intermittent tests are visible instead
of silently retried.

Usage: flake-report.py DIR [--min-runs 3] [--json]
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def iter_cases(path):
    try:
        tree = ET.parse(path)  # noqa: S314 - CI-generated junit only
    except ET.ParseError:
        return
    for case in tree.iter("testcase"):
        name = case.get("classname", "") + "::" + case.get("name", "")
        failed = (
            case.find("failure") is not None
            or case.find("error") is not None
            or case.find("flakyFailure") is not None
        )
        skipped = case.find("skipped") is not None
        yield name, failed, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("--min-runs", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    stats = defaultdict(lambda: {"runs": 0, "fails": 0, "skips": 0})
    for xml in sorted(args.dir.rglob("*.xml")):
        for name, failed, skipped in iter_cases(xml):
            st = stats[name]
            st["runs"] += 1
            st["fails"] += int(failed)
            st["skips"] += int(skipped)

    rows = [
        (name, s)
        for name, s in stats.items()
        if s["runs"] >= args.min_runs and s["fails"] > 0
    ]
    rows.sort(key=lambda r: r[1]["fails"] / r[1]["runs"], reverse=True)

    if args.json:
        print(json.dumps(dict(rows), indent=2))
        return 0
    if not rows:
        print(f"no flaky tests in {args.dir} (min-runs={args.min_runs})")
        return 0
    print(f"flaky tests in {args.dir}:")
    for name, s in rows[:50]:
        rate = 100.0 * s["fails"] / s["runs"]
        print(f"  {rate:5.0f}% fail ({s['fails']}/{s['runs']})  {name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
