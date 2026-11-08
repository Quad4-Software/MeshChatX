#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Harden LXST's PulseAudio binding against stripped asserts and NULL ops.

Upstream LXST 0.5.x uses ``assert`` for control flow in the Linux
soundcard backend and unconditionally unrefs the ``pa_operation *``
returned by PulseAudio calls. cx_Freeze builds run with ``optimize=2``,
which strips every ``assert``: on hosts without a reachable PulseAudio
server the context never reaches PA_CONTEXT_READY, the stripped assert
no longer raises, and the first ``pa_context_get_server_info`` call
unrefs a NULL operation. ``pa_operation_unref(NULL)`` trips a C-level
``assert(o)`` inside libpulse and aborts the whole process — Python
``try/except`` cannot catch it.

This patch:

* replaces the READY assert with an explicit ``RuntimeError`` raise so
  import fails cleanly (and catchably) when no PulseAudio server exists;
* NULL-guards ``pa_operation_unref`` in ``_lock_and_block`` so a dead
  context or a vanished server degrades to an exception instead of a
  process abort;
* converts the remaining ``assert``-as-validation statements in the same
  file to explicit raises for the same reason.

Idempotent. Run with the project interpreter after ``uv sync``:

    .venv/bin/python scripts/patch_lxst_pulseaudio_hardened.py
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

_MARKER = "# meshchatx-lxst-pulse-hardened (do not remove)"

_REPLACEMENTS: list[tuple[str, str]] = [
    (
        "        assert self._pa_context_get_state(self.context)==_pa.PA_CONTEXT_READY\n",
        (
            "        # meshchatx-lxst-pulse-hardened (do not remove)\n"
            "        if self._pa_context_get_state(self.context) != _pa.PA_CONTEXT_READY:\n"
            '            raise RuntimeError("pulseaudio context failed to become ready")\n'
        ),
    ),
    (
        (
            "        self._block_operation(operation)\n"
            "        self._pa_operation_unref(operation)\n"
        ),
        (
            "        self._block_operation(operation)\n"
            "        if operation != _ffi.NULL:\n"
            "            self._pa_operation_unref(operation)\n"
        ),
    ),
    (
        (
            "        assert name is not None\n"
            "        return name\n"
        ),
        (
            "        if name is None:\n"
            '            raise RuntimeError("pulseaudio client info callback did not fire")\n'
            "        return name\n"
        ),
    ),
    (
        (
            "        assert rv is not None\n"
            "        if rv == 0:\n"
        ),
        (
            "        if rv is None:\n"
            '            raise RuntimeError("pulseaudio set_name callback did not fire")\n'
            "        if rv == 0:\n"
        ),
    ),
]


def _lxst_file(*parts: str) -> Path | None:
    try:
        dist = importlib.metadata.distribution("lxst")
    except importlib.metadata.PackageNotFoundError:
        return None
    for rel in dist.files or ():
        if tuple(rel.parts[-len(parts) :]) == parts:
            return Path(dist.locate_file(rel))
    return None


def main() -> int:
    soundcard = _lxst_file("Platforms", "linux", "soundcard.py")
    if soundcard is None:
        print(
            "patch_lxst_pulseaudio_hardened: lxst soundcard.py not found, "
            "nothing to do",
            file=sys.stderr,
        )
        return 0

    text = soundcard.read_text(encoding="utf-8")
    if _MARKER in text:
        print(
            f"patch_lxst_pulseaudio_hardened: already patched ({soundcard})"
        )
        return 0

    patched = text
    applied = 0
    for old, new in _REPLACEMENTS:
        if old in patched:
            patched = patched.replace(old, new, 1)
            applied += 1
        else:
            print(
                "patch_lxst_pulseaudio_hardened: expected snippet not found, "
                f"skipping replacement {applied + 1}: {old[:60]!r}",
                file=sys.stderr,
            )

    if applied == 0:
        print(
            "patch_lxst_pulseaudio_hardened: no replacements applied; "
            "LXST version may have changed",
            file=sys.stderr,
        )
        return 1

    soundcard.write_text(patched, encoding="utf-8")
    print(
        f"patch_lxst_pulseaudio_hardened: applied {applied} fix(es) "
        f"({soundcard})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
