# SPDX-License-Identifier: 0BSD
"""HTTP routes: crawl opt-outs."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.archives._helpers import resolve_node_name
from meshchatx.src.backend.http.routes.archives._names import *  # noqa: F403


def register_archives_opt_outs_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/nomadnet/crawl/opt-outs")
    async def list_crawl_opt_outs(_request):
        rows = app.database.misc.list_crawl_opt_outs()
        return web.json_response(
            {
                "opt_outs": [
                    {
                        "destination_hash": row["destination_hash"],
                        "reason": row["reason"],
                        "source": row["source"],
                        "created_at": row["created_at"],
                        "node_name": resolve_node_name(app, row["destination_hash"]),
                    }
                    for row in rows
                ],
            },
        )

    @routes.post("/api/v1/nomadnet/crawl/opt-outs")
    async def add_crawl_opt_out(request):
        data = await request.json()
        destination_hash = (data.get("destination_hash") or "").strip().lower()
        if len(destination_hash) != 32:
            return web.json_response(
                {"message": "destination_hash must be 32 hex characters"},
                status=400,
            )
        reason = (data.get("reason") or "user").strip()[:200] or "user"
        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler:
            crawler.record_opt_out(destination_hash, reason=reason, source="user")
        else:
            app.database.misc.upsert_crawl_opt_out(
                destination_hash,
                reason=reason,
                source="user",
            )
            app.database.misc.cancel_crawl_tasks_for_destination(destination_hash)
        return web.json_response(
            {"message": "opt-out recorded", "destination_hash": destination_hash},
        )

    @routes.delete("/api/v1/nomadnet/crawl/opt-outs/{destination_hash}")
    async def remove_crawl_opt_out(request):
        destination_hash = (
            (request.match_info.get("destination_hash") or "").strip().lower()
        )
        if len(destination_hash) != 32:
            return web.json_response(
                {"message": "destination_hash must be 32 hex characters"},
                status=400,
            )
        crawler = (
            getattr(app.current_context, "crawler_manager", None)
            if app.current_context
            else None
        )
        if crawler:
            crawler.remove_opt_out(destination_hash)
        else:
            app.database.misc.delete_crawl_opt_out(destination_hash)
        return web.json_response(
            {"message": "opt-out removed", "destination_hash": destination_hash},
        )
