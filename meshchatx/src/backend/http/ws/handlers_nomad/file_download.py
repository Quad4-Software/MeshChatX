# SPDX-License-Identifier: 0BSD

"""WebSocket handlers: Nomad file download."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.ws.handlers_nomad._helpers import (
    _is_nomad_image_request,
    _request_id_fields,
    _send_nomad_file_bytes,
    _validate_nomad_image_bytes,
)
from meshchatx.src.backend.http.ws.handlers_nomad._names import *  # noqa: F403, F405
from meshchatx.src.backend.websocket_runtime import WS_NOMAD_FILE_MAX_BYTES


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


HANDLERS = {
    "nomadnet.file.download": handle_nomadnet_file_download,
}
