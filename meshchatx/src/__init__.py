# SPDX-License-Identifier: 0BSD

"""Package init for meshchatx.src.

Wraps process stdout and stderr so each write is flushed. Electron and other
host processes that read child stdout via data events need this so log lines
arrive before process exit.
"""

from __future__ import annotations

import sys
from typing import Any, TextIO


class _LineFlushStream:
    """Proxy that flushes the underlying TextIO after every write."""

    __slots__ = ("_inner",)

    def __init__(self, inner: TextIO) -> None:
        self._inner = inner

    def write(self, data: str) -> int:
        written = self._inner.write(data)
        self._inner.flush()
        return written

    def writelines(self, lines: list[str]) -> None:
        self._inner.writelines(lines)
        self._inner.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


sys.stdout = _LineFlushStream(sys.stdout)  # type: ignore[assignment]
sys.stderr = _LineFlushStream(sys.stderr)  # type: ignore[assignment]
