#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Emit meshchatx/src/backend/data/community_interfaces.json from the directory API or a local export."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from meshchatx.src.backend.community_interfaces_directory import (
    rows_from_payload,
    transform_directory_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "meshchatx" / "src" / "backend" / "data" / "community_interfaces.json"

DEFAULT_SUBMITTED_URL = (
    "https://directory.rns.recipes/api/directory/submitted?status=online"
)
DEFAULT_DISCOVERED_URL = (
    "https://directory.rns.recipes/api/directory/discovered?status=online"
)
DEFAULT_DIRECTORY_URLS = (DEFAULT_SUBMITTED_URL, DEFAULT_DISCOVERED_URL)
_ALLOWED_HOST = "directory.rns.recipes"
_MAX_FETCH_BYTES = 1 * 1024 * 1024
_FETCH_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "MeshChatX-community-interfaces-build/1.0 (+https://meshchatx.com/)",
}


def validate_directory_fetch_url(url: str) -> str:
    if not url or not isinstance(url, str):
        msg = "URL must be a non-empty string"
        raise ValueError(msg)
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        msg = "Community directory URL must use https"
        raise ValueError(msg)
    netloc = parsed.netloc or ""
    if "@" in netloc:
        msg = "Community directory URL must not contain credentials"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if host != _ALLOWED_HOST:
        msg = "Community directory URL host is not allowed"
        raise ValueError(msg)
    return url.strip()


def fetch_directory_payload(url: str, *, timeout: float = 60.0) -> object:
    resolved = validate_directory_fetch_url(url)
    req = urllib.request.Request(resolved, headers=_FETCH_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(_MAX_FETCH_BYTES + 1)
    if len(raw) > _MAX_FETCH_BYTES:
        msg = f"Community directory download exceeds {_MAX_FETCH_BYTES} bytes"
        raise ValueError(msg)
    return json.loads(raw.decode("utf-8"))


def _merge_directory_rows(row_lists: list[list]) -> list:
    merged: list = []
    seen: set[tuple] = set()
    for rows in row_lists:
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = (
                str(row.get("name") or "").strip().lower(),
                str(row.get("type") or "").strip().lower(),
                str(row.get("host") or row.get("address") or "").strip().lower(),
                str(row.get("port") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    return merged


def build_interfaces_from_directory_url(
    url: str | None = None,
    *,
    timeout: float = 60.0,
) -> tuple[list[dict], str]:
    if url is not None and str(url).strip():
        resolved = validate_directory_fetch_url(url)
        payload = fetch_directory_payload(resolved, timeout=timeout)
        rows = rows_from_payload(payload)
        return transform_directory_rows(rows), resolved

    row_lists: list[list] = []
    used: list[str] = []
    errors: list[str] = []
    for candidate in DEFAULT_DIRECTORY_URLS:
        try:
            payload = fetch_directory_payload(candidate, timeout=timeout)
            row_lists.append(rows_from_payload(payload))
            used.append(candidate)
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
    if not used:
        msg = "; ".join(errors) if errors else "No directory URLs configured"
        raise ValueError(msg)
    rows = _merge_directory_rows(row_lists)
    return transform_directory_rows(rows), " + ".join(used)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help=f"Local JSON (directory data shape). Default: fetch {DEFAULT_SUBMITTED_URL}",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SUBMITTED_URL,
        help="Fetch URL override",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUT,
        help=f"Output path (default: {OUT})",
    )
    args = parser.parse_args()

    try:
        if args.source:
            payload = json.loads(Path(args.source).read_text(encoding="utf-8"))
            rows = rows_from_payload(payload)
            out_list = transform_directory_rows(rows)
            used_url = str(Path(args.source).resolve())
        else:
            out_list, used_url = build_interfaces_from_directory_url(
                args.url,
                timeout=60.0,
            )
    except OSError as e:
        print(f"Read/fetch failed: {e}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    doc = {
        "_comment": "build_community_interfaces_json.py; source: directory.rns.recipes online listings. "
        "RNode omitted. Backbone without transport_identity -> TCPClientInterface. "
        "Optional override: public/community_interfaces.json.",
        "_source": used_url,
        "interfaces": out_list,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(out_list)} interfaces to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
