#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Per-module coverage floors on top of the global --fail-under gate.

Reads `coverage json` output and fails if any protected path glob drops
below its floor. Floors sit ~5 points under current measured coverage so
the ratchet only trips on real regressions, not noise.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
import sys

FLOORS: list[tuple[str, float]] = [
    ("meshchatx/src/backend/recovery/*", 50),
    ("meshchatx/src/backend/plugin_manager.py", 55),
    ("meshchatx/src/backend/http/*", 50),
    ("meshchatx/src/backend/websocket*", 40),
]


def main() -> int:
    proc = subprocess.run(
        ["uv", "run", "coverage", "json", "-o", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or "coverage json failed", file=sys.stderr)
        return 1
    data = json.loads(proc.stdout)

    failures = []
    for pattern, floor in FLOORS:
        covered = stmts = 0
        for path, fdata in data.get("files", {}).items():
            if not fnmatch.fnmatch(path, pattern):
                continue
            summary = fdata.get("summary", {})
            stmts += summary.get("num_statements", 0)
            covered += summary.get("covered_lines", 0)
        if stmts == 0:
            continue
        pct = 100.0 * covered / stmts
        status = "ok" if pct >= floor else "FAIL"
        print(f"{pattern}: {pct:.1f}% (floor {floor}%) {status}")
        if pct < floor:
            failures.append(pattern)

    if failures:
        print(f"coverage-floors: {len(failures)} path(s) below floor", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
