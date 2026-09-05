# SPDX-License-Identifier: 0BSD
"""HTTP routes: maintenance/ops."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.maintenance._names import *  # noqa: F403


def register_maintenance_ops_routes(routes: Any, app: Any) -> None:
    # maintenance - clear messages (all, or older than days / before date)

    @routes.delete("/api/v1/maintenance/messages")
    async def maintenance_clear_messages(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        if cutoff is None:
            app.database.messages.delete_all_lxmf_messages()
            return web.json_response(
                {"message": "All messages cleared", "deleted": None},
            )

        def _cancel(h):
            try:
                if app.message_router is not None:
                    app.message_router.cancel_outbound(h)
            except Exception:
                pass

        deleted = await asyncio.to_thread(
            purge_messages_before_cutoff,
            app.database.messages,
            _cancel,
            cutoff,
        )
        return web.json_response(
            {
                "message": f"Deleted {deleted} messages older than cutoff",
                "deleted": deleted,
                "cutoff": cutoff,
            },
        )

    @routes.get("/api/v1/maintenance/messages/duplicates")
    async def maintenance_messages_duplicates_preview(request):
        count = await asyncio.to_thread(
            app.database.messages.count_duplicate_lxmf_messages_by_content,
        )
        return web.json_response({"count": count})

    @routes.delete("/api/v1/maintenance/messages/duplicates")
    async def maintenance_messages_duplicates_clear(request):
        def _clear():
            hashes = (
                app.database.messages.list_duplicate_lxmf_message_hashes_by_content()
            )
            if not hashes:
                return 0
            if app.message_router is not None:
                for h in hashes:
                    if not h or len(h) % 2 != 0:
                        continue
                    try:
                        app.message_router.cancel_outbound(bytes.fromhex(h))
                    except Exception:
                        pass
            app.database.messages.delete_lxmf_messages_by_hashes(hashes)
            app.database.messages.prune_conversation_metadata_for_peers_with_no_messages()
            return len(hashes)

        deleted = await asyncio.to_thread(_clear)
        return web.json_response(
            {
                "message": f"Deleted {deleted} duplicate messages",
                "deleted": deleted,
            },
        )

    @routes.get("/api/v1/maintenance/messages/purge-preview")
    async def maintenance_messages_purge_preview(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        if cutoff is None:
            return web.json_response(
                {"message": "older_than_days or before is required"},
                status=400,
            )
        count = app.database.messages.count_lxmf_messages_with_timestamp_before(
            cutoff,
        )
        return web.json_response({"count": count, "cutoff": cutoff})

    @routes.delete("/api/v1/maintenance/announces")
    async def maintenance_clear_announces(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_announces(aspect=aspect)
        return web.json_response(
            {
                "message": f"Announces cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    @routes.delete("/api/v1/maintenance/favourites")
    async def maintenance_clear_favourites(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_favourites(aspect=aspect)
        return web.json_response(
            {
                "message": f"Favourites cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    @routes.delete("/api/v1/maintenance/archives")
    async def maintenance_clear_archives(request):
        app.database.misc.delete_archived_pages()
        return web.json_response({"message": "All archived pages cleared"})

    @routes.delete("/api/v1/maintenance/lxmf-icons")
    async def maintenance_clear_lxmf_icons(request):
        app.database.misc.delete_all_user_icons()
        return web.json_response({"message": "All LXMF icons cleared"})

    @routes.delete("/api/v1/maintenance/stickers")
    async def maintenance_clear_stickers(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.stickers.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "Stickers cleared", "deleted": n})

    @routes.delete("/api/v1/maintenance/gifs")
    async def maintenance_clear_gifs(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.gifs.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "GIFs cleared", "deleted": n})

    @routes.delete("/api/v1/maintenance/path-table")
    async def maintenance_clear_path_table(request):
        try:
            dropped = app.rnpath_handler.drop_all_paths()
            return web.json_response(
                {"message": "Path table cleared", "dropped": dropped},
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.post("/api/v1/maintenance/messages/export")
    async def maintenance_export_messages(request):
        try:
            body = await request.json() if request.can_read_body else {}
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=body.get(
                    "older_than_days", request.query.get("older_than_days")
                ),
                before=body.get("before", request.query.get("before")),
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        messages_list = []
        page_size = 5000
        offset = 0
        while True:
            if cutoff is None:
                page = app.database.messages.get_all_lxmf_messages(
                    limit=page_size,
                    offset=offset,
                )
            else:
                page = app.database.messages.get_lxmf_messages_with_timestamp_before(
                    cutoff,
                    limit=page_size,
                    offset=offset,
                )
            messages_list.extend(dict(m) for m in page)
            if len(page) < page_size:
                break
            offset += page_size
        bundle = await asyncio.to_thread(
            build_messages_export_bundle,
            app.database,
            messages_list,
        )
        return web.json_response(bundle)

    @routes.post("/api/v1/maintenance/messages/import")
    async def maintenance_import_messages(request):
        try:
            data = await request.json()
            if app.database is None:
                return web.json_response(
                    {"error": "No active identity database"},
                    status=400,
                )

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                data,
            )
            return _message_import_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    @routes.post("/api/v1/maintenance/messages/import-file")
    async def maintenance_import_messages_file(request):
        try:
            if app.database is None:
                return web.json_response(
                    {"error": "No active identity database"},
                    status=400,
                )

            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                return web.json_response(
                    {"error": "Import file is required"},
                    status=400,
                )

            chunks = []
            while True:
                chunk = await field.read_chunk(size=1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                return web.json_response(
                    {"error": f"Invalid JSON: {exc}"},
                    status=400,
                )

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                payload,
            )
            return _message_import_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
