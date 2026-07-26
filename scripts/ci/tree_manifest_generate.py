#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Fast git-index tree manifest for meshchatx.rsm signing.

Hashes index blobs (same bytes as git show :path) via git cat-file --batch.
Output format matches scripts/ci/tree-manifest.sh generate.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

MANIFEST_HEADER = "# meshchatx tree manifest v1"
EXCLUDE_RSM = "meshchatx.rsm"
ALLOWED_MODES = frozenset({"100644", "100755"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_excluded_path(path: str) -> bool:
    if path == EXCLUDE_RSM:
        return True
    if path == "vendor" or path.startswith("vendor/"):
        return True
    if "/vendor/" in path or path.endswith("/vendor"):
        return True
    return False


def _parse_ls_files_z(raw: bytes) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for chunk in raw.split(b"\0"):
        if not chunk:
            continue
        tab = chunk.find(b"\t")
        if tab < 0:
            continue
        meta = chunk[:tab].decode("ascii", errors="replace")
        path = chunk[tab + 1 :].decode("utf-8", errors="surrogateescape")
        parts = meta.split()
        if len(parts) < 3:
            continue
        mode, oid, _stage = parts[0], parts[1], parts[2]
        entries.append((path, mode, oid))
    return entries


def _read_batch_blob(stdout, header: bytes) -> bytes | None:
    parts = header.strip().split()
    if len(parts) == 2 and parts[1] == b"missing":
        return None
    if len(parts) != 3:
        raise RuntimeError(f"unexpected cat-file header: {header!r}")
    _oid, typ, size_s = parts
    if typ == b"missing":
        return None
    size = int(size_s)
    data = stdout.read(size)
    if len(data) != size:
        raise RuntimeError("short read from git cat-file --batch")
    if typ == b"blob":
        delim = stdout.read(1)
        if delim != b"\n":
            raise RuntimeError("expected newline delimiter after cat-file blob")
    return data


def generate_manifest(root: Path) -> str:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    raw = subprocess.check_output(
        ["git", "ls-files", "-s", "-z"],
        cwd=root,
        env=env,
    )
    rows: list[tuple[str, str, str]] = []
    for path, mode, oid in _parse_ls_files_z(raw):
        if not path or is_excluded_path(path):
            continue
        if mode not in ALLOWED_MODES:
            continue
        rows.append((path, mode, oid))
    rows.sort(key=lambda item: item[0])

    lines = [MANIFEST_HEADER]
    if not rows:
        return "\n".join(lines) + "\n"

    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    stdin_buf = "".join(f"{oid}\n" for _path, _mode, oid in rows).encode("ascii")
    proc.stdin.write(stdin_buf)
    proc.stdin.close()

    for path, _mode, _oid in rows:
        header = proc.stdout.readline()
        if not header:
            raise RuntimeError("git cat-file --batch closed stdout early")
        blob = _read_batch_blob(proc.stdout, header)
        if blob is None:
            continue
        digest = hashlib.sha256(blob).hexdigest()
        lines.append(f"{digest}  {path}")

    proc.wait()
    if proc.returncode not in (0, None):
        raise RuntimeError(f"git cat-file --batch exited {proc.returncode}")

    return "\n".join(lines) + "\n"


def main() -> int:
    root = _repo_root()
    try:
        sys.stdout.write(generate_manifest(root))
    except Exception as exc:
        print(f"tree_manifest_generate.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
