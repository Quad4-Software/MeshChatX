#!/usr/bin/env python3
"""Download repository bundled wheels at build time (offline-first installs).

Wheels are written to ``meshchatx/public/repository-server-bundled/bundled`` so they
ship with the same artifact layout as the Vite output. At runtime,
:class:`~meshchatx.src.backend.repository_server_manager.RepositoryServerManager`
copies any missing ``*.whl`` files from that directory into each identity's
``repository-server/bundled`` folder (no network required).

The PyPI/sdist wheel intentionally omits this tree (see ``MANIFEST.in`` and
``tool.setuptools.exclude-package-data``); use this script for desktop or
Android builds, or refresh bundled wheels when online. If
``dist/reticulum_meshchatx-*.whl`` exists at the project root, it is copied into
the bundled directory after PyPI downloads so the shipped wheel matches this
tree.

Usage::

    python3 scripts/build/fetch_repository_wheels.py [--dest DIR]

Environment::

    MESHCHATX_SKIP_REPOSITORY_WHEELS_FETCH  If ``1``/``true``, exit without downloading.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

DEFAULT_DEST = (
    Path(__file__).resolve().parent.parent.parent
    / "meshchatx"
    / "public"
    / "repository-server-bundled"
    / "bundled"
)


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if _is_truthy(os.environ.get("MESHCHATX_SKIP_REPOSITORY_WHEELS_FETCH")):
        logging.info(
            "Skipping repository wheels fetch (MESHCHATX_SKIP_REPOSITORY_WHEELS_FETCH)."
        )
        return 0

    repo_root = Path(__file__).resolve().parent.parent.parent
    rr = str(repo_root)
    if rr not in sys.path:
        sys.path.insert(0, rr)

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help=f"Output directory (default: {DEFAULT_DEST})",
    )
    args = parser.parse_args(argv)
    dest: Path = args.dest.resolve()

    from meshchatx.src.backend.repository_server_manager import (
        download_bundled_wheels_to_directory,
    )

    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("*.whl"):
        try:
            old.unlink()
        except OSError as e:
            logging.warning("Could not remove %s: %s", old, e)

    result = download_bundled_wheels_to_directory(dest)
    failed = result.get("failed") or {}
    ok = result.get("downloaded") or []
    if failed:
        for pkg, msg in failed.items():
            logging.error("%s: %s", pkg, msg[:500])
    if ok:
        logging.info("Repository wheels OK: %s", ", ".join(ok))
    if not ok and failed:
        return 1
    if failed:
        logging.warning(
            "Repository wheels partial success (%d ok, %d failed).",
            len(ok),
            len(failed),
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
