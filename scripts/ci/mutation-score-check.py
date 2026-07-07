#!/usr/bin/env python3
"""Check mutation score thresholds for mutmut or MeshMut reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-score",
        type=float,
        required=True,
        help="Minimum acceptable mutation score percentage (0-100)",
    )
    parser.add_argument(
        "--mutmut-stats",
        type=Path,
        help="Path to mutmut export-cicd-stats JSON file",
    )
    parser.add_argument(
        "--meshmut-report",
        type=Path,
        help="Path to MeshMut JSON report",
    )
    return parser.parse_args()


def score_from_mutmut(payload: dict) -> float | None:
    killed = int(payload.get("killed", 0))
    survived = int(payload.get("survived", 0))
    timeout = int(payload.get("timeout", 0))
    suspicious = int(payload.get("suspicious", 0))
    evaluated = killed + survived + timeout + suspicious
    if evaluated == 0:
        return None
    return (killed / evaluated) * 100.0


def score_from_meshmut(payload: dict) -> float | None:
    summary = payload.get("summary") or {}
    score = summary.get("score")
    if score is not None:
        return float(score)
    killed = int(summary.get("killed", 0))
    survived = int(summary.get("survived", 0))
    evaluated = killed + survived
    if evaluated == 0:
        return None
    return (killed / evaluated) * 100.0


def main() -> int:
    args = parse_args()

    if not args.mutmut_stats and not args.meshmut_report:
        print("Provide --mutmut-stats and/or --meshmut-report", file=sys.stderr)
        return 1

    exit_code = 0

    if args.mutmut_stats:
        if not args.mutmut_stats.is_file():
            print(f"Missing mutmut stats: {args.mutmut_stats}", file=sys.stderr)
            return 1
        score = score_from_mutmut(
            json.loads(args.mutmut_stats.read_text(encoding="utf-8"))
        )
        if score is None:
            print("No scored mutmut results.", file=sys.stderr)
            return 1
        print(f"Backend mutation score: {score:.1f}% (minimum: {args.min_score:.1f}%)")
        if score < args.min_score:
            exit_code = 1

    if args.meshmut_report:
        if not args.meshmut_report.is_file():
            print(f"Missing MeshMut report: {args.meshmut_report}", file=sys.stderr)
            return 1
        score = score_from_meshmut(
            json.loads(args.meshmut_report.read_text(encoding="utf-8"))
        )
        if score is None:
            print("No scored MeshMut results.", file=sys.stderr)
            return 1
        print(f"Frontend mutation score: {score:.1f}% (minimum: {args.min_score:.1f}%)")
        if score < args.min_score:
            exit_code = 1

    if exit_code != 0:
        print("Mutation score below threshold.", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
