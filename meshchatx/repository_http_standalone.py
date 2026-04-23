# SPDX-License-Identifier: 0BSD

"""Plain HTTP file server for a MeshChatX repository-server directory."""

from __future__ import annotations

import argparse
import os
import socketserver

from meshchatx.src.backend.repository_server_manager import (
    make_repository_http_request_handler,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve MeshChatX repository-server files over HTTP without TLS.",
    )
    parser.add_argument(
        "--directory",
        required=True,
        help="Path to the identity's repository-server folder (contains uploads/ and bundled/).",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Bind address (default 0.0.0.0)."
    )
    parser.add_argument(
        "--port", type=int, default=8787, help="TCP port (default 8787)."
    )
    parser.add_argument(
        "--public-dir",
        default=None,
        help="MeshChatX public directory (for repository-server-index.html when not next to source).",
    )
    args = parser.parse_args()
    root = os.path.abspath(args.directory)
    if not os.path.isdir(root):
        print(f"Not a directory: {root}", flush=True)
        return 2

    pub = os.path.abspath(args.public_dir) if args.public_dir else None
    handler_cls = make_repository_http_request_handler(root, public_dir=pub)
    httpd = socketserver.ThreadingTCPServer((args.host, args.port), handler_cls)
    httpd.allow_reuse_address = True
    print(
        f"Serving {root} at http://{args.host}:{args.port}/ (uploads/ and bundled/ subdirs)",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping.", flush=True)
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
