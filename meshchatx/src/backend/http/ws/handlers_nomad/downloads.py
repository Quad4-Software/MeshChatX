# SPDX-License-Identifier: 0BSD

"""WebSocket handlers: Nomad download cancellation."""

from __future__ import annotations

# ruff: noqa: F405
from meshchatx.src.backend.http.ws.handlers_nomad._helpers import _request_id_fields
from meshchatx.src.backend.http.ws.handlers_nomad._names import *  # noqa: F403


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


HANDLERS = {
    "nomadnet.download.cancel": handle_nomadnet_download_cancel,
}
