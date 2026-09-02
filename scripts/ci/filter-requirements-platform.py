#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Filter a uv/pip requirements export for a target sys_platform.

Reads requirements text on stdin (or --input). Writes requirement lines that
evaluate true for the target platform, with environment markers stripped so a
host pip download --platform can fetch foreign wheels.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packaging.markers import Marker, default_environment
from packaging.requirements import InvalidRequirement, Requirement


def target_environment(sys_platform: str, python_version: str) -> dict[str, str]:
    env = default_environment().copy()
    env["sys_platform"] = sys_platform
    # packaging expects "3.14" and a full version like "3.14.0".
    parts = python_version.split(".")
    major_minor = ".".join(parts[:2]) if len(parts) >= 2 else python_version
    full = python_version if len(parts) >= 3 else f"{major_minor}.0"
    env["python_version"] = major_minor
    env["python_full_version"] = full
    if sys_platform == "win32":
        env["platform_system"] = "Windows"
        env["os_name"] = "nt"
    elif sys_platform == "darwin":
        env["platform_system"] = "Darwin"
        env["os_name"] = "posix"
    elif sys_platform == "linux":
        env["platform_system"] = "Linux"
        env["os_name"] = "posix"
    return env


def filter_line(line: str, env: dict[str, str]) -> str | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith("-e ") or raw.startswith("--"):
        return None
    try:
        req = Requirement(raw)
    except InvalidRequirement:
        return None
    if req.marker is not None and not Marker(str(req.marker)).evaluate(env):
        return None
    req.marker = None
    return str(req)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sys-platform",
        default="win32",
        help="Target sys_platform for marker evaluation (default: win32)",
    )
    parser.add_argument(
        "--python-version",
        default="3.14.4",
        help="Target Python version for marker evaluation (default: 3.14.4)",
    )
    parser.add_argument(
        "--input", "-i", help="Input requirements path (default: stdin)"
    )
    parser.add_argument("--output", "-o", help="Output path (default: stdout)")
    args = parser.parse_args()

    text = (
        Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    )
    env = target_environment(args.sys_platform, args.python_version)
    out_lines: list[str] = []
    for line in text.splitlines():
        kept = filter_line(line, env)
        if kept:
            out_lines.append(kept)

    body = "\n".join(out_lines) + ("\n" if out_lines else "")
    if args.output:
        Path(args.output).write_text(body, encoding="utf-8")
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
