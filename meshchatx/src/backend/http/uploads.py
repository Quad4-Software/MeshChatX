# SPDX-License-Identifier: 0BSD

"""Bounded reads for aiohttp request bodies and multipart fields.

Route handlers used to hand-roll while-read_chunk loops with slightly
different (or missing) byte caps. An unbounded field.read() is a memory
exhaustion vector, so every client-supplied body or field should flow
through these helpers with an explicit per-endpoint limit.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os


class PayloadTooLargeError(ValueError):
    """Raised when a request body or multipart field exceeds its byte cap."""


# Default cap for request.json() bodies and small multipart text fields.
# JSON endpoints take config or command payloads; anything larger is a
# feature-specific upload and must declare its own limit.
DEFAULT_JSON_BODY_BYTES = 1024 * 1024
DEFAULT_TEXT_FIELD_BYTES = 64 * 1024

_MIB = 1024 * 1024
_GIB = 1024 * 1024 * 1024

# Per-endpoint byte caps for route-local uploads, kept in one table so
# limits can be audited without reading handlers. Feature-owned caps stay
# in their feature modules instead: MAX_PLUGIN_ZIP_BYTES in plugin_guard,
# MANAGER_UPLOAD_MAX_BYTES in rns_filesync_handler, _MAX_MODULE_BYTES in
# interface_module_store.
UPLOAD_LIMITS: dict[str, int] = {
    "map_offline_mbtiles": 2 * _GIB,
    "database_restore": 1 * _GIB,
    "docs_zip": 64 * _MIB,
    "page_node_file": 64 * _MIB,
    "message_import": 64 * _MIB,
    "translation_pack": 512 * _MIB,
    "repository_upload": 256 * _MIB,
    "audio_upload": 64 * _MIB,
}


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
    left behind. Writes run via asyncio.to_thread so multi-hundred-MB
    uploads do not block the event loop.
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
                await asyncio.to_thread(handle.write, chunk)
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


async def read_field_text_limited(
    field,
    max_bytes: int = DEFAULT_TEXT_FIELD_BYTES,
    *,
    chunk_size: int = 65536,
) -> str:
    """Read a multipart text field, capped at max_bytes.

    Mirrors field.text() charset handling (content-type charset, default
    utf-8) but bounds the buffer so an unbounded text field cannot exhaust
    memory.
    """
    raw = await read_field_limited(field, max_bytes, chunk_size=chunk_size)
    decode = getattr(field, "decode", None)
    if callable(decode):
        raw = decode(raw)
    get_charset = getattr(field, "get_charset", None)
    charset = "utf-8"
    if callable(get_charset):
        try:
            resolved = get_charset(default="utf-8")
            if isinstance(resolved, str) and resolved:
                charset = resolved
        except Exception:
            pass
    return raw.decode(charset, errors="replace")


async def read_json_limited(
    request,
    max_bytes: int = DEFAULT_JSON_BODY_BYTES,
    *,
    chunk_size: int = 65536,
):
    """Read a JSON request body, capped at max_bytes.

    Raises PayloadTooLargeError over the cap and json.JSONDecodeError on
    malformed JSON so existing except clauses keep working. aiohttp
    requests always carry .content; the request.json fallback exists so
    legacy test fakes that only stub json() still exercise handlers.
    """
    if getattr(request, "content", None) is None:
        return await request.json()
    raw = await read_body_limited(request, max_bytes, chunk_size=chunk_size)
    return json.loads(raw.decode("utf-8"))
