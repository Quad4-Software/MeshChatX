# SPDX-License-Identifier: 0BSD
"""Oracle: SafeRotatingFileHandler does not thrash on EMFILE."""

from __future__ import annotations

import logging
from pathlib import Path

from meshchatx.src.backend.safe_rotating_file_handler import SafeRotatingFileHandler


def test_safe_rotating_handler_falls_back_when_open_fails(tmp_path, monkeypatch):
    log_path = Path(tmp_path) / "meshchatx.log"
    handler = SafeRotatingFileHandler(
        str(log_path),
        maxBytes=1024,
        backupCount=1,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))

    def boom(*_args, **_kwargs):
        raise OSError(24, "No file descriptors available")

    # Simulate stream lost after rollover close, then reopen failing with EMFILE.
    if handler.stream is not None:
        handler.stream.close()
    handler.stream = None
    monkeypatch.setattr(handler, "_open", boom)

    record = logging.LogRecord(
        name="meshchatx",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="socket.accept() out of system resource",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    handler.emit(record)

    assert handler._open_failed is True
    assert handler.stream is None
