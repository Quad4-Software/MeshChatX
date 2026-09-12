# SPDX-License-Identifier: 0BSD

"""Probe module for self-check --meshchatx-run-module verification."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    argv = sys.argv[1:]
    if argv[:1] == ["--check"] and len(argv) > 1:
        from meshchatx.src.backend import self_check

        result = self_check.run_probe(argv[1])
        print("SELF_CHECK_JSON:" + json.dumps(result), flush=True)
        return
    marker = os.environ.get("MESHCHATX_SELF_CHECK_PROBE_PATH")
    if marker:
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("ok\n")
            handle.write(" ".join(sys.argv[1:]))
            handle.write("\n")
    print("meshchatx-self-check-probe", *sys.argv[1:], flush=True)


if __name__ == "__main__":
    main()
