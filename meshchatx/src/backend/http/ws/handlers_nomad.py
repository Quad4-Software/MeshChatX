# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_nomad."""

from __future__ import annotations

import base64
import json
import time

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.constants import WsInboundType
from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    nomad_link_identity_kwargs,
)
from meshchatx.src.backend.nomadnet_utils import (
    convert_nomadnet_field_data_to_map,
    convert_nomadnet_string_data_to_map,
)
from meshchatx.src.backend.sticker_utils import detect_image_format_from_magic
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


async def handle_nomadnet_download_cancel(app, client, data):
    # get data from websocket client
    download_id = data.get("download_id")
    rid = _request_id_fields(data)
    if download_id is None:
        return

    # cancel the download. The RNS request callbacks run on another thread
    # and can pop the same key, so remove atomically rather than
    # check-then-delete.
    downloader = app.active_downloads.pop(download_id, None)
    if downloader is not None:
        downloader.cancel()

        # notify client
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.download.cancelled",
                        "download_id": download_id,
                        **rid,
                    },
                ),
            ),
        )

    # handle getting page archives


async def handle_nomadnet_page_archives_get(app, client, data):
    destination_hash = data.get("destination_hash")
    page_path = data.get("page_path")

    if not destination_hash or not page_path:
        return

    # Try relative path first
    archives = app.get_archived_page_versions(destination_hash, page_path)

    # If nothing found and path doesn't look like it's already absolute,
    # try searching with the destination hash prefix (support for old buggy archives)
    if not archives and not page_path.startswith(destination_hash):
        buggy_path = f"{destination_hash}:{page_path}"
        archives = app.get_archived_page_versions(destination_hash, buggy_path)

    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "nomadnet.page.archives",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                    "archives": [
                        {
                            "id": archive["id"],
                            "hash": archive["hash"],
                            "destination_hash": archive["destination_hash"],
                            "page_path": archive["page_path"],
                            "created_at": archive["created_at"].isoformat()
                            if hasattr(archive["created_at"], "isoformat")
                            else str(archive["created_at"]),
                        }
                        for archive in archives
                    ],
                },
            ),
        ),
    )

    # handle loading a specific archived page version


async def handle_nomadnet_page_archive_load(app, client, data):
    archive_id = data.get("archive_id")
    download_id = data.get("download_id")
    if archive_id is None:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "failure",
                            "destination_hash": "",
                            "page_path": "",
                            "failure_reason": "missing archive_id",
                        },
                    },
                ),
            ),
        )
        return

    archive = app.database.misc.get_archived_page_by_id(archive_id)

    if archive:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        "nomadnet_page_download": {
                            "status": "success",
                            "destination_hash": archive["destination_hash"],
                            "page_path": archive["page_path"],
                            "page_content": archive["content"],
                            "is_archived_version": True,
                            "archived_at": archive["created_at"],
                        },
                    },
                ),
            ),
        )
        return

    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                    "download_id": download_id,
                    "nomadnet_page_download": {
                        "status": "failure",
                        "destination_hash": "",
                        "page_path": "",
                        "failure_reason": "archive not found",
                    },
                },
            ),
        ),
    )

    # handle flushing all archived pages


async def handle_nomadnet_page_archive_flush(app, client, data):
    app.flush_all_archived_pages()
    # notify config updated
    AsyncUtils.run_async(app.send_config_to_websocket_clients())

    # handle manual page archiving


async def handle_nomadnet_page_archive_add(app, client, data):
    destination_hash = data.get("destination_hash")
    page_path = data.get("page_path")
    content = data.get("content")

    if not destination_hash or not page_path or not content:
        return

    app.archive_page(destination_hash, page_path, content, is_manual=True)

    # notify client that page was archived
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "nomadnet.page.archive.added",
                    "destination_hash": destination_hash,
                    "page_path": page_path,
                },
            ),
        ),
    )

    # handle downloading a file from a nomadnet node


