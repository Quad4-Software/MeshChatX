#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Upload a Flatpak OSTree tree to bunny.net Edge Storage in safe order.

Upload order (Larsson / Flatpak static hosting):

1. ``repo/objects/**`` then ``repo/deltas/**``
2. ``repo/refs/**``, ``repo/config``, root discovery files
3. ``repo/summaries/**``, ``summary``, ``summary.sig``, then ``summary.idx`` last

Within each phase, uploads may run concurrently. Phases never overlap.
After summary is live, delete remote files under ``objects/`` and ``deltas/``
that are no longer present locally (post-prune orphans).

Never treats ``flatpak`` as a release-asset track/version prune prefix.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

DEFAULT_PREFIX = "flatpak"
DEFAULT_WORKERS = 16
MAX_WORKERS = 64

PHASE_OBJECTS = 0
PHASE_DELTAS = 1
PHASE_METADATA = 2
PHASE_SUMMARIES = 3
PHASE_SUMMARY = 4
PHASE_SUMMARY_SIG = 5
PHASE_SUMMARY_IDX = 6


def encode_object_rel(rel: str) -> str:
    return "/".join(quote(part, safe="") for part in rel.split("/"))


def mime_for(path: Path) -> str:
    if path.suffix.lower() == ".wasm":
        return "application/wasm"
    guessed, _enc = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def upload_phase(rel: str) -> int:
    """Return sort phase for a path relative to the flatpak export root."""
    if rel.startswith("repo/objects/") or rel == "repo/objects":
        return PHASE_OBJECTS
    if rel.startswith("repo/deltas/") or rel == "repo/deltas":
        return PHASE_DELTAS
    if rel.startswith("repo/summaries/") or rel == "repo/summaries":
        return PHASE_SUMMARIES
    if rel == "repo/summary.idx":
        return PHASE_SUMMARY_IDX
    if rel == "repo/summary.sig":
        return PHASE_SUMMARY_SIG
    if rel == "repo/summary":
        return PHASE_SUMMARY
    return PHASE_METADATA


def ordered_rel_paths(root: Path) -> list[str]:
    rels = sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )
    return sorted(rels, key=lambda r: (upload_phase(r), r))


def upload_workers() -> int:
    raw = os.environ.get("BUNNY_UPLOAD_WORKERS", str(DEFAULT_WORKERS))
    try:
        n = int(raw)
    except ValueError:
        n = DEFAULT_WORKERS
    return max(1, min(n, MAX_WORKERS))


def put_file(
    url: str,
    body: bytes,
    access_key: str,
    content_type: str,
    max_attempts: int = 4,
) -> None:
    checksum = hashlib.sha256(body).hexdigest().upper()
    timeout = 600 if len(body) > 50_000_000 else 120
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            data=body,
            method="PUT",
            headers={
                "AccessKey": access_key,
                "Content-Type": content_type,
                "Checksum": checksum,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: BAN-B310
                code = resp.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
            err_body = e.read(500)
            if code in (200, 201):
                return
            if 500 <= code < 600 and attempt < max_attempts:
                time.sleep(0.5 * (2 ** (attempt - 1)))
                continue
            raise SystemExit(
                f"HTTP {code} for {url}: {err_body!r}",
            ) from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_attempts:
                time.sleep(0.5 * (2 ** (attempt - 1)))
                continue
            raise SystemExit(f"request failed for {url}: {e}") from e
        else:
            if code in (200, 201):
                return
            raise SystemExit(f"unexpected status {code} for {url}")


def get_json(url: str, access_key: str, timeout: int = 120) -> object:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"AccessKey": access_key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: BAN-B310
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def delete_path(url: str, access_key: str, timeout: int = 120) -> None:
    req = urllib.request.Request(
        url,
        method="DELETE",
        headers={"AccessKey": access_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: BAN-B310
            code = resp.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
        if code == 404:
            return
        e.read(500)
        raise SystemExit(f"HTTP {code} DELETE {url}") from e
    else:
        if code not in (200, 201, 204):
            raise SystemExit(f"unexpected DELETE status {code} for {url}")


def list_remote_files(
    base: str,
    access_key: str,
    prefix: str,
) -> set[str]:
    """Recursively list object-relative paths under prefix (no trailing slash)."""
    base = base.rstrip("/")
    prefix = prefix.strip("/")
    found: set[str] = set()

    def walk(rel_dir: str) -> None:
        list_rel = rel_dir.strip("/")
        list_url = f"{base}/{encode_object_rel(list_rel)}/" if list_rel else f"{base}/"
        try:
            listing = get_json(list_url, access_key)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return
            raise
        if not isinstance(listing, list):
            return
        for item in listing:
            if not isinstance(item, dict):
                continue
            name = item.get("ObjectName")
            if not name or not isinstance(name, str):
                continue
            child = f"{list_rel}/{name}" if list_rel else name
            if item.get("IsDirectory"):
                walk(child)
            else:
                found.add(child)

    walk(prefix)
    return found


def prune_remote_orphans(
    base: str,
    access_key: str,
    prefix: str,
    local_rels: set[str],
) -> None:
    """Delete remote objects/deltas files missing from the local export."""
    base = base.rstrip("/")
    prefix = prefix.strip("/")
    remote = list_remote_files(base, access_key, prefix)
    for remote_rel in sorted(remote):
        # remote_rel includes prefix (e.g. flatpak/repo/objects/..)
        if not remote_rel.startswith(f"{prefix}/"):
            continue
        under = remote_rel[len(prefix) + 1 :]
        if not (under.startswith("repo/objects/") or under.startswith("repo/deltas/")):
            continue
        if under in local_rels:
            continue
        url = f"{base}/{encode_object_rel(remote_rel)}"
        print(f"orphan prune: DELETE {url}", file=sys.stderr, flush=True)
        delete_path(url, access_key)


def _upload_one(
    root: Path,
    rel: str,
    base: str,
    prefix: str,
    access_key: str,
) -> str:
    object_rel = f"{prefix}/{rel}" if prefix else rel
    url = f"{base}/{encode_object_rel(object_rel)}"
    path = root / rel
    body = path.read_bytes()
    put_file(url, body, access_key, mime_for(path))
    return f"phase={upload_phase(rel)} {url}"


def upload_ostree_tree(
    root: Path,
    base: str,
    access_key: str,
    prefix: str = DEFAULT_PREFIX,
    prune_orphans: bool = True,
    workers: int | None = None,
) -> int:
    rels = ordered_rel_paths(root)
    if not rels:
        print(f"no files under {root}", file=sys.stderr, flush=True)
        return 1
    if "repo/config" not in rels:
        print("missing repo/config under export root", file=sys.stderr, flush=True)
        return 1

    base = base.rstrip("/")
    prefix = prefix.strip("/")
    local_set = set(rels)
    pool = upload_workers() if workers is None else max(1, min(workers, MAX_WORKERS))

    by_phase: dict[int, list[str]] = {}
    for rel in rels:
        by_phase.setdefault(upload_phase(rel), []).append(rel)

    print(
        f"bunny ostree upload: {len(rels)} files in {len(by_phase)} phases "
        f"workers={pool}",
        flush=True,
    )

    for phase in sorted(by_phase):
        batch = by_phase[phase]
        print(f"bunny ostree phase={phase} files={len(batch)}", flush=True)
        if pool == 1 or len(batch) == 1:
            for rel in batch:
                print(
                    _upload_one(root, rel, base, prefix, access_key),
                    flush=True,
                )
            continue
        with ThreadPoolExecutor(max_workers=pool) as ex:
            futures = [
                ex.submit(_upload_one, root, rel, base, prefix, access_key)
                for rel in batch
            ]
            for fut in as_completed(futures):
                print(fut.result(), flush=True)

    if prune_orphans:
        prune_remote_orphans(base, access_key, prefix, local_set)
    return 0


def main() -> None:
    base = os.environ.get("BUNNY_STORAGE_BASE_URL", "").rstrip("/")
    key = os.environ.get("BUNNY_STORAGE_ACCESS_KEY", "")
    prefix = os.environ.get(
        "BUNNY_FLATPAK_STORAGE_PREFIX",
        DEFAULT_PREFIX,
    ).strip("/")
    if not base or not key:
        print(
            "BUNNY_STORAGE_BASE_URL and BUNNY_STORAGE_ACCESS_KEY must be set",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <flatpak-export-directory>", file=sys.stderr)
        sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(1)
    sys.exit(upload_ostree_tree(root, base, key, prefix))


if __name__ == "__main__":
    main()
