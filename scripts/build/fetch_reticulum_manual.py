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

Sources are rns:// rngit remotes (requires git and git-remote-rns). Before an
rns:// clone the script installs rns when needed and writes an ephemeral Reticulum
config with up to eight random clearnet TCP bootstraps from
https://meshchatx.com/api/mcx-interfaces. An HTTPS ZIP fallback runs when mesh
fetch still fails. Pass --source for a local checkout or extra fallbacks.

By default the upstream PDF/EPUB copies of the manual are excluded from the
bundle because the in-app viewer only renders the HTML version. Pass
--include-pdf (or set MESHCHATX_DOCS_INCLUDE_PDF=1) to keep any PDF/EPUB files
that happen to sit in the website docs/ tree. This script does not fetch release
PDF/EPUB artifacts.

Refresh policy
--------------

Normal builds skip the network fetch when the bundled HTML tree is present and
scripts/build/reticulum_docs_bundle.json records the same rns version as
uv.lock. Pass --force to refetch anyway. CI should restore a docs cache keyed on
uv.lock so clearnet-free runners reuse the last mesh fetch until rns bumps.

Manual PDF and EPUB outside this script
---------------------------------------

You can always fetch the latest manual in PDF and EPUB formats directly using
rngit::

    rngit release rns://7649a50d84610232d1416b41d2896aff/reticulum/reticulum \\
        fetch "latest:Reticulum Manual.pdf"

Or download from the latest release page in Nomad Network::

    a8d24177d946de4f1f0a0fe1af9a1338:/page/release.mu`g=reticulum|r=reticulum|t=latest

There is also a fully Nomad Network browsable copy on Aleph::

    a8d24177d946de4f1f0a0fe1af9a1338:/page/blob.mu`g=reticulum|r=reticulum|ref=HEAD|path=docs/markdown/index.md

Environment variables::

    MESHCHATX_RETICULUM_DOCS_URL   Override the default source URL (single value).
    MESHCHATX_RETICULUM_DOCS_DEST  Override the destination directory.
    MESHCHATX_RETICULUM_DOCS_REF   Git ref for rns:// clones (default HEAD).
    MESHCHATX_SKIP_DOCS_FETCH      If set to 1/true, exit without fetching.
    MESHCHATX_DOCS_INCLUDE_PDF     If set to 1/true, include PDF/EPUB.
    MESHCHATX_SKIP_RNS_INSTALL     If set to 1/true, do not pip install rns.
    MESHCHATX_DOCS_BOOTSTRAP_COUNT Max random TCP bootstraps for rns:// fetch (default 8).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pip_rns_remotes import DEFAULT_WEBSITE_REMOTE  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_HTTPS_FALLBACK = (
    "https://codeload.github.com/markqvist/reticulum_website/zip/refs/heads/master"
)
DEFAULT_RNS_SOURCE = DEFAULT_WEBSITE_REMOTE
DEFAULT_SOURCES = (DEFAULT_RNS_SOURCE, DEFAULT_HTTPS_FALLBACK)
KNOWN_DOCS_SOURCES = frozenset({DEFAULT_RNS_SOURCE, DEFAULT_HTTPS_FALLBACK})
MCX_INTERFACES_URL = "https://meshchatx.com/api/mcx-interfaces"
DEFAULT_BOOTSTRAP_COUNT = 8

_RNS_LOCK_VERSION = re.compile(
    r'^\[\[package\]\]\s*\nname = "rns"\s*\nversion = "([^"]+)"',
    re.MULTILINE,
)

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


