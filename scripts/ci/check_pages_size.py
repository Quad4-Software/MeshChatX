#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Guard a GitHub Pages site tree against the platform size limits.

Usage:
    python3 scripts/ci/check_pages_size.py SITE_DIR

Exits 1 when any single file exceeds MAX_FILE_BYTES or the total site
exceeds MAX_TOTAL_BYTES, and prints the totals either way.
"""

from __future__ import annotations

import os
import sys

MAX_FILE_BYTES = 95 * 1024 * 1024
MAX_TOTAL_BYTES = 900 * 1024 * 1024


def check_tree(root: str) -> tuple[int, int, list[tuple[str, int]]]:
    total = 0
    files = 0
    oversized: list[tuple[str, int]] = []
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            size = os.path.getsize(path)
            total += size
            files += 1
            if size > MAX_FILE_BYTES:
                rel = os.path.relpath(path, root)
                oversized.append((rel, size))
    return total, files, oversized


def fmt(size: int) -> str:
    return f"{size / (1024 * 1024):.1f} MB"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(f"usage: {sys.argv[0]} SITE_DIR", file=sys.stderr)
        return 2
    root = args[0]
    if not os.path.isdir(root):
        print(f"check_pages_size: not a directory: {root}", file=sys.stderr)
        return 2
    total, files, oversized = check_tree(root)
    print(f"site: {files} files, {fmt(total)} total")
    if oversized:
        for rel, size in oversized:
            print(
                f"check_pages_size: file too large ({fmt(size)} > {fmt(MAX_FILE_BYTES)}): {rel}",
                file=sys.stderr,
            )
        return 1
    if total > MAX_TOTAL_BYTES:
        print(
            f"check_pages_size: site too large ({fmt(total)} > {fmt(MAX_TOTAL_BYTES)})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
