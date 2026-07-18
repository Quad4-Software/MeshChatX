#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Fetch the Reticulum manual at build time and stage it for bundling.

The downloaded archive is extracted into meshchatx/public/reticulum-docs-bundled/current
so that the application ships with an offline copy of the manual. At runtime the
backend will serve those files for any /reticulum-docs/ request that does not
have a user-uploaded version overriding it.

Usage::

    python scripts/build/fetch_reticulum_manual.py [--source URL] [--dest DIR]
                                                   [--force] [--include-pdf]

Sources may be HTTPS ZIP URLs, local directories that contain a docs/ tree, or
rns:// rngit remotes (requires git and git-remote-rns).

By default the upstream PDF/EPUB copies of the manual are excluded from the
bundle because the in-app viewer only renders the HTML version. Pass
--include-pdf (or set MESHCHATX_DOCS_INCLUDE_PDF=1) to keep them.

Environment variables::

    MESHCHATX_RETICULUM_DOCS_URL   Override the default source URL (single value).
    MESHCHATX_RETICULUM_DOCS_DEST  Override the destination directory.
    MESHCHATX_RETICULUM_DOCS_VIA_RNS  If set, prefer the default rngit website remote.
    MESHCHATX_RETICULUM_DOCS_REF   Git ref for rns:// clones (default HEAD).
    MESHCHATX_SKIP_DOCS_FETCH      If set to 1/true, exit without fetching.
    MESHCHATX_DOCS_INCLUDE_PDF     If set to 1/true, include PDF/EPUB.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pip_rns_remotes import DEFAULT_WEBSITE_REMOTE  # noqa: E402

DEFAULT_SOURCES = (
    "https://codeload.github.com/markqvist/reticulum_website/zip/refs/heads/master",
)
DEFAULT_RNS_SOURCE = DEFAULT_WEBSITE_REMOTE

DEFAULT_DEST = (
    Path(__file__).resolve().parent.parent.parent
    / "meshchatx"
    / "public"
    / "reticulum-docs-bundled"
    / "current"
)

BUNDLE_MANIFEST_PATH = Path(__file__).resolve().parent / "reticulum_docs_bundle.json"

EXTRA_BINARY_SUFFIXES = (".pdf", ".epub")
"""File suffixes for large alternate-format manuals that are excluded from the
bundled copy by default. The HTML viewer does not use them, so dropping these
saves roughly 9 MB on disk per build artifact."""


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _is_rns_source(source: str) -> bool:
    return source.strip().lower().startswith("rns://")


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
    """Extract docs/ tree from archive into dest.

    Returns (extracted_count, skipped_binary_count). When include_pdf is
    false, large alternate-format manuals listed in EXTRA_BINARY_SUFFIXES
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


def _extract_from_docs_dir(
    docs_dir: Path,
    dest: Path,
    include_pdf: bool = False,
) -> tuple[int, int]:
    """Copy a local docs/ tree into dest."""
    if not docs_dir.is_dir():
        raise ValueError(f"docs directory missing: {docs_dir}")
    extracted = 0
    skipped_binary = 0
    for path in docs_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(docs_dir).as_posix()
        if not rel or ".." in rel.split("/"):
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
        shutil.copy2(path, target)
        extracted += 1
    return extracted, skipped_binary


def _find_docs_dir(root: Path) -> Path:
    direct = root / "docs"
    if direct.is_dir():
        return direct
    matches = [p for p in root.rglob("docs") if p.is_dir()]
    for candidate in matches:
        if (candidate / "index.html").is_file() or (candidate / "manual").is_dir():
            return candidate
    if matches:
        return matches[0]
    raise ValueError(f"no docs/ directory found under {root}")


def _run_git(args: list[str], *, cwd: Path | None, timeout: float) -> None:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"git timed out: {' '.join(args)}") from exc
    if completed.returncode != 0:
        err = (completed.stderr or b"").decode("utf-8", errors="replace")[:500]
        raise ValueError(f"git failed ({completed.returncode}): {err or args}")


def _clone_rns_docs(
    remote: str,
    *,
    timeout: float,
    ref: str,
) -> Path:
    """Clone an rns:// website repo sparsely and return its docs/ path."""
    if shutil.which("git") is None:
        raise ValueError("git is required for rns:// docs sources")
    if shutil.which("git-remote-rns") is None:
        raise ValueError("git-remote-rns is required for rns:// docs sources")

    work = Path(tempfile.mkdtemp(prefix="meshchatx-rns-docs-"))
    try:
        logging.info("Cloning Reticulum website from %s (ref=%s)", remote, ref)
        _run_git(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--sparse",
                "--no-checkout",
                remote,
                str(work),
            ],
            cwd=None,
            timeout=timeout,
        )
        _run_git(
            ["git", "sparse-checkout", "set", "--no-cone", "--", "docs"],
            cwd=work,
            timeout=min(60.0, timeout),
        )
        fetch_ref = ref if ref and ref != "HEAD" else "HEAD"
        _run_git(
            ["git", "fetch", "--depth", "1", "origin", fetch_ref],
            cwd=work,
            timeout=timeout,
        )
        _run_git(
            ["git", "checkout", "FETCH_HEAD", "--", "docs"],
            cwd=work,
            timeout=min(120.0, timeout),
        )
        return _find_docs_dir(work)
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def _stage_from_local_or_rns(
    source: str,
    dest: Path,
    *,
    timeout: float,
    include_pdf: bool,
    ref: str,
) -> tuple[int, int, str]:
    """Return extracted counts and a cleanup workdir path (may be empty)."""
    cleanup = ""
    local = Path(source)
    if local.exists() and local.is_dir():
        docs_dir = _find_docs_dir(local)
        extracted, skipped = _extract_from_docs_dir(
            docs_dir, dest, include_pdf=include_pdf
        )
        return extracted, skipped, cleanup

    if _is_rns_source(source):
        docs_dir = _clone_rns_docs(source.strip(), timeout=timeout, ref=ref)
        cleanup = str(docs_dir.parent)
        try:
            extracted, skipped = _extract_from_docs_dir(
                docs_dir, dest, include_pdf=include_pdf
            )
        finally:
            shutil.rmtree(cleanup, ignore_errors=True)
            cleanup = ""
        return extracted, skipped, cleanup

    raise ValueError(f"unsupported local/rns source: {source}")


