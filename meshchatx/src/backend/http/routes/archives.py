# SPDX-License-Identifier: 0BSD
"""HTTP routes: archives."""

from __future__ import annotations

import asyncio
import io
import json
import re
import secrets
import zipfile
from datetime import UTC, datetime

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.crawler_manager import make_snippet
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.meshchat_utils import (
    parse_bool_query_param,
    parse_nomadnetwork_node_display_name,
)
from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetPageDownloader,
    nomad_link_identity_kwargs,
)


def _resolve_node_name(app, destination_hash: str) -> str:
    node_name = app.get_custom_destination_display_name(destination_hash)
    if not node_name:
        db_announce = app.database.announces.get_announce_by_hash(destination_hash)
        if db_announce and db_announce["aspect"] == "nomadnetwork.node":
            node_name = parse_nomadnetwork_node_display_name(db_announce["app_data"])
    return node_name or "Unknown Node"


def register_archives_routes(routes, app):
    @routes.get(API_V1_PREFIX + "/nomadnet/archives")
    async def get_all_archived_pages(request):
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
                "node_name": _resolve_node_name(app, archive["destination_hash"]),
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

    @routes.get(API_V1_PREFIX + "/nomadnet/archives/export")
    async def export_archived_pages(request):
        """Download the filtered archive set as a single zip bundle."""
        query = request.query.get("q", "").strip()
        destination_hash = request.query.get("destination_hash", "").strip() or None
        rows = app.database.misc.get_archived_pages_paginated(
            destination_hash=destination_hash,
            query=query or None,
            limit=None,
            include_content=True,
        )

        def _safe_segment(value: str) -> str:
            cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", value or "").strip()
            cleaned = cleaned.strip(". ")
            return cleaned[:80] or "_"

        def _arcname(row) -> str:
            dest_dir = (row["destination_hash"] or "unknown")[:8]
            raw_path = (row["page_path"] or "/").split("`", 1)[0].strip("/")
            parts = [_safe_segment(p) for p in raw_path.split("/") if p.strip()]
            rel = "/".join(parts) if parts else "index"
            return f"{dest_dir}/{rel}"

        buf = io.BytesIO()
        used_names = set()
        manifest = []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for row in rows:
                name = _arcname(row)
                stem, dot, ext = name.rpartition(".")
                if not dot or "/" in ext:
                    stem, ext = name, ""
                if name in used_names:
                    short = (row.get("hash") or "snap")[:8]
                    name = f"{stem}__{short}{'.' + ext if ext else ''}"
                while name in used_names:
                    name = f"{stem}__{secrets.token_hex(4)}{'.' + ext if ext else ''}"
                used_names.add(name)
                zf.writestr(name, row.get("content") or "")
                manifest.append(
                    {
                        "id": row["id"],
                        "file": name,
                        "destination_hash": row["destination_hash"],
                        "node_name": _resolve_node_name(app, row["destination_hash"]),
                        "page_path": row["page_path"],
                        "hash": row["hash"],
                        "created_at": row["created_at"],
                    }
                )
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format": "meshchatx-archives",
                        "version": 1,
                        "exported_at": datetime.now(UTC).isoformat(),
                        "archives": manifest,
                    },
                    indent=2,
                ),
            )

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return web.Response(
            body=buf.getvalue(),
            content_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="meshchatx-archives-{stamp}.zip"',
            },
        )

    @routes.get(API_V1_PREFIX + "/nomadnet/archives/{archive_id}")
    async def get_archived_page(request):
        try:
            archive_id = int(request.match_info["archive_id"])
        except (TypeError, ValueError):
            return http_bad_request("Invalid archive id")
        archive = app.database.misc.get_archived_page_by_id(archive_id)
        if not archive:
            return http_not_found("Archive not found")
        return web.json_response(
            {
                "archive": {
                    "id": archive["id"],
                    "destination_hash": archive["destination_hash"],
                    "node_name": _resolve_node_name(app, archive["destination_hash"]),
                    "page_path": archive["page_path"],
                    "content": archive["content"],
                    "hash": archive["hash"],
                    "created_at": archive["created_at"],
                    "snippet": make_snippet(archive["content"], None),
                },
            },
        )

    @routes.delete(API_V1_PREFIX + "/nomadnet/archives")
    async def delete_archived_pages(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        ids = data.get("ids", [])

        if not ids:
            return http_bad_request("No archive IDs provided!")

        app.database.misc.delete_archived_pages(ids=ids)

        return web.json_response(
            {
                "message": f"Deleted {len(ids)} archives!",
            },
        )

    @routes.get(API_V1_PREFIX + "/nomadnet/crawl/opt-outs")
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
                        "node_name": _resolve_node_name(app, row["destination_hash"]),
                    }
                    for row in rows
                ],
            },
        )

    @routes.post(API_V1_PREFIX + "/nomadnet/crawl/opt-outs")
    async def add_crawl_opt_out(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = (data.get("destination_hash") or "").strip().lower()
        if len(destination_hash) != 32:
            return http_bad_request(
                "destination_hash must be 32 hex characters",
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

    @routes.delete(API_V1_PREFIX + "/nomadnet/crawl/opt-outs/{destination_hash}")
    async def remove_crawl_opt_out(request):
        destination_hash = (
            (request.match_info.get("destination_hash") or "").strip().lower()
        )
        if len(destination_hash) != 32:
            return http_bad_request(
                "destination_hash must be 32 hex characters",
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

    @routes.post(API_V1_PREFIX + "/nomadnet/archives/recrawl")
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
        success = [False]
        content_received = [None]
        failure_reason = ["timeout"]

        def on_success(content):
            success[0] = True
            content_received[0] = content
            done_event.set()

        def on_failure(reason):
            failure_reason[0] = reason or "download failed"
            done_event.set()

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
                    "node_name": _resolve_node_name(app, latest["destination_hash"]),
                    "page_path": latest["page_path"],
                    "content": latest["content"],
                    "hash": latest["hash"],
                    "created_at": latest["created_at"],
                    "snippet": make_snippet(latest["content"], None),
                    "preview": (latest["content"] or "")[:2000],
                },
            },
        )
