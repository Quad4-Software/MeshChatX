#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Entrypoint for Chainguard/minimal-style images without a POSIX shell."""

from __future__ import annotations

import os
import pwd
import sys


def _chown_tree(path: str, uid: int, gid: int) -> None:
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    if not (st.st_uid == uid and st.st_gid == gid):
        os.lchown(path, uid, gid)
    if not os.path.isdir(path) or os.path.islink(path):
        return
    with os.scandir(path) as it:
        for entry in it:
            _chown_tree(entry.path, uid, gid)


def main() -> None:
    argv = sys.argv[1:]
    if not argv:
        print("docker-entrypoint: missing command", file=sys.stderr)
        raise SystemExit(1)

    if os.getuid() == 0:
        pw = pwd.getpwnam("meshchat")
        _chown_tree("/config", pw.pw_uid, pw.pw_gid)
        os.initgroups(pw.pw_name, pw.pw_gid)
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)
        os.environ.setdefault("HOME", pw.pw_dir)

    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