def _write_bundle_manifest(
    *,
    source_url: str,
    dest: Path,
    extracted: int,
    skipped_binary: int,
    manifest_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        dest_value = str(dest.resolve().relative_to(repo_root))
    except ValueError:
        dest_value = str(dest.resolve())

    source_value = source_url
    if source_url.startswith("/"):
        try:
            source_value = str(Path(source_url).resolve().relative_to(repo_root))
        except ValueError:
            pass

    payload = {
        "source_url": source_value,
        "dest": dest_value,
        "fetched_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "html_files": extracted,
        "skipped_binary_files": skipped_binary,
    }
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logging.info("Wrote bundle manifest to %s", manifest_path)


def fetch_manual(
    sources: list[str],
    dest: Path,
    timeout: float = 120.0,
    force: bool = False,
    include_pdf: bool = False,
    ref: str = "HEAD",
    manifest_path: Path | None = None,
) -> int:
    if dest.exists() and any(dest.iterdir()) and not force:
        logging.info(
            "Reticulum manual already present at %s (%d entries); skipping fetch.",
            dest,
            sum(1 for _ in dest.rglob("*")),
        )
        return 0

    last_error: Exception | None = None
    extracted = 0
    skipped_binary = 0
    source_url: str | None = None

    for url in sources:
        try:
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)

            if _is_rns_source(url) or Path(url).exists():
                extracted, skipped_binary, _cleanup = _stage_from_local_or_rns(
                    url,
                    dest,
                    timeout=timeout,
                    include_pdf=include_pdf,
                    ref=ref,
                )
                source_url = url
                break

            data = _download(url, timeout)
            archive, docs_prefix = _resolve_docs_root(data)
            try:
                extracted, skipped_binary = _extract(
                    archive,
                    docs_prefix,
                    dest,
                    include_pdf=include_pdf,
                )
            finally:
                archive.close()
            source_url = url
            break
        except (
            urllib.error.URLError,
            OSError,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            logging.warning("Failed to fetch %s: %s", url, exc)
            last_error = exc
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)

    if source_url is None:
        raise SystemExit(
            f"Could not download Reticulum manual from any source: {last_error}",
        )

    if extracted == 0:
        raise SystemExit("Archive contained no docs/ files to extract")

    if skipped_binary:
        logging.info(
            "Skipped %d alternate-format manual file(s) (%s); pass --include-pdf to keep them.",
            skipped_binary,
            ", ".join(EXTRA_BINARY_SUFFIXES),
        )

    logging.info("Extracted %d files to %s", extracted, dest)
    _write_bundle_manifest(
        source_url=source_url,
        dest=dest,
        extracted=extracted,
        skipped_binary=skipped_binary,
        manifest_path=manifest_path or BUNDLE_MANIFEST_PATH,
    )
    return extracted


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help=(
            "HTTPS ZIP URL, local checkout path, or rns:// remote. May be passed "
            "multiple times for fallbacks. Defaults to the canonical upstream sources."
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
        help="HTTP / git timeout in seconds.",
    )
    parser.add_argument(
        "--ref",
        default=os.environ.get("MESHCHATX_RETICULUM_DOCS_REF", "HEAD"),
        help="Git ref for rns:// clones (default HEAD or MESHCHATX_RETICULUM_DOCS_REF).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if the destination already exists.",
    )
    parser.add_argument(
        "--via-rns",
        action="store_true",
        default=_is_truthy(os.environ.get("MESHCHATX_RETICULUM_DOCS_VIA_RNS")),
        help=(
            "Prefer the default rngit website remote "
            f"({DEFAULT_RNS_SOURCE}). Also set MESHCHATX_RETICULUM_DOCS_VIA_RNS=1."
        ),
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
        logging.info(
            "MESHCHATX_SKIP_DOCS_FETCH is set; skipping Reticulum manual fetch."
        )
        return 0

    sources: list[str] = []
    if args.source:
        sources.extend(args.source)
    env_url = os.environ.get("MESHCHATX_RETICULUM_DOCS_URL")
    if env_url:
        sources.append(env_url)
    if args.via_rns:
        sources.insert(0, DEFAULT_RNS_SOURCE)
    if not sources:
        sources = list(DEFAULT_SOURCES)

    env_dest = os.environ.get("MESHCHATX_RETICULUM_DOCS_DEST")
    dest = args.dest or (Path(env_dest) if env_dest else DEFAULT_DEST)

    if _is_truthy(os.environ.get("MESHCHATX_OFFLINE_BUILD")):
        if dest.exists() and any(dest.iterdir()):
            logging.info(
                "MESHCHATX_OFFLINE_BUILD=1 and Reticulum manual already present at %s; skipping fetch.",
                dest,
            )
            return 0
        logging.error(
            "MESHCHATX_OFFLINE_BUILD=1 but Reticulum manual is missing at %s", dest
        )
        return 1

    fetch_manual(
        sources=sources,
        dest=dest.resolve(),
        timeout=args.timeout,
        force=args.force,
        include_pdf=args.include_pdf,
        ref=args.ref,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
