# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives recrawl."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_forbidden,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.routes.archives._helpers import resolve_node_name
from meshchatx.src.backend.http.routes.archives._names import *
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_archives_recrawl_routes(routes: Any, app: Any) -> None:
    @routes.post("/api/v1/nomadnet/archives/recrawl")
    async def recrawl_archived_page(request):
        """Fetch a Nomad page now and store a fresh archive snapshot."""
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = (data.get("destination_hash") or "").strip().lower()
        page_path = (data.get("page_path") or "").strip()
        if len(destination_hash) != 32:
            return http_bad_request(
                "destination_hash must be 32 hex characters",
            )
        try:
            bytes.fromhex(destination_hash)
        except ValueError:
            return http_bad_request(
                "destination_hash must be valid hex",
            )
        if not page_path:
            page_path = (
                app.config.nomad_default_page_path.get() if app.config else None
            ) or "/page/index.mu"

        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler and crawler.is_opted_out(destination_hash):
            return http_forbidden("Node is on the crawl opt-out list")

        done_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        success = [False]
        content_received = [None]
        failure_reason = ["timeout"]

        def on_success(content):
            success[0] = True
            content_received[0] = content
            # RNS request callbacks fire on the transport thread, so the
            # asyncio.Event must be set through the owning loop.
            loop.call_soon_threadsafe(done_event.set)

        def on_failure(reason):
            failure_reason[0] = reason or "download failed"
            loop.call_soon_threadsafe(done_event.set)

        downloader = NomadnetPageDownloader(
            destination_hash=bytes.fromhex(destination_hash),
            page_path=page_path.split("`", 1)[0],
            data=None,
            on_page_download_success=on_success,
            on_page_download_failure=on_failure,
            on_progress_update=lambda _p: None,
            timeout=120,
            reticulum=getattr(app, "reticulum", None),
            **nomad_link_identity_kwargs(
                app,
                bytes.fromhex(destination_hash),
                private=False,
            ),
        )

        try:
            download_task = asyncio.create_task(downloader.download())
            try:
                await asyncio.wait_for(done_event.wait(), timeout=180)
            except TimeoutError:
                failure_reason[0] = "timeout"
                downloader.cancel()
            await download_task
        except Exception:
            return http_error(502, "Recrawl failed")

        if not success[0]:
            return http_error(502, f"Recrawl failed: {failure_reason[0]}")

        app.archive_page(
            destination_hash,
            page_path,
            content_received[0] or "",
            is_manual=True,
        )
        if crawler:
            crawler.queue_if_allowed(
                destination_hash,
                page_path,
                depth=0,
                force=True,
            )

        versions = app.database.misc.get_archived_page_versions(
            destination_hash,
            page_path,
        )
        latest = versions[0] if versions else None
        if not latest:
            return http_unexpected(
                "Page fetched but archive was not stored",
            )
        return web.json_response(
            {
                "message": "Recrawled",
                "archive": {
                    "id": latest["id"],
                    "destination_hash": latest["destination_hash"],
                    "node_name": resolve_node_name(app, latest["destination_hash"]),
                    "page_path": latest["page_path"],
                    "content": latest["content"],
                    "hash": latest["hash"],
                    "created_at": latest["created_at"],
                    "snippet": make_snippet(latest["content"], None),
                    "preview": (latest["content"] or "")[:2000],
                },
            },
        )
