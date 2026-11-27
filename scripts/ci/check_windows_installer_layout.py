#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
r"""Verify the payload layout of the Windows NSIS installer.

Regression guard for the 4.12.0/4.12.1 bug where the frozen backend was
extracted into the install root instead of backend\\ next to the shell exe.
"""

import os
import shutil
import subprocess
import sys

REQUIRED_BACKEND_EXE = "backend/reticulummeshchatx.exe"
SHELL_EXE = "meshchatx-desktop.exe"
STRANDED_BACKEND_EXE = "reticulummeshchatx.exe"
BACKEND_LIB_PREFIX = "backend/lib/"


def normalize(path: str) -> str:
    return path.replace("\\", "/").strip().lower()


def check_listing(paths: list[str]) -> list[str]:
    errors = []
    normalized = []
    for raw in paths:
        path = normalize(raw)
        if path.startswith("$pluginsdir/"):
            continue
        for prefix in ("$instdir/", "$_outdir/"):
            if path.startswith(prefix):
                path = path[len(prefix) :]
                break
        normalized.append(path)

    entries = {p for p in normalized if p}
    if REQUIRED_BACKEND_EXE not in entries:
        errors.append(
            f"missing {REQUIRED_BACKEND_EXE} (backend must live under backend/)"
        )
    if SHELL_EXE not in entries:
        errors.append(f"missing root-level shell exe {SHELL_EXE}")
    if STRANDED_BACKEND_EXE in entries:
        errors.append(
            f"root-level {STRANDED_BACKEND_EXE} present: backend payload stranded in install root"
        )
    if not any(p.startswith(BACKEND_LIB_PREFIX) for p in entries):
        errors.append(
            f"no {BACKEND_LIB_PREFIX} entries found (backend payload incomplete)"
        )
    return errors


def find_7z() -> str | None:
    for candidate in ("7z", "7za", "C:/Program Files/7-Zip/7z.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if "/" in candidate and os.path.isfile(candidate):
            return candidate
    return None


def list_installer(sevenz: str, installer: str) -> list[str]:
    result = subprocess.run(
        [sevenz, "l", "-slt", installer],
        capture_output=True,
        text=True,
        check=True,
    )
    return [
        line[len("Path = ") :]
        for line in result.stdout.splitlines()
        if line.startswith("Path = ")
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <installer.exe>", file=sys.stderr)
        return 2
    sevenz = find_7z()
    if not sevenz:
        print("error: 7z/7za not found", file=sys.stderr)
        return 2
    try:
        paths = list_installer(sevenz, argv[1])
    except subprocess.CalledProcessError as exc:
        print(f"error: 7z failed on {argv[1]}: {exc.stderr or exc}", file=sys.stderr)
        return 2
    errors = check_listing(paths)
    if errors:
        for error in errors:
            print(f"layout error: {error}", file=sys.stderr)
        return 1
    print(f"installer layout ok: {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