async def handle_nomadnet_file_download(app, client, data):
    # get data from websocket client
    download_data = data.get("nomadnet_file_download")
    if not download_data:
        return

    destination_hash_hex = download_data.get("destination_hash")
    file_path = download_data.get("file_path")
    request_data = download_data.get("data")
    private = bool(download_data.get("private"))
    if isinstance(request_data, str):
        request_data = convert_nomadnet_string_data_to_map(request_data)
    elif request_data is None:
        request_data = {}

    if not destination_hash_hex or not file_path:
        return

    try:
        destination_hash = bytes.fromhex(destination_hash_hex)
    except ValueError:
        return

    rid = _request_id_fields(data)

    page_path = (
        request_data.get("page_path") if isinstance(request_data, dict) else None
    )
    local_file = app._try_serve_local_page_node_file(
        destination_hash,
        file_path,
        client=client,
        page_path=page_path,
        request_data=request_data,
    )
    if local_file is not None:
        file_name, file_bytes = local_file
        if _is_nomad_image_request(request_data) and not _validate_nomad_image_bytes(
            file_bytes
        ):
            await client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                        "download_id": 0,
                        **rid,
                        "nomadnet_file_download": {
                            "status": "failure",
                            "failure_reason": "invalid_image",
                            "destination_hash": destination_hash_hex,
                            "file_path": file_path,
                            **(
                                {"data": request_data}
                                if request_data is not None
                                else {}
                            ),
                        },
                    },
                ),
            )
            return
        async with app.download_id_lock:
            app.download_id_counter += 1
            download_id = app.download_id_counter
        await _send_nomad_file_bytes(
            client,
            download_id=download_id,
            destination_hash_hex=destination_hash.hex(),
            file_path=file_path,
            file_name=file_name,
            file_bytes=file_bytes,
            private=private,
            request_id_fields=rid,
            extra=request_data,
        )
        return

    # generate download id
    async with app.download_id_lock:
        app.download_id_counter += 1
        download_id = app.download_id_counter

    # handle successful file download
    def on_file_download_success(file_name, file_bytes):
        # remove from active downloads (callback thread races cancel)
        app.active_downloads.pop(download_id, None)

        if _is_nomad_image_request(request_data) and not _validate_nomad_image_bytes(
            file_bytes
        ):
            on_file_download_failure("invalid_image")
            return

        # Track download speed
        download_size = len(file_bytes)
        if hasattr(downloader, "start_time") and downloader.start_time:
            download_duration = time.time() - downloader.start_time
            if download_duration > 0:
                app.download_speeds.append((download_size, download_duration))
                # Keep only last 100 downloads for average calculation
                del app.download_speeds[:-100]

        AsyncUtils.run_async(
            _send_nomad_file_bytes(
                client,
                download_id=download_id,
                destination_hash_hex=destination_hash.hex(),
                file_path=file_path,
                file_name=file_name,
                file_bytes=file_bytes,
                private=private,
                request_id_fields=rid,
                extra=request_data,
            ),
        )

    # handle file download failure
    def on_file_download_failure(failure_reason):
        # remove from active downloads (callback thread races cancel)
        app.active_downloads.pop(download_id, None)

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_file_download": {
                            "status": "failure",
                            "failure_reason": failure_reason,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                            **(
                                {"data": request_data}
                                if request_data is not None
                                else {}
                            ),
                        },
                    },
                ),
            ),
        )

    # handle file download progress
    def on_file_download_progress(progress):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_file_download": {
                            "status": "progress",
                            "progress": progress,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                            **(
                                {"data": request_data}
                                if request_data is not None
                                else {}
                            ),
                        },
                    },
                ),
            ),
        )

    def on_file_download_phase(phase: str):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_file_download": {
                            "status": "phase",
                            "load_phase": phase,
                            "destination_hash": destination_hash.hex(),
                            "file_path": file_path,
                        },
                    },
                ),
            ),
        )

    # Route /media/ requests through the single /media handler.
    rns_path = file_path
    rns_data = request_data
    if file_path.startswith("/media/"):
        rns_path = "/media"
        media_payload = {"path": file_path}
        if isinstance(request_data, dict):
            media_payload.update(request_data)
        rns_data = media_payload

    # download the file
    downloader = NomadnetFileDownloader(
        destination_hash,
        rns_path,
        on_file_download_success,
        on_file_download_failure,
        on_file_download_progress,
        data=rns_data,
        on_phase=on_file_download_phase,
        reticulum=getattr(app, "reticulum", None),
        max_bytes=WS_NOMAD_FILE_MAX_BYTES,
        private=private,
        **nomad_link_identity_kwargs(app, destination_hash, private=private),
    )
    downloader.start_time = time.time()
    app.active_downloads[download_id] = downloader

    # notify client download started (await so phase updates cannot reorder ahead of started)
    await client.send_str(
        json.dumps(
            {
                "type": WsInboundType.NOMADNET_FILE_DOWNLOAD,
                "download_id": download_id,
                **rid,
                "nomadnet_file_download": {
                    "status": "started",
                    "destination_hash": destination_hash.hex(),
                    "file_path": file_path,
                    **({"data": request_data} if request_data is not None else {}),
                },
            },
        ),
    )

    AsyncUtils.run_async(downloader.download())

    # handle downloading a page from a nomadnet node


