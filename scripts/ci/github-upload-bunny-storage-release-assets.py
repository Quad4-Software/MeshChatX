#!/usr/bin/env python3
"""Upload a directory tree to bunny.net Edge Storage (HTTP PUT per object)."""

from __future__ import annotations

import hashlib
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
