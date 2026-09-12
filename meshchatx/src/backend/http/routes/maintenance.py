# SPDX-License-Identifier: 0BSD
"""HTTP routes: maintenance."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_field_limited,
    read_json_limited,
)
from meshchatx.src.backend.local_message_retention import (
    purge_messages_before_cutoff,
    resolve_message_age_cutoff,
)
from meshchatx.src.backend.message_export_bundle import (
    build_messages_export_bundle,
    import_messages_export_bundle,
)


def register_maintenance_routes(routes, app):
    # maintenance - clear messages (all, or older than days / before date)
    @routes.delete(API_V1_PREFIX + "/maintenance/messages")
    async def maintenance_clear_messages(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return http_bad_request(str(e))
        if cutoff is None:
            await asyncio.to_thread(
                app.database.messages.delete_all_lxmf_messages,
            )
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

    @routes.get(API_V1_PREFIX + "/maintenance/messages/duplicates")
    async def maintenance_messages_duplicates_preview(request):
        count = await asyncio.to_thread(
            app.database.messages.count_duplicate_lxmf_messages_by_content,
        )
        return web.json_response({"count": count})

    @routes.delete(API_V1_PREFIX + "/maintenance/messages/duplicates")
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

    @routes.get(API_V1_PREFIX + "/maintenance/messages/purge-preview")
    async def maintenance_messages_purge_preview(request):
        try:
            cutoff = resolve_message_age_cutoff(
                older_than_days=request.query.get("older_than_days"),
                before=request.query.get("before"),
            )
        except ValueError as e:
            return http_bad_request(str(e))
        if cutoff is None:
            return http_bad_request("older_than_days or before is required")
        count = app.database.messages.count_lxmf_messages_with_timestamp_before(
            cutoff,
        )
        return web.json_response({"count": count, "cutoff": cutoff})

    # maintenance - clear announces

    # maintenance - clear announces
    @routes.delete(API_V1_PREFIX + "/maintenance/announces")
    async def maintenance_clear_announces(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_announces(aspect=aspect)
        return web.json_response(
            {
                "message": f"Announces cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    # maintenance - clear favorites

    # maintenance - clear favorites
    @routes.delete(API_V1_PREFIX + "/maintenance/favourites")
    async def maintenance_clear_favourites(request):
        aspect = request.query.get("aspect")
        app.database.announces.delete_all_favourites(aspect=aspect)
        return web.json_response(
            {
                "message": f"Favourites cleared{' for aspect ' + aspect if aspect else ''}",
            },
        )

    # maintenance - clear archives

    # maintenance - clear archives
    @routes.delete(API_V1_PREFIX + "/maintenance/archives")
    async def maintenance_clear_archives(request):
        app.database.misc.delete_archived_pages()
        return web.json_response({"message": "All archived pages cleared"})

    # maintenance - clear LXMF icons

    # maintenance - clear LXMF icons
    @routes.delete(API_V1_PREFIX + "/maintenance/lxmf-icons")
    async def maintenance_clear_lxmf_icons(request):
        app.database.misc.delete_all_user_icons()
        return web.json_response({"message": "All LXMF icons cleared"})

    @routes.delete(API_V1_PREFIX + "/maintenance/stickers")
    async def maintenance_clear_stickers(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.stickers.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "Stickers cleared", "deleted": n})

    @routes.delete(API_V1_PREFIX + "/maintenance/gifs")
    async def maintenance_clear_gifs(request):
        identity_hash = app.identity.hash.hex()
        n = app.database.gifs.delete_all_for_identity(identity_hash)
        return web.json_response({"message": "GIFs cleared", "deleted": n})

    @routes.delete(API_V1_PREFIX + "/maintenance/path-table")
    async def maintenance_clear_path_table(request):
        try:
            dropped = app.rnpath_handler.drop_all_paths()
            return web.json_response(
                {"message": "Path table cleared", "dropped": dropped},
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    # maintenance - export messages (optional age filter for archive-before-purge)

    # maintenance - export messages (optional age filter for archive-before-purge)
    @routes.post(API_V1_PREFIX + "/maintenance/messages/export")
    async def maintenance_export_messages(request):
        try:
            body = await read_json_limited(request) if request.can_read_body else {}
        except PayloadTooLargeError:
            return http_payload_too_large()
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
            return http_bad_request(str(e))

        def _collect_and_build():
            # Paged SQLite reads must not run on the event loop: a large
            # inbox would stall every other request while pages are fetched.
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
                    page = (
                        app.database.messages.get_lxmf_messages_with_timestamp_before(
                            cutoff,
                            limit=page_size,
                            offset=offset,
                        )
                    )
                messages_list.extend(dict(m) for m in page)
                if len(page) < page_size:
                    break
                offset += page_size
            return build_messages_export_bundle(app.database, messages_list)

        bundle = await asyncio.to_thread(_collect_and_build)
        return web.json_response(bundle)

    def _message_import_response(result):
        if not result.get("ok", True) and result.get("error"):
            return http_bad_request(
                result["error"],
                imported=result.get("imported", 0),
                skipped=result.get("skipped", 0),
            )
        imported = result["imported"]
        skipped = result["skipped"]
        errors = result.get("errors") or []
        if imported == 0 and errors:
            return http_bad_request(
                errors[0]["error"], imported=imported, skipped=skipped, errors=errors
            )
        response = {
            "message": f"Successfully imported {imported} messages",
            "imported": imported,
            "skipped": skipped,
            "contacts_added": result.get("contacts_added", 0),
            "contacts_skipped": result.get("contacts_skipped", 0),
            "display_names_imported": result.get("display_names_imported", 0),
            "read_state_imported": result.get("read_state_imported", 0),
        }
        if errors:
            response["errors"] = errors
        return web.json_response(response)

    # maintenance - import messages

    # maintenance - import messages
    @routes.post(API_V1_PREFIX + "/maintenance/messages/import")
    async def maintenance_import_messages(request):
        try:
            data = await read_json_limited(request, UPLOAD_LIMITS["message_import"])
            if app.database is None:
                return http_bad_request("No active identity database")

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                data,
            )
            return _message_import_response(result)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e)

    @routes.post(API_V1_PREFIX + "/maintenance/messages/import-file")
    async def maintenance_import_messages_file(request):
        try:
            if app.database is None:
                return http_bad_request("No active identity database")

            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                return http_bad_request("Import file is required")

            raw = await read_field_limited(
                field,
                UPLOAD_LIMITS["message_import"],
                chunk_size=1024 * 1024,
            )

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                return http_bad_request(f"Invalid JSON: {exc}")

            result = await asyncio.to_thread(
                import_messages_export_bundle,
                app.database,
                payload,
            )
            return _message_import_response(result)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_error_from_exception(e)

    # get config