def pinned_rns_version(lock_path: Path | None = None) -> str | None:
    """Return the rns version pinned in uv.lock."""
    target = lock_path or (REPO_ROOT / "uv.lock")
    if not target.is_file():
        return None
    match = _RNS_LOCK_VERSION.search(target.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def load_bundle_manifest(manifest_path: Path) -> dict | None:
    if not manifest_path.is_file():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def bundle_looks_valid(dest: Path) -> bool:
    if not dest.is_dir():
        return False
    if not (dest / "manual" / "index.html").is_file():
        return False
    return any(dest.rglob("*"))


def should_skip_fetch(
    *,
    dest: Path,
    manifest_path: Path,
    source_url: str,
    pinned_rns: str | None,
    force: bool,
) -> tuple[bool, str]:
    if force:
        return False, "forced refresh"
    if not bundle_looks_valid(dest):
        return False, "bundled docs missing or incomplete"
    manifest = load_bundle_manifest(manifest_path)
    if manifest is None:
        return False, "bundle manifest missing"
    recorded_source = manifest.get("source_url")
    if recorded_source != source_url and recorded_source not in KNOWN_DOCS_SOURCES:
        return False, "bundle source changed"
    if pinned_rns is None:
        return False, "pinned rns version unknown"
    recorded = manifest.get("rns_version")
    if recorded != pinned_rns:
        return False, f"rns version changed ({recorded} -> {pinned_rns})"
    return True, "bundled docs match pinned rns version"


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


@dataclass(frozen=True)
class TcpBootstrap:
    name: str
    host: str
    port: int


def _validate_mcx_interfaces_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError("mcx-interfaces URL must use https")
    host = (parsed.hostname or "").lower()
    if host != "meshchatx.com":
        raise ValueError("mcx-interfaces URL host is not allowed")
    return url.strip()


def _sanitize_interface_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not cleaned:
        return "bootstrap"
    cleaned = (
        cleaned.replace("[", "(")
        .replace("]", ")")
        .replace("\n", " ")
        .replace("\r", " ")
    )
    cleaned = " ".join(cleaned.split())
    return cleaned[:128] or "bootstrap"


def _sanitize_target_host(host: str) -> str | None:
    cleaned = str(host or "").strip()
    if not cleaned:
        return None
    if any(ch in cleaned for ch in "\r\n\t="):
        return None
    cleaned = " ".join(cleaned.split())
    return cleaned[:253] or None


def _valid_tcp_port(port: int) -> bool:
    return 1 <= port <= 65535


def _parse_mcx_tcp_bootstraps(payload: object) -> list[TcpBootstrap]:
    rows: list[object]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        candidate = payload.get("interfaces")
        rows = candidate if isinstance(candidate, list) else []
    else:
        rows = []

    out: list[TcpBootstrap] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if (row.get("type") or "").lower() != "tcp":
            continue
        if (row.get("network") or "").lower() != "clearnet":
            continue
        if (row.get("status") or "").lower() != "online":
            continue
        host = _sanitize_target_host(str(row.get("host") or row.get("address") or ""))
        port = row.get("port")
        if not host or port is None:
            continue
        try:
            port_i = int(port)
        except (TypeError, ValueError):
            continue
        if not _valid_tcp_port(port_i):
            continue
        key = (host.lower(), port_i)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            TcpBootstrap(
                name=_sanitize_interface_name(str(row.get("name") or host)),
                host=host,
                port=port_i,
            ),
        )
    return out


