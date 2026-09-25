#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Upload a directory tree to bunny.net Edge Storage (HTTP PUT per object).

When ``BUNNY_STORAGE_OBJECT_PREFIX`` is ``<track>/<version>`` with track in
``release``, ``testing``, or ``beta``, older version directories under that
track are pruned after a successful upload so only the newest
``KEEP_VERSIONS`` folders remain.

Legacy ``nightly`` prefixes are accepted and remapped to ``testing``.

Modes:
    upload <dir>   upload tree, then prune the track to KEEP_VERSIONS
    prune          prune every keep-track to KEEP_VERSIONS, no upload

Upload behavior:
- Objects already on Bunny with a matching SHA256 checksum are skipped so
  unchanged artifacts keep their warm edge caches (a PUT rewrites the object
  and can invalidate cached copies).
- Metadata/index files (.sha256, .json, .txt, .flatpakref, checksums.txt,
  openvex.json, sbom.cyclonedx.json) upload last so a fetched manifest never
  references artifacts that are still uploading.
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

KEEP_TRACKS = frozenset({"release", "testing", "beta"})
KEEP_VERSIONS = int(os.environ.get("BUNNY_KEEP_VERSIONS", "4"))
TRACK_ALIASES = {
    "nightly": "testing",
    "preview": "beta",
}

# Match scripts/ci/github-draft-release-upload-assets.sh skip_noise.
_SKIP_BASENAME_EXACT = frozenset(
    {
        "builder-debug.yml",
        "builder-debug.yml.cosign.bundle",
        "library.zip",
        "library.zip.cosign.bundle",
    }
)


def encode_object_rel(rel: str) -> str:
    return "/".join(quote(part, safe="") for part in rel.split("/"))


def mime_for(path: Path) -> str:
    if path.suffix.lower() == ".wasm":
        return "application/wasm"
    guessed, _enc = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def should_skip_file(path: Path) -> bool:
    name = path.name
    if name in _SKIP_BASENAME_EXACT:
        return True
    if name.endswith("__builder-debug.yml") or name.endswith(
        "__builder-debug.yml.cosign.bundle"
    ):
        return True
    if name.endswith("__library.zip") or name.endswith("__library.zip.cosign.bundle"):
        return True
    if name.endswith(".so.yml") or name.endswith(".so.yml.cosign.bundle"):
        return True
    return False


def parse_track_version(prefix: str) -> tuple[str, str] | None:
    """Return (track, version) when prefix is a pruneable track/version path."""
    cleaned = prefix.strip("/")
    if not cleaned:
        return None
    parts = cleaned.split("/", 1)
    if len(parts) != 2:
        return None
    track, version = parts
    track = TRACK_ALIASES.get(track, track)
    if track not in KEEP_TRACKS or not version or "/" in version:
        return None
    return track, version


