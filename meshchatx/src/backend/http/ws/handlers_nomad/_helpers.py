# SPDX-License-Identifier: 0BSD

"""Shared helper functions for nomad WS handler slices."""

from __future__ import annotations

import hashlib

# ruff: noqa: F405

from meshchatx.src.backend.http.ws.handlers_nomad._names import *  # noqa: F403, F405
from meshchatx.src.backend.websocket_runtime import (
    WS_NOMAD_CHUNK_SIZE,
    WS_NOMAD_CHUNK_THRESHOLD,
    WS_NOMAD_FILE_MAX_BYTES,
    WS_NOMAD_PAGE_MAX_CHARS,
)


def _request_id_fields(data: dict) -> dict:
    rid = data.get("request_id")
    if rid is None:
        return {}
    if isinstance(rid, str):
        rid = rid.strip()
        if len(rid) > 64 or not rid:
            return {}
        return {"request_id": rid}
    if isinstance(rid, (int, float)) and 0 <= rid < 2**63:
        return {"request_id": rid}
    return {}


def _is_nomad_image_request(extra: dict | None) -> bool:
    if not isinstance(extra, dict):
        return False
    return extra.get("image_id") is not None


_SUPPORTED_NOMAD_IMAGE_TYPES = frozenset({"webp", "png", "jpeg", "bmp", "gif", "tiff"})


def _validate_nomad_image_bytes(file_bytes: bytes | None) -> bool:
    if not file_bytes:
        return False
    return detect_image_format_from_magic(file_bytes) in _SUPPORTED_NOMAD_IMAGE_TYPES


async def _send_nomad_file_bytes(
    client,
    *,
    download_id,
    destination_hash_hex: str,
    file_path: str,
    file_name: str,
    file_bytes: bytes,
    private: bool,
    request_id_fields: dict,
    extra: dict | None = None,
):
    """Single-frame for small files; chunked frames for large ones."""
    if len(file_bytes) > WS_NOMAD_FILE_MAX_BYTES:
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_file_download": {
                        "status": "failure",
                        "failure_reason": "file_too_large",
                        "destination_hash": destination_hash_hex,
                        "file_path": file_path,
                    },
                },
            ),
        )
        return
    if len(file_bytes) <= WS_NOMAD_CHUNK_THRESHOLD:
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_file_download": {
                        "status": "success",
                        "destination_hash": destination_hash_hex,
                        "file_path": file_path,
                        "file_name": file_name,
                        "file_bytes": base64.b64encode(file_bytes).decode("utf-8"),
                        "private": private,
                        **({"data": extra} if extra is not None else {}),
                    },
                },
            ),
        )
        return
    total = len(file_bytes)
    offset = 0
    chunk_index = 0
    while offset < total:
        chunk = file_bytes[offset : offset + WS_NOMAD_CHUNK_SIZE]
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_file_download": {
                        "status": "chunk",
                        "destination_hash": destination_hash_hex,
                        "file_path": file_path,
                        "file_name": file_name,
                        "offset": offset,
                        "total": total,
                        "chunk_index": chunk_index,
                        "chunk_b64": base64.b64encode(chunk).decode("utf-8"),
                        "private": private,
                        **({"data": extra} if extra is not None else {}),
                    },
                },
            ),
        )
        offset += len(chunk)
        chunk_index += 1
    import hashlib

    digest = hashlib.sha256(file_bytes).hexdigest()
    await client.send_str(
        json.dumps(
            {
                "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                "download_id": download_id,
                **request_id_fields,
                "nomadnet_file_download": {
                    "status": "success",
                    "destination_hash": destination_hash_hex,
                    "file_path": file_path,
                    "file_name": file_name,
                    "chunked": True,
                    "total": total,
                    "sha256": digest,
                    "private": private,
                    **({"data": extra} if extra is not None else {}),
                },
            },
        ),
    )


async def _send_nomad_page_content(
    client,
    *,
    download_id,
    destination_hash_hex: str,
    page_path: str,
    page_content: str,
    private: bool,
    request_id_fields: dict,
    extra: dict | None = None,
):
    if not isinstance(page_content, str):
        page_content = str(page_content)
    if len(page_content) > WS_NOMAD_PAGE_MAX_CHARS:
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_page_download": {
                        "status": "failure",
                        "failure_reason": "page_too_large",
                        "destination_hash": destination_hash_hex,
                        "page_path": page_path,
                    },
                },
            ),
        )
        return
    body = {
        "status": "success",
        "destination_hash": destination_hash_hex,
        "page_path": page_path,
        "page_content": page_content,
        "private": private,
    }
    if extra:
        body.update(extra)
    if len(page_content.encode("utf-8", errors="replace")) <= WS_NOMAD_CHUNK_THRESHOLD:
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_page_download": body,
                },
            ),
        )
        return
    raw = page_content.encode("utf-8", errors="replace")
    total = len(raw)
    offset = 0
    chunk_index = 0
    while offset < total:
        chunk = raw[offset : offset + WS_NOMAD_CHUNK_SIZE]
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                    "download_id": download_id,
                    **request_id_fields,
                    "nomadnet_page_download": {
                        "status": "chunk",
                        "destination_hash": destination_hash_hex,
                        "page_path": page_path,
                        "offset": offset,
                        "total": total,
                        "chunk_index": chunk_index,
                        "chunk_b64": base64.b64encode(chunk).decode("utf-8"),
                        "private": private,
                    },
                },
            ),
        )
        offset += len(chunk)
        chunk_index += 1
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    body = {
        "status": "success",
        "destination_hash": destination_hash_hex,
        "page_path": page_path,
        "chunked": True,
        "total": total,
        "sha256": digest,
        "private": private,
    }
    if extra:
        body.update({k: v for k, v in extra.items() if k != "page_content"})
    await client.send_str(
        json.dumps(
            {
                "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                "download_id": download_id,
                **request_id_fields,
                "nomadnet_page_download": body,
            },
        ),
    )


