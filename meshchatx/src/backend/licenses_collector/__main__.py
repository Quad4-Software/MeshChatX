# SPDX-License-Identifier: 0BSD
"""CLI entry for licenses:refresh (python -m meshchatx.src.backend.licenses_collector)."""

from meshchatx.src.backend.licenses_collector.core import main

if __name__ == "__main__":
    raise SystemExit(main())
