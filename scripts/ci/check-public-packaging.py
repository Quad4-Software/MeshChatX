#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Fail if meshchatx/public is unsafe to ship in the wheel.

Production Vite builds wipe assets/ and scrub known leftovers. This check
catches a dirty tree before uv build / electron packaging:

  - leftover browser-Tailwind runtime files
  - hashed Vite chunks piled up across builds (3+ hashes for one stem)

The bundled Roboto Mono Nerd Font is a shipped asset again, so Nerd Font
paths under public/ are expected and not treated as leftovers.
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "meshchatx" / "public"
ASSETS = PUBLIC / "assets"

# Paths (any depth under public) that must never ship.
LEFTOVER_RES = (re.compile(r"tailwind-v3\.4\.3-forms-v0\.5\.7\.js$", re.I),)

# Vite emits Name-<hash>.ext; group by (Name, ext).
HASHED_ASSET = re.compile(r"^(.+)-[A-Za-z0-9_-]{6,}\.([A-Za-z0-9]+)$")

# Two entry points (app + nomad-crash-tab) can share a split chunk under
# different hashes. Three or more means emptyOutDir / wipe failed.
MAX_HASHES_PER_STEM = 2


def iter_public_files(public: Path):
    if not public.is_dir():
        return
    for path in public.rglob("*"):
        if path.is_file():
            yield path


def find_leftovers(public: Path) -> list[str]:
    bad: list[str] = []
    for path in iter_public_files(public):
        rel = path.relative_to(public).as_posix()
        if any(rx.search(rel) for rx in LEFTOVER_RES):
            bad.append(rel)
    return sorted(bad)


def find_hash_pileups(assets: Path) -> list[str]:
    if not assets.is_dir():
        return []
    counts: collections.Counter[tuple[str, str]] = collections.Counter()
    for path in assets.iterdir():
        if not path.is_file():
            continue
        m = HASHED_ASSET.match(path.name)
        if not m:
            continue
        counts[(m.group(1), m.group(2))] += 1
    bad = []
    for (stem, ext), n in sorted(counts.items()):
        if n > MAX_HASHES_PER_STEM:
            bad.append(f"{stem}-*.{ext} x{n}")
    return bad


def check_tree(public: Path) -> list[str]:
    errors: list[str] = []
    if not public.is_dir():
        errors.append(f"missing public tree: {public}")
        return errors
    index = public / "index.html"
    if not index.is_file():
        errors.append(f"missing {index.relative_to(public.parent.parent)}")
    leftovers = find_leftovers(public)
    if leftovers:
        errors.append("leftover public files:\n  " + "\n  ".join(leftovers))
    pileups = find_hash_pileups(public / "assets")
    if pileups:
        errors.append(
            "hashed assets piled up (rebuild after wiping assets/):\n  "
            + "\n  ".join(pileups)
        )
    return errors


def check_wheel(wheel: Path) -> list[str]:
    errors: list[str] = []
    if not wheel.is_file():
        return [f"missing wheel: {wheel}"]
    leftovers: list[str] = []
    stems: collections.Counter[tuple[str, str]] = collections.Counter()
    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            if "/public/" not in name:
                continue
            rel = name.split("/public/", 1)[1]
            if any(rx.search(rel) for rx in LEFTOVER_RES):
                leftovers.append(name)
            base = Path(rel).name
            if rel.startswith("assets/") and "/" not in rel[len("assets/") :]:
                m = HASHED_ASSET.match(base)
                if m:
                    stems[(m.group(1), m.group(2))] += 1
    if leftovers:
        errors.append("wheel contains leftovers:\n  " + "\n  ".join(sorted(leftovers)))
    pileups = [
        f"{stem}-*.{ext} x{n}"
        for (stem, ext), n in sorted(stems.items())
        if n > MAX_HASHES_PER_STEM
    ]
    if pileups:
        errors.append("wheel hashed assets piled up:\n  " + "\n  ".join(pileups))
    return errors


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--public",
        type=Path,
        default=PUBLIC,
        help="meshchatx/public path (default: repo meshchatx/public)",
    )
    p.add_argument(
        "--wheel",
        type=Path,
        action="append",
        default=[],
        help="also inspect a .whl (repeatable)",
    )
    args = p.parse_args(argv)

    errors = check_tree(args.public.resolve())
    for whl in args.wheel:
        errors.extend(check_wheel(whl.resolve()))

    if errors:
        print("check-public-packaging: FAIL", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("check-public-packaging: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
