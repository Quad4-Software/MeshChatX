#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Emit meshchatx/src/backend/data/community_interfaces.json from the MeshChatX interfaces API or a local export."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from meshchatx.src.backend.community_interfaces_directory import (
    DEFAULT_DIRECTORY_URL,
    rows_from_payload,
    transform_directory_rows,
    validate_directory_fetch_url,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "meshchatx" / "src" / "backend" / "data" / "community_interfaces.json"

_MAX_FETCH_BYTES = 1 * 1024 * 1024
_FETCH_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "MeshChatX-community-interfaces-build/1.0 (+https://meshchatx.com/)",
}


def fetch_directory_payload(url: str, *, timeout: float = 60.0) -> object:
    resolved = validate_directory_fetch_url(url)
    req = urllib.request.Request(resolved, headers=_FETCH_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: BAN-B310
        raw = resp.read(_MAX_FETCH_BYTES + 1)
    if len(raw) > _MAX_FETCH_BYTES:
        msg = f"Community directory download exceeds {_MAX_FETCH_BYTES} bytes"
        raise ValueError(msg)
    return json.loads(raw.decode("utf-8"))


def build_interfaces_from_directory_url(
    url: str | None = None,
    *,
    timeout: float = 60.0,
) -> tuple[list[dict], str]:
    resolved = validate_directory_fetch_url(
        url if url is not None and str(url).strip() else DEFAULT_DIRECTORY_URL,
    )
    payload = fetch_directory_payload(resolved, timeout=timeout)
    rows = rows_from_payload(payload)
    return transform_directory_rows(rows), resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help=f"Local JSON (mcx-interfaces or legacy directory shape). Default: fetch {DEFAULT_DIRECTORY_URL}",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_DIRECTORY_URL,
        help="Fetch URL override (https://meshchatx.com only)",
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
        "_comment": "build_community_interfaces_json.py. Source: https://meshchatx.com/api/mcx-interfaces. "
        "RNode omitted. Backbone without transport_identity becomes TCPClientInterface. "
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
