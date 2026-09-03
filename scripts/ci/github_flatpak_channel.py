#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Map a git tag / ref name to a Flatpak OSTree branch (testing / beta / stable)."""

from __future__ import annotations

import sys

VALID_BRANCHES = frozenset({"testing", "beta", "stable"})


def flatpak_branch_from_ref_name(ref_name: str) -> str:
    """Return Flatpak branch for a release tag name.

    Matches Bunny track selection in build-release.yml except the product
    branch name is ``stable`` (Bunny binary track remains ``release``).
    """
    name = (ref_name or "").strip()
    if name.startswith(("nightly-", "testing-")):
        return "testing"
    if name.startswith(("beta-", "preview-")):
        return "beta"
    return "stable"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or not args[0]:
        print(f"usage: {sys.argv[0]} <git-ref-name>", file=sys.stderr)
        return 2
    branch = flatpak_branch_from_ref_name(args[0])
    print(branch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
