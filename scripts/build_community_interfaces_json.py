#!/usr/bin/env python3
"""Emit meshchatx/src/backend/data/community_interfaces.json from the directory API or a local export."""
# ruff: noqa: T201

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from meshchatx.src.backend.community_interfaces_directory import (
    DEFAULT_SUBMITTED_URL,
    rows_from_payload,
    transform_directory_rows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "meshchatx" / "src" / "backend" / "data" / "community_interfaces.json"


def fetch_json(url: str, timeout: float = 60.0) -> dict | list:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MeshChatX-community-interfaces-build/1.0 (+https://meshchatx.com/)",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help=f"Local JSON (directory `data` shape). Default: fetch {DEFAULT_SUBMITTED_URL}",
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
        else:
            payload = fetch_json(args.url)
    except OSError as e:
        print(f"Read/fetch failed: {e}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        rows = rows_from_payload(payload)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1

    out_list = transform_directory_rows(rows)
    doc = {
        "_comment": "build_community_interfaces_json.py; source: directory.rns.recipes online listings. "
        "RNode omitted. Backbone without transport_identity -> TCPClientInterface. "
        "Optional override: public/community_interfaces.json.",
        "_source": args.url if not args.source else str(Path(args.source).resolve()),
        "interfaces": out_list,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(out_list)} interfaces to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
