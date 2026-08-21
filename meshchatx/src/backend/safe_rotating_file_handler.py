# SPDX-License-Identifier: 0BSD
"""Rotating file log handler that survives EMFILE without cascading errors."""

from __future__ import annotations

import sys
from logging.handlers import RotatingFileHandler


class SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that does not raise or thrash when FDs are exhausted.

    After a failed reopen (common under Errno 24), fall back to stderr once
    and skip further open attempts until a later emit succeeds at reopening.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._open_failed = False
        self._warned_open_failed = False

    def _open(self):
        try:
            stream = super()._open()
            self._open_failed = False
            return stream
        except OSError:
            self._open_failed = True
            raise

    def shouldRollover(self, record):
        if self._open_failed and self.stream is None:
            return False
        try:
            return super().shouldRollover(record)
        except OSError:
            self.stream = None
            self._open_failed = True
            return False

    def emit(self, record):
        try:
            if self.stream is None and not self.delay:
                try:
                    self.stream = self._open()
                except OSError:
                    self._open_failed = True
                    self._emit_fallback(record)
                    return
            super().emit(record)
        except OSError:
            self.stream = None
            self._open_failed = True
            self._emit_fallback(record)

    def _emit_fallback(self, record) -> None:
        if not self._warned_open_failed:
            self._warned_open_failed = True
            try:
                sys.stderr.write(
                    "meshchatx: log file reopen failed (likely too many open files)\n",
                )
            except Exception:
                pass
        try:
            msg = self.format(record)
            sys.stderr.write(msg + "\n")
        except Exception:
            pass
