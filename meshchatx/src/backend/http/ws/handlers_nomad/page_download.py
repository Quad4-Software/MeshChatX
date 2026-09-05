# SPDX-License-Identifier: 0BSD

"""WebSocket handlers: Nomad page download."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.ws.handlers_nomad._helpers import (
    _request_id_fields,
    _send_nomad_page_content,
)
from meshchatx.src.backend.http.ws.handlers_nomad._names import *  # noqa: F403, F405


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
    app.download_id_counter += 1
    download_id = app.download_id_counter

    async def send_failure(reason: str, dest_hex: str = "", path: str = "") -> None:
        # Match other Nomad WS callbacks: fire and forget so MagicMock clients
        # in unit tests do not need to be awaitable.
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
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
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

        # archive the page if enabled (never for private browse)
        if not private:
            app.archive_page(destination_hash.hex(), page_path, page_content)

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
        # remove from active downloads
        if download_id in app.active_downloads:
            del app.active_downloads[download_id]

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
                        "type": "nomadnet.page.download",
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
                        "type": "nomadnet.page.download",
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
                        "type": "nomadnet.page.download",
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
                "type": "nomadnet.page.download",
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


HANDLERS = {
    "nomadnet.page.download": handle_nomadnet_page_download,
}