def _fetch_mcx_tcp_bootstraps(
    *,
    url: str = MCX_INTERFACES_URL,
    timeout: float,
) -> list[TcpBootstrap]:
    safe_url = _validate_mcx_interfaces_url(url)
    logging.info("Fetching community TCP bootstraps from %s", safe_url)
    req = urllib.request.Request(
        safe_url,
        headers={"User-Agent": "meshchatx-build-script"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.load(response)
    return _parse_mcx_tcp_bootstraps(payload)


def _pick_random_tcp_bootstraps(
    count: int,
    *,
    url: str = MCX_INTERFACES_URL,
    timeout: float,
    rng: random.Random | None = None,
) -> list[TcpBootstrap]:
    pool = _fetch_mcx_tcp_bootstraps(url=url, timeout=timeout)
    if not pool:
        return []
    picker = rng or random.SystemRandom()
    take = max(1, min(count, len(pool)))
    return picker.sample(pool, take)


def _write_bootstrap_config(config_path: Path, bootstraps: list[TcpBootstrap]) -> None:
    lines = [
        "[reticulum]",
        "  enable_transport = yes",
        "  share_instance = no",
        "  panic_on_interface_error = no",
        "",
        "[interfaces]",
    ]
    used_names: set[str] = set()
    for item in bootstraps:
        host = _sanitize_target_host(item.host)
        if not host or not _valid_tcp_port(item.port):
            logging.warning(
                "Skipping bootstrap with invalid target %r:%s",
                item.host,
                item.port,
            )
            continue
        name = item.name
        suffix = 2
        while name in used_names:
            name = f"{item.name} {suffix}"
            suffix += 1
        used_names.add(name)
        lines.extend(
            [
                f"  [[{name}]]",
                "    type = TCPClientInterface",
                "    enabled = yes",
                f"    target_host = {host}",
                f"    target_port = {item.port}",
                "    bootstrap_only = yes",
                "",
            ],
        )
    config_path.write_text("\n".join(lines), encoding="utf-8")


def _git_remote_rns_path() -> str | None:
    found = shutil.which("git-remote-rns")
    if found:
        return found
    candidate = Path(sys.executable).resolve().parent / "git-remote-rns"
    if candidate.is_file():
        return str(candidate)
    return None


def _ensure_rns_tooling(*, pinned_rns: str | None) -> None:
    if _git_remote_rns_path():
        return
    if _is_truthy(os.environ.get("MESHCHATX_SKIP_RNS_INSTALL")):
        raise ValueError(
            "git-remote-rns is required for rns:// docs sources "
            "(set MESHCHATX_SKIP_RNS_INSTALL=0 and install rns, or use HTTPS fallback)",
        )
    version = pinned_rns or pinned_rns_version() or "1.5.0"
    logging.info("Installing rns %s for git-remote-rns", version)
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "install", f"rns=={version}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-500:]
        raise ValueError(f"failed to install rns=={version}: {tail or completed.returncode}")
    if not _git_remote_rns_path():
        raise ValueError("git-remote-rns still missing after installing rns")


def _build_rns_git_env(config_dir: str | None) -> dict[str, str]:
    env = os.environ.copy()
    bindir = str(Path(sys.executable).resolve().parent)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    if config_dir:
        env["RNS_CONFIG"] = config_dir
    return env


@contextlib.contextmanager
def _ephemeral_rns_bootstrap(
    *,
    count: int,
    timeout: float,
    pinned_rns: str | None,
) -> Iterator[dict[str, str]]:
    _ensure_rns_tooling(pinned_rns=pinned_rns)
    work = Path(tempfile.mkdtemp(prefix="meshchatx-rns-bootstrap-"))
    try:
        bootstraps = _pick_random_tcp_bootstraps(count, timeout=timeout)
        if bootstraps:
            config_path = work / "config"
            _write_bootstrap_config(config_path, bootstraps)
            names = ", ".join(f"{b.name} ({b.host}:{b.port})" for b in bootstraps)
            logging.info(
                "Using %d ephemeral TCP bootstrap(s) for rns:// docs fetch: %s",
                len(bootstraps),
                names,
            )
            yield _build_rns_git_env(str(work))
        else:
            logging.warning(
                "No clearnet TCP bootstraps from mcx-interfaces; "
                "attempting rns:// fetch without ephemeral interfaces",
            )
            yield _build_rns_git_env(None)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _bootstrap_count() -> int:
    raw = os.environ.get("MESHCHATX_DOCS_BOOTSTRAP_COUNT", "")
    if not raw.strip():
        return DEFAULT_BOOTSTRAP_COUNT
    try:
        return max(1, min(DEFAULT_BOOTSTRAP_COUNT, int(raw.strip())))
    except ValueError:
        return DEFAULT_BOOTSTRAP_COUNT


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


def _run_git(
    args: list[str],
    *,
    cwd: Path | None,
    timeout: float,
    env: dict[str, str] | None = None,
) -> None:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            check=False,
            capture_output=True,
            timeout=timeout,
            env=env,
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
    pinned_rns: str | None = None,
) -> tuple[Path, str]:
    """Clone an rns:// website repo sparsely and return docs/ path and commit."""
    if shutil.which("git") is None:
        raise ValueError("git is required for rns:// docs sources")

    work = Path(tempfile.mkdtemp(prefix="meshchatx-rns-docs-"))
    try:
        with _ephemeral_rns_bootstrap(
            count=_bootstrap_count(),
            timeout=timeout,
            pinned_rns=pinned_rns,
        ) as git_env:
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
                env=git_env,
            )
            _run_git(
                ["git", "sparse-checkout", "set", "--no-cone", "--", "docs"],
                cwd=work,
                timeout=min(60.0, timeout),
                env=git_env,
            )
            fetch_ref = ref if ref and ref != "HEAD" else "HEAD"
            _run_git(
                ["git", "fetch", "--depth", "1", "origin", fetch_ref],
                cwd=work,
                timeout=timeout,
                env=git_env,
            )
            _run_git(
                ["git", "checkout", "FETCH_HEAD", "--", "docs"],
                cwd=work,
                timeout=min(120.0, timeout),
                env=git_env,
            )
            completed = subprocess.run(
                ["git", "rev-parse", "FETCH_HEAD"],
                cwd=work,
                check=False,
                capture_output=True,
                timeout=min(30.0, timeout),
                env=git_env,
            )
        docs_commit = (
            completed.stdout.decode("utf-8", errors="replace").strip()
            if completed.returncode == 0
            else ""
        )
        return _find_docs_dir(work), docs_commit
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
) -> tuple[int, int, str, str]:
    """Return extracted counts, cleanup workdir path, and optional docs commit."""
    cleanup = ""
    docs_commit = ""
    local = Path(source)
    if local.exists() and local.is_dir():
        docs_dir = _find_docs_dir(local)
        extracted, skipped = _extract_from_docs_dir(
            docs_dir, dest, include_pdf=include_pdf
        )
        return extracted, skipped, cleanup, docs_commit

    if _is_rns_source(source):
        docs_dir, docs_commit = _clone_rns_docs(
            source.strip(),
            timeout=timeout,
            ref=ref,
            pinned_rns=pinned_rns_version(),
        )
        cleanup = str(docs_dir.parent)
        try:
            extracted, skipped = _extract_from_docs_dir(
                docs_dir, dest, include_pdf=include_pdf
            )
        finally:
            shutil.rmtree(cleanup, ignore_errors=True)
            cleanup = ""
        return extracted, skipped, cleanup, docs_commit

    raise ValueError(f"unsupported local/rns source: {source}")