def get_json(url: str, access_key: str, timeout: int = 120) -> object:
    req = urllib.request.Request(  # noqa: S310 - CI storage endpoint
        url,
        method="GET",
        headers={"AccessKey": access_key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - CI storage endpoint
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def delete_path(url: str, access_key: str, timeout: int = 120) -> None:
    req = urllib.request.Request(  # noqa: S310 - CI storage endpoint
        url,
        method="DELETE",
        headers={"AccessKey": access_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - CI storage endpoint
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


def _list_remote_checksums(
    base: str,
    access_key: str,
    prefix: str,
    depth: int = 0,
) -> dict[str, str]:
    """Return ``{relative_path: sha256}`` for files under ``prefix`` on Bunny.

    Bunny list responses carry an uppercase hex ``Checksum`` per file, which
    lets the uploader skip unchanged objects instead of rewriting them (each
    rewrite can cold-start that object's edge cache).
    """
    if depth > 8:
        return {}
    base = base.rstrip("/")
    list_url = f"{base}/{encode_object_rel(prefix)}/"
    try:
        listing = get_json(list_url, access_key)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise
    if not isinstance(listing, list):
        return {}
    out: dict[str, str] = {}
    for item in listing:
        if not isinstance(item, dict):
            continue
        name = item.get("ObjectName")
        if not name or not isinstance(name, str):
            continue
        rel = f"{prefix}/{name}"
        if item.get("IsDirectory"):
            out.update(_list_remote_checksums(base, access_key, rel, depth + 1))
            continue
        checksum = item.get("Checksum")
        out[rel] = str(checksum).upper() if checksum else ""
    return out


# Index/metadata files are uploaded last so consumers fetching them never see
# a manifest pointing at artifacts that are still uploading.
_META_SUFFIXES = (
    ".sha256",
    ".json",
    ".txt",
    ".flatpakref",
    ".xml",
    ".md",
)
_META_NAMES = frozenset(
    {
        "checksums.txt",
        "openvex.json",
        "sbom.cyclonedx.json",
        "release-body.md",
    }
)


def _upload_order(path: Path, root: Path) -> tuple[bool, str]:
    rel = path.relative_to(root).as_posix()
    name = path.name.lower()
    is_meta = name in _META_NAMES or any(
        name.endswith(suffix) for suffix in _META_SUFFIXES
    )
    return (is_meta, rel)


def _list_version_dirs(base: str, access_key: str, track: str) -> list[dict]:
    """Return unique directory entries under ``track/``."""
    base = base.rstrip("/")
    list_url = f"{base}/{encode_object_rel(track)}/"
    try:
        listing = get_json(list_url, access_key)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    if not isinstance(listing, list):
        return []
    seen: set[str] = set()
    dirs: list[dict] = []
    for item in listing:
        if not isinstance(item, dict) or not item.get("IsDirectory"):
            continue
        name = item.get("ObjectName")
        if not name or not isinstance(name, str) or name in seen:
            continue
        seen.add(name)
        dirs.append(item)
    return dirs


def prune_other_versions(
    base: str,
    access_key: str,
    track: str,
    keep_version: str,
    keep_count: int = KEEP_VERSIONS,
) -> None:
    """Keep ``keep_version`` plus the newest ``keep_count`` dirs under ``track/``.

    "Newest" is Bunny's ``LastChanged`` timestamp, which tracks the upload
    date rather than the version string, so nightly/beta/stable names sort
    correctly. ``keep_version`` is always retained even when it would not
    rank in the top entries.
    """
    dirs = _list_version_dirs(base, access_key, track)
    # Newest first; name is a deterministic tie-break.
    dirs.sort(
        key=lambda it: (
            str(it.get("LastChanged") or ""),
            str(it.get("ObjectName") or ""),
        ),
        reverse=True,
    )
    keep = {keep_version}
    keep.update(str(it["ObjectName"]) for it in dirs[:keep_count])
    for item in dirs:
        name = item["ObjectName"]
        if name in keep:
            continue
        rel = f"{track}/{name}"
        delete_url = f"{base.rstrip('/')}/{encode_object_rel(rel)}"
        print(f"prune: DELETE {delete_url}", file=sys.stderr)
        delete_path(delete_url, access_key)


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
        req = urllib.request.Request(  # noqa: S310 - CI storage endpoint
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
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - CI storage endpoint
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


def collect_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and not should_skip_file(p))


def upload_tree(
    root: Path,
    base: str,
    access_key: str,
    prefix: str,
) -> int:
    files = collect_files(root)
    if not files:
        print(f"no files under {root}", file=sys.stderr)
        return 1

    base = base.rstrip("/")
    prefix = prefix.strip("/")
    remote = _list_remote_checksums(base, access_key, prefix) if prefix else {}
    workers = max(1, min(int(os.environ.get("BUNNY_UPLOAD_WORKERS", "8")), 24))

    def _put(path: Path) -> str | None:
        rel = path.relative_to(root).as_posix()
        object_rel = f"{prefix}/{rel}" if prefix else rel
        body = path.read_bytes()
        local_sha = hashlib.sha256(body).hexdigest().upper()
        if remote.get(object_rel) == local_sha:
            return None
        url = f"{base}/{encode_object_rel(object_rel)}"
        put_file(url, body, access_key, mime_for(path))
        return url

    # Artifacts first (parallel), metadata/index files last (sequential) so a
    # fetched manifest never references an object that is still uploading.
    meta, blobs = [], []
    for path in sorted(files, key=lambda p: _upload_order(p, root)):
        (meta if _upload_order(path, root)[0] else blobs).append(path)

    uploaded = skipped = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_put, p): p for p in blobs}
        for fut in as_completed(futs):
            url = fut.result()
            if url is None:
                skipped += 1
            else:
                uploaded += 1
                print(url)
    for path in meta:
        url = _put(path)
        if url is None:
            skipped += 1
        else:
            uploaded += 1
            print(url)
    print(f"uploaded {uploaded}, skipped {skipped} unchanged", file=sys.stderr)

    parsed = parse_track_version(prefix)
    if parsed is not None:
        track, version = parsed
        prune_other_versions(base, access_key, track, version)
    return 0


def prune_all_tracks(base: str, access_key: str) -> int:
    for track in sorted(KEEP_TRACKS):
        print(f"prune: track {track} -> keep {KEEP_VERSIONS}", file=sys.stderr)
        prune_other_versions(base, access_key, track, keep_version="")
    return 0


def main() -> None:
    base = os.environ.get("BUNNY_STORAGE_BASE_URL", "").rstrip("/")
    key = os.environ.get("BUNNY_STORAGE_ACCESS_KEY", "")
    prefix = os.environ.get("BUNNY_STORAGE_OBJECT_PREFIX", "").strip("/")
    if not base or not key:
        print(
            "BUNNY_STORAGE_BASE_URL and BUNNY_STORAGE_ACCESS_KEY must be set",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <directory>|prune", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "prune":
        sys.exit(prune_all_tracks(base, key))
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(1)
    sys.exit(upload_tree(root, base, key, prefix))


if __name__ == "__main__":
    main()
