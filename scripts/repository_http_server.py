#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""CLI wrapper: plain HTTP file server for a MeshChatX repository-server directory."""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from meshchatx.repository_http_standalone import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
