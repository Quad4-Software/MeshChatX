# SPDX-License-Identifier: 0BSD

"""Bounded reads for aiohttp request bodies and multipart fields.

Route handlers used to hand-roll while-read_chunk loops with slightly
different (or missing) byte caps. An unbounded field.read() is a memory
exhaustion vector, so every client-supplied body or field should flow
through these helpers with an explicit per-endpoint limit.
"""

from __future__ import annotations

import contextlib
import os


class PayloadTooLargeError(ValueError):
    """Raised when a request body or multipart field exceeds its byte cap."""


async def read_field_limited(
    field,
    max_bytes: int,
    *,
    chunk_size: int = 65536,
) -> bytes:
    """Read a multipart field fully into memory, capped at max_bytes.

    Raises PayloadTooLargeError once the cap is exceeded; the unread
    remainder is left for aiohttp to drain. Use only for payloads that
    legitimately fit in memory (archives, images); stream to disk for
    larger uploads.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await field.read_chunk(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError("Upload exceeds size limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def write_field_to_path(
    field,
    path: str | os.PathLike[str],
    max_bytes: int,
    *,
    chunk_size: int = 65536,
) -> int:
    """Stream a multipart field to path, capped at max_bytes.

    Returns the bytes written. On a cap breach or write error the
    partial file is unlinked before raising so no truncated upload is
    left behind.
    """
    total = 0
    try:
        with open(path, "wb") as handle:
            while True:
                chunk = await field.read_chunk(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise PayloadTooLargeError("Upload exceeds size limit")
                handle.write(chunk)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(path)
        raise
    return total


async def read_body_limited(
    request,
    max_bytes: int,
    *,
    chunk_size: int = 65536,
) -> bytes:
    """Read a non-multipart request body fully, capped at max_bytes."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.content.iter_chunked(chunk_size):
        total += len(chunk)
        if total > max_bytes:
            raise PayloadTooLargeError("Request body exceeds size limit")
        chunks.append(chunk)
    return b"".join(chunks)