def _write_bundle_manifest(
    *,
    source_url: str,
    dest: Path,
    extracted: int,
    skipped_binary: int,
    manifest_path: Path,
    rns_version: str | None = None,
    docs_commit: str = "",
) -> None:
    repo_root = REPO_ROOT
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
    if rns_version:
        payload["rns_version"] = rns_version
    if docs_commit:
        payload["docs_commit"] = docs_commit
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
    pinned_rns: str | None = None,
) -> int:
    manifest = manifest_path or BUNDLE_MANIFEST_PATH
    primary_source = sources[0] if sources else DEFAULT_RNS_SOURCE
    resolved_pinned = pinned_rns if pinned_rns is not None else pinned_rns_version()

    skip, reason = should_skip_fetch(
        dest=dest,
        manifest_path=manifest,
        source_url=primary_source,
        pinned_rns=resolved_pinned,
        force=force,
    )
    if skip:
        logging.info(
            "Reticulum manual up to date at %s (%s); skipping fetch.",
            dest,
            reason,
        )
        return 0

    logging.info("Refreshing Reticulum manual (%s).", reason)

    last_error: Exception | None = None
    extracted = 0
    skipped_binary = 0
    source_url: str | None = None
    docs_commit = ""

    for url in sources:
        try:
            if dest.exists():
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)

            if _is_rns_source(url) or Path(url).exists():
                extracted, skipped_binary, _cleanup, docs_commit = (
                    _stage_from_local_or_rns(
                        url,
                        dest,
                        timeout=timeout,
                        include_pdf=include_pdf,
                        ref=ref,
                    )
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
        manifest_path=manifest,
        rns_version=resolved_pinned,
        docs_commit=docs_commit,
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
            "multiple times for fallbacks. Defaults to the rngit website remote."
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
        help="Re-fetch even when the bundled docs match the pinned rns version.",
    )
    parser.add_argument(
        "--via-rns",
        action="store_true",
        help=(
            "Deprecated alias kept for scripts. The default source is already "
            f"{DEFAULT_RNS_SOURCE}."
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
