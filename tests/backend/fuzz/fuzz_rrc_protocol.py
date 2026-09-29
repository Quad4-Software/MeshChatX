#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Coverage-guided fuzz targets for the RRC wire format and parsers.

Run directly (bounded by libFuzzer flags, e.g. -runs=20000 or
-max_total_time=30) or via the pytest wrapper, which executes each
target as a bounded subprocess. Any uncaught exception aborts the run
and is reported as a finding; the minimizer then shrinks the input.
"""

from __future__ import annotations

import sys

import atheris

with atheris.instrument_imports():
    import cborx

    from meshchatx.src.backend.rrc import protocol as proto


def fuzz_decode(data: bytes) -> None:
    """Envelope decode: arbitrary bytes must not crash.

    CBORDecodeError is the documented malformed-input path (callers
    already catch it); anything else is a finding.
    """
    try:
        proto.decode(data)
    except cborx.CBORDecodeError:
        return


def fuzz_room_list_notice(data: bytes) -> None:
    """Room-list notice parser: arbitrary text must not crash."""
    try:
        text = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return
    proto.parse_room_list_notice_details(text)


def fuzz_normalize_room(data: bytes) -> None:
    try:
        text = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return
    try:
        proto.normalize_room(text)
    except ValueError:
        # Documented rejection path (empty, invalid unicode).
        return


def fuzz_parse_who(data: bytes) -> None:
    try:
        text = data.decode("utf-8", errors="surrogateescape")
    except Exception:
        return
    proto.parse_who_notice(text)


_TARGETS = {
    "decode": fuzz_decode,
    "room_list": fuzz_room_list_notice,
    "room_name": fuzz_normalize_room,
    "who": fuzz_parse_who,
}


def main() -> None:
    args = list(sys.argv)
    target = "decode"
    if len(args) > 1 and not args[1].startswith("-"):
        target = args.pop(1)
    if target not in _TARGETS:
        print(f"unknown target {target}; options: {sorted(_TARGETS)}", file=sys.stderr)
        raise SystemExit(2)
    atheris.Setup(args, _TARGETS[target])
    atheris.Fuzz()


if __name__ == "__main__":
    main()