async def handle_nomadnet_page_download(app, client, data):
    # get data from websocket client
    page_download_data = data.get("nomadnet_page_download")
    if not page_download_data:
        return

    destination_hash = page_download_data.get("destination_hash")
    page_path = page_download_data.get("page_path")
    field_data = page_download_data.get("field_data")
    private = bool(page_download_data.get("private"))
    rid = _request_id_fields(data)

    # generate download id early so the client can always clear Loading page
    async with app.download_id_lock:
        app.download_id_counter += 1
        download_id = app.download_id_counter

    async def send_failure(reason: str, dest_hex: str = "", path: str = "") -> None:
        # Match other Nomad WS callbacks: fire-and-forget so MagicMock clients
        # in unit tests do not need to be awaitable.
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_page_download": {
                            "status": "failure",
                            "failure_reason": reason,
                            "destination_hash": dest_hex or (destination_hash or ""),
                            "page_path": path or (page_path or ""),
                            "has_archives": False,
                        },
                    },
                ),
            ),
        )

    if not destination_hash or not page_path:
        await send_failure("missing_destination_or_path")
        return

    combined_data = {}
    # parse data from page path
    # example path then backtick then field1=123|field2=456
    page_data = None
    page_path_to_download = page_path
    if "`" in page_path:
        page_path_parts = page_path.split("`")
        page_path_to_download = page_path_parts[0]
        page_data = convert_nomadnet_string_data_to_map(page_path_parts[1])

    # Field data
    field_data = convert_nomadnet_field_data_to_map(field_data)

    # Combine page data and field data
    if page_data is not None:
        combined_data.update(page_data)
    if field_data is not None:
        combined_data.update(field_data)

    # convert destination hash to bytes
    try:
        destination_hash_bytes = bytes.fromhex(destination_hash)
    except (TypeError, ValueError):
        await send_failure("invalid_destination_hash", str(destination_hash), page_path)
        return

    destination_hash = destination_hash_bytes

    local_page = app._try_serve_local_page_node(
        destination_hash,
        page_path_to_download,
        request_data=combined_data,
    )
    if local_page is not None:
        if not private:
            app.archive_page(destination_hash.hex(), page_path, local_page)
        app._register_page_file_grant(client, destination_hash, page_path, local_page)
        AsyncUtils.run_async(
            _send_nomad_page_content(
                client,
                download_id=download_id,
                destination_hash_hex=destination_hash.hex(),
                page_path=page_path,
                page_content=local_page,
                private=private,
                request_id_fields=rid,
            ),
        )
        return

    # handle successful page download
    def on_page_download_success(page_content):
        # remove from active downloads (callback thread races cancel)
        app.active_downloads.pop(download_id, None)

        # archive the page if enabled (never for private browse)
        if not private:
            app.archive_page(destination_hash.hex(), page_path, page_content)

        app._register_page_file_grant(client, destination_hash, page_path, page_content)

        AsyncUtils.run_async(
            _send_nomad_page_content(
                client,
                download_id=download_id,
                destination_hash_hex=destination_hash.hex(),
                page_path=page_path,
                page_content=page_content,
                private=private,
                request_id_fields=rid,
            ),
        )

    # handle page download failure
    def on_page_download_failure(failure_reason):
        # remove from active downloads (callback thread races cancel)
        app.active_downloads.pop(download_id, None)

        # check if there are any archived versions (not offered in private browse)
        has_archives = False
        if not private:
            has_archives = (
                len(
                    app.get_archived_page_versions(
                        destination_hash.hex(),
                        page_path,
                    ),
                )
                > 0
            )

        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_page_download": {
                            "status": "failure",
                            "failure_reason": failure_reason,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                            "has_archives": has_archives,
                        },
                    },
                ),
            ),
        )

    # handle page download progress
    def on_page_download_progress(progress):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_page_download": {
                            "status": "progress",
                            "progress": progress,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                        },
                    },
                ),
            ),
        )

    def on_page_download_phase(phase: str):
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                        "download_id": download_id,
                        **rid,
                        "nomadnet_page_download": {
                            "status": "phase",
                            "load_phase": phase,
                            "destination_hash": destination_hash.hex(),
                            "page_path": page_path,
                        },
                    },
                ),
            ),
        )

    # download the page
    downloader = NomadnetPageDownloader(
        destination_hash,
        page_path_to_download,
        combined_data,
        on_page_download_success,
        on_page_download_failure,
        on_page_download_progress,
        on_phase=on_page_download_phase,
        reticulum=getattr(app, "reticulum", None),
        private=private,
        **nomad_link_identity_kwargs(app, destination_hash, private=private),
    )
    app.active_downloads[download_id] = downloader

    # notify client download started (await so phase updates cannot reorder ahead of started)
    await client.send_str(
        json.dumps(
            {
                "type": WsInboundType.NOMADNET_PAGE_DOWNLOAD,
                "download_id": download_id,
                **rid,
                "nomadnet_page_download": {
                    "status": "started",
                    "destination_hash": destination_hash.hex(),
                    "page_path": page_path,
                },
            },
        ),
    )

    AsyncUtils.run_async(downloader.download())

    # handle lxmf forwarding rules


HANDLERS = {
    WsInboundType.NOMADNET_DOWNLOAD_CANCEL: handle_nomadnet_download_cancel,
    WsInboundType.NOMADNET_PAGE_ARCHIVES_GET: handle_nomadnet_page_archives_get,
    WsInboundType.NOMADNET_PAGE_ARCHIVE_LOAD: handle_nomadnet_page_archive_load,
    WsInboundType.NOMADNET_PAGE_ARCHIVE_FLUSH: handle_nomadnet_page_archive_flush,
    WsInboundType.NOMADNET_PAGE_ARCHIVE_ADD: handle_nomadnet_page_archive_add,
    WsInboundType.NOMADNET_FILE_DOWNLOAD: handle_nomadnet_file_download,
    WsInboundType.NOMADNET_PAGE_DOWNLOAD: handle_nomadnet_page_download,
}
