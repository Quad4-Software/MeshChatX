#!/usr/bin/env python3
"""Fetch the Reticulum manual at build time and stage it for bundling.

The downloaded archive is extracted into ``meshchatx/public/reticulum-docs-bundled/current``
so that the application ships with an offline copy of the manual. At runtime the
backend will serve those files for any ``/reticulum-docs/`` request that does not
have a user-uploaded version overriding it.

Usage::

    python scripts/build/fetch_reticulum_manual.py [--source URL] [--dest DIR]
                                                   [--force] [--include-pdf]

By default the upstream PDF/EPUB copies of the manual are excluded from the
bundle because the in-app viewer only renders the HTML version. Pass
``--include-pdf`` (or set ``MESHCHATX_DOCS_INCLUDE_PDF=1``) to keep them.

Environment variables::

    MESHCHATX_RETICULUM_DOCS_URL   Override the default source URL (single value).
    MESHCHATX_RETICULUM_DOCS_DEST  Override the destination directory.
    MESHCHATX_SKIP_DOCS_FETCH      If set to ``1``/``true``, exit without fetching.
    MESHCHATX_DOCS_INCLUDE_PDF     If set to ``1``/``true``, include PDF/EPUB.
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_SOURCES = (
    "https://github.com/markqvist/reticulum_website/archive/refs/heads/main.zip",
    "https://git.quad4.io/Reticulum/reticulum_website/archive/main.zip",
)

DEFAULT_DEST = (
    Path(__file__).resolve().parent.parent.parent
    / "meshchatx"
    / "public"
    / "reticulum-docs-bundled"
    / "current"
)

EXTRA_BINARY_SUFFIXES = (".pdf", ".epub")
"""File suffixes for large alternate-format manuals that are excluded from the
bundled copy by default. The HTML viewer does not use them, so dropping these
saves roughly 9 MB on disk per build artifact."""


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _download(url: str, timeout: float) -> bytes:
    logging.info("Downloading Reticulum manual from %s", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "meshchatx-build-script"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _resolve_docs_root(zip_bytes: bytes) -> tuple[zipfile.ZipFile, str]:
    """Return the open zip and the path prefix that contains the docs/ tree."""
    archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = archive.namelist()
    if not names:
        archive.close()
        raise ValueError("downloaded archive is empty")

    root = names[0].split("/", 1)[0]
    docs_prefix = f"{root}/docs/"
    if not any(name.startswith(docs_prefix) for name in names):
        archive.close()
        raise ValueError(
            f"archive does not contain expected docs/ folder under {root}/",
        )
    return archive, docs_prefix


def _extract(
    archive: zipfile.ZipFile,
    docs_prefix: str,
    dest: Path,
    include_pdf: bool = False,
) -> tuple[int, int]:
    """Extract docs/ tree from ``archive`` into ``dest``.

    Returns ``(extracted_count, skipped_binary_count)``. When ``include_pdf`` is
    false, large alternate-format manuals listed in :data:`EXTRA_BINARY_SUFFIXES`
    are skipped to keep shipped artifacts small.
    """
    extracted = 0
    skipped_binary = 0
    for member in archive.infolist():
        name = member.filename
        if not name.startswith(docs_prefix):
            continue
        rel = name[len(docs_prefix) :]
        if not rel or rel.endswith("/"):
            continue
        if ".." in rel.split("/"):
            continue
        if not include_pdf and rel.lower().endswith(EXTRA_BINARY_SUFFIXES):
            skipped_binary += 1
            continue
        target = dest / rel
        try:
            target.relative_to(dest)
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as src, open(target, "wb") as fh:
            shutil.copyfileobj(src, fh)
        extracted += 1
    return extracted, skipped_binary


def fetch_manual(
    sources: list[str],
    dest: Path,
    timeout: float = 120.0,
    force: bool = False,
    include_pdf: bool = False,
) -> int:
    if dest.exists() and any(dest.iterdir()) and not force:
        logging.info(
            "Reticulum manual already present at %s (%d entries); skipping fetch.",
            dest,
            sum(1 for _ in dest.rglob("*")),
        )
        return 0

    last_error: Exception | None = None
    archive: zipfile.ZipFile | None = None
    docs_prefix: str | None = None
    for url in sources:
        try:
            data = _download(url, timeout)
            archive, docs_prefix = _resolve_docs_root(data)
            break
        except (urllib.error.URLError, OSError, ValueError, zipfile.BadZipFile) as exc:
            logging.warning("Failed to fetch %s: %s", url, exc)
            last_error = exc
            archive = None
            docs_prefix = None

    if archive is None or docs_prefix is None:
        raise SystemExit(
            f"Could not download Reticulum manual from any source: {last_error}",
        )

    try:
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        extracted, skipped_binary = _extract(
            archive,
            docs_prefix,
            dest,
            include_pdf=include_pdf,
        )
    finally:
        archive.close()

    if extracted == 0:
        raise SystemExit("Archive contained no docs/ files to extract")

    if skipped_binary:
        logging.info(
            "Skipped %d alternate-format manual file(s) (%s); pass --include-pdf to keep them.",
            skipped_binary,
            ", ".join(EXTRA_BINARY_SUFFIXES),
        )

    logging.info("Extracted %d files to %s", extracted, dest)
    return extracted


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help=(
            "URL of a Reticulum website ZIP. May be passed multiple times to provide "
            "fallbacks. Defaults to the canonical upstream sources."
        ),
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Output directory for the extracted manual.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if the destination already exists.",
    )
    parser.add_argument(
        "--include-pdf",
        action="store_true",
        default=_is_truthy(os.environ.get("MESHCHATX_DOCS_INCLUDE_PDF")),
        help=(
            "Include the upstream PDF/EPUB manuals in the bundle. They are "
            "skipped by default to keep build artifacts smaller because the "
            "in-app viewer only uses the HTML version."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce log output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s",
    )

    if _is_truthy(os.environ.get("MESHCHATX_SKIP_DOCS_FETCH")):
        logging.info("MESHCHATX_SKIP_DOCS_FETCH is set; skipping Reticulum manual fetch.")
        return 0

    sources: list[str] = []
    if args.source:
        sources.extend(args.source)
    env_url = os.environ.get("MESHCHATX_RETICULUM_DOCS_URL")
    if env_url:
        sources.append(env_url)
    if not sources:
        sources = list(DEFAULT_SOURCES)

    env_dest = os.environ.get("MESHCHATX_RETICULUM_DOCS_DEST")
    dest = args.dest or (Path(env_dest) if env_dest else DEFAULT_DEST)

    fetch_manual(
        sources=sources,
        dest=dest.resolve(),
        timeout=args.timeout,
        force=args.force,
        include_pdf=args.include_pdf,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
