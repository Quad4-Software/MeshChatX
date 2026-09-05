# SPDX-License-Identifier: 0BSD

"""WebSocket handlers: Nomad page archives."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.ws.handlers_nomad._names import *  # noqa: F403, F405


async def handle_nomadnet_page_archives_get(app, client, data):
    destination_hash = data.get("destination_hash")
    page_path = data.get("page_path")

    if not destination_hash or not page_path:
        return

    # Try relative path first
    archives = app.get_archived_page_versions(destination_hash, page_path)

    # If nothing found and path does not look like it is already absolute,
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


async def handle_nomadnet_page_archive_load(app, client, data):
    archive_id = data.get("archive_id")
    download_id = data.get("download_id")
    if archive_id is None:
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "nomadnet.page.download",
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
                        "type": "nomadnet.page.download",
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
                    "type": "nomadnet.page.download",
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


async def handle_nomadnet_page_archive_flush(app, client, data):
    app.flush_all_archived_pages()
    # notify config updated
    AsyncUtils.run_async(app.send_config_to_websocket_clients())


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


HANDLERS = {
    "nomadnet.page.archives.get": handle_nomadnet_page_archives_get,
    "nomadnet.page.archive.load": handle_nomadnet_page_archive_load,
    "nomadnet.page.archive.flush": handle_nomadnet_page_archive_flush,
    "nomadnet.page.archive.add": handle_nomadnet_page_archive_add,
}
