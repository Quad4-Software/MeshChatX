# SPDX-License-Identifier: 0BSD
"""HTTP routes: archived Nomad pages."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.routes.archives._helpers import resolve_node_name
from meshchatx.src.backend.http.routes.archives._names import *  # noqa: F403


def register_archives_pages_routes(routes: Any, app: Any) -> None:
    @routes.get("/api/v1/nomadnet/archives")
    async def get_all_archived_pages(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        query = request.query.get("q", "").strip()
        destination_hash = request.query.get("destination_hash", "").strip() or None
        include_content_raw = request.query.get("include_content")
        if include_content_raw is None:
            include_content = False
        else:
            include_content = parse_bool_query_param(include_content_raw)
        try:
            page = max(1, int(request.query.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            limit = max(1, min(100, int(request.query.get("limit", 25))))
        except (ValueError, TypeError):
            limit = 25
        offset = (page - 1) * limit

        try:
            total_count = app.database.misc.count_archived_pages(
                destination_hash=destination_hash,
                query=query or None,
            )
            total_pages = (total_count + limit - 1) // limit if total_count else 0

            # Fetch a wider window when searching so token ranking can reorder.
            fetch_limit = limit
            fetch_offset = offset
            if query:
                fetch_limit = min(200, max(limit * 4, limit))
                fetch_offset = max(0, offset - limit)

            rows = app.database.misc.get_archived_pages_paginated(
                destination_hash=destination_hash,
                query=query or None,
                limit=fetch_limit,
                offset=fetch_offset,
                include_content=True if query else include_content,
            )

            crawler = (
                getattr(app.current_context, "crawler_manager", None)
                if app.current_context
                else None
            )
            if query and crawler:
                rows = crawler.rank_archives_by_query(rows, query)
                # Re-slice to the requested page after ranking.
                start = offset - fetch_offset
                rows = rows[start : start + limit]
            elif query and not include_content:
                # Rank helper needed content. Drop bodies for the list payload.
                pass

            archives = []
            for archive in rows:
                content = archive.get("content")
                preview = archive.get("content_preview")
                if content is None and preview is not None:
                    content = preview
                raw_preview = (content or "")[:2000]
                snippet = make_snippet(content, query or None)
                entry = {
                    "id": archive["id"],
                    "destination_hash": archive["destination_hash"],
                    "node_name": resolve_node_name(app, archive["destination_hash"]),
                    "page_path": archive["page_path"],
                    "hash": archive["hash"],
                    "created_at": archive["created_at"],
                    "snippet": snippet,
                    "preview": raw_preview,
                }
                if include_content:
                    entry["content"] = archive.get("content") or ""
                archives.append(entry)

            return web.json_response(
                {
                    "archives": archives,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total_count": total_count,
                        "total_pages": total_pages,
                    },
                },
            )
        except Exception as exc:
            return http_for_database_exception(exc, unexpected_message="Failed to load archives")

    @routes.get("/api/v1/nomadnet/archives/{archive_id}")
    async def get_archived_page(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            archive_id = int(request.match_info["archive_id"])
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid archive id"}, status=400)
        try:
            archive = app.database.misc.get_archived_page_by_id(archive_id)
            if not archive:
                return web.json_response({"message": "Archive not found"}, status=404)
            return web.json_response(
                {
                    "archive": {
                        "id": archive["id"],
                        "destination_hash": archive["destination_hash"],
                        "node_name": resolve_node_name(app, archive["destination_hash"]),
                        "page_path": archive["page_path"],
                        "content": archive["content"],
                        "hash": archive["hash"],
                        "created_at": archive["created_at"],
                        "snippet": make_snippet(archive["content"], None),
                    },
                },
            )
        except Exception as exc:
            return http_for_database_exception(exc, unexpected_message="Failed to load archive")

    @routes.delete("/api/v1/nomadnet/archives")
    async def delete_archived_pages(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        data = await request.json()
        ids = data.get("ids", [])

        if not ids:
            return web.json_response(
                {
                    "message": "No archive IDs provided!",
                },
                status=400,
            )

        try:
            app.database.misc.delete_archived_pages(ids=ids)
        except Exception as exc:
            return http_for_database_exception(exc, unexpected_message="Failed to delete archives")

        return web.json_response(
            {
                "message": f"Deleted {len(ids)} archives!",
            },
        )
