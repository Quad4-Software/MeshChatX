#!/usr/bin/env python3
"""Upload a directory tree to bunny.net Edge Storage (HTTP PUT per object)."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote


def encode_object_rel(rel: str) -> str:
    return "/".join(quote(part, safe="") for part in rel.split("/"))


def mime_for(path: Path) -> str:
    if path.suffix.lower() == ".wasm":
        return "application/wasm"
    guessed, _enc = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def get_json(url: str, access_key: str, timeout: int = 120) -> object:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"AccessKey": access_key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def delete_path(url: str, access_key: str, timeout: int = 120) -> None:
    req = urllib.request.Request(
        url,
        method="DELETE",
        headers={"AccessKey": access_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def prune_other_versions(
    base: str,
    access_key: str,
    track: str,
    keep_version: str,
) -> None:
    """Remove every version directory under ``track/`` except ``keep_version``."""
    base = base.rstrip("/")
    list_url = f"{base}/{encode_object_rel(track)}/"
    try:
        listing = get_json(list_url, access_key)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return
        raise
    if not isinstance(listing, list):
        return
    seen: set[str] = set()
    for item in listing:
        if not isinstance(item, dict):
            continue
        if not item.get("IsDirectory"):
            continue
        name = item.get("ObjectName")
        if not name or not isinstance(name, str):
            continue
        if name in seen:
            continue
        seen.add(name)
        if name == keep_version:
            continue
        rel = f"{track}/{name}"
        delete_url = f"{base}/{encode_object_rel(rel)}"
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
            with urllib.request.urlopen(req, timeout=timeout) as resp:
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
    if prefix:
        seg = prefix.split("/", 1)
        if len(seg) == 2 and seg[0] in ("master", "dev"):
            prune_other_versions(base, key, seg[0], seg[1])
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        print(f"no files under {root}", file=sys.stderr)
        sys.exit(1)

    for path in files:
        rel = path.relative_to(root).as_posix()
        if prefix:
            object_rel = f"{prefix}/{rel}"
        else:
            object_rel = rel
        url = f"{base}/{encode_object_rel(object_rel)}"
        body = path.read_bytes()
        put_file(url, body, key, mime_for(path))
        print(url)


if __name__ == "__main__":
    main()
