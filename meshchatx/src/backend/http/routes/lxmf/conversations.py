# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf conversations."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.lxmf._names import *  # noqa: F403, F405


def register_lxmf_conversations_routes(routes, app):

    @routes.get("/api/v1/lxmf/conversation-pins")
    async def lxmf_conversation_pins_get(request):
        peer_hashes = app.database.messages.get_pinned_peer_hashes()
        return web.json_response({"peer_hashes": peer_hashes})

    @routes.post("/api/v1/lxmf/conversation-pins/toggle")
    async def lxmf_conversation_pins_toggle(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"message": "invalid json"}, status=400)
        destination_hash = (
            data.get("destination_hash") if isinstance(data, dict) else None
        )
        if not destination_hash:
            return web.json_response(
                {"message": "missing destination_hash"},
                status=400,
            )
        pinned = app.database.messages.toggle_peer_pin(destination_hash)
        return web.json_response(
            {
                "peer_hashes": app.database.messages.get_pinned_peer_hashes(),
                "pinned": pinned,
            },
        )

    # get lxmf conversations

    # get lxmf conversations
    @routes.get("/api/v1/lxmf/conversations")
    async def lxmf_conversations_get(request):
        not_ready = app._require_identity_context_ready()
        if not_ready is not None:
            return not_ready

        # get query params
        search_query = request.query.get("search", request.query.get("q", None))
        filter_unread = parse_bool_query_param(
            request.query.get(
                "unread",
                request.query.get("filter_unread", "false"),
            ),
        )
        filter_failed = parse_bool_query_param(
            request.query.get(
                "failed",
                request.query.get("filter_failed", "false"),
            ),
        )
        filter_has_attachments = parse_bool_query_param(
            request.query.get(
                "has_attachments",
                request.query.get("filter_has_attachments", "false"),
            ),
        )
        folder_id = request.query.get("folder_id")
        if folder_id is not None:
            try:
                folder_id = int(folder_id)
            except ValueError:
                folder_id = None

        # get pagination params
        try:
            limit = request.query.get("limit")
            limit = int(limit) if limit is not None else None
        except ValueError:
            limit = None
        limit = app.message_handler.clamp_conversations_limit(limit)

        try:
            offset = request.query.get("offset")
            offset = int(offset) if offset is not None else 0
        except ValueError:
            offset = 0

        try:
            local_hash = app.local_lxmf_destination.hexhash

            db_conversations = await asyncio.to_thread(
                app.message_handler.get_conversations,
                local_hash,
                search=search_query,
                filter_unread=filter_unread,
                filter_failed=filter_failed,
                filter_has_attachments=filter_has_attachments,
                folder_id=folder_id,
                limit=limit,
                offset=offset,
            )

            row_dicts = []
            peer_hashes = []
            for row in db_conversations:
                if not isinstance(row, dict):
                    row = dict(row)
                other_user_hash = row["peer_hash"]
                if app._lxmf_sieve_hides_peer(
                    other_user_hash,
                    message_title=row.get("title"),
                    message_content=row.get("content"),
                ):
                    continue
                row_dicts.append(row)
                peer_hashes.append(other_user_hash)

            tracking_states = await asyncio.to_thread(
                app.database.telemetry.get_tracking_states,
                peer_hashes,
            )
            viewed_map = {}
            if filter_unread:
                viewed_map = await asyncio.to_thread(
                    app.database.messages.get_notification_last_viewed_at_map,
                    peer_hashes,
                )

            conversations = []
            for row in row_dicts:
                other_user_hash = row["peer_hash"]

                display_name = None
                if row.get("peer_app_data"):
                    display_name = parse_lxmf_display_name(
                        app_data_base64=row["peer_app_data"],
                        default_value=None,
                    )
                if not display_name and row.get("contact_name"):
                    display_name = row["contact_name"]
                if not display_name:
                    display_name = "Anonymous Peer"

                # user icon
                user_icon = None
                if row.get("icon_name"):
                    user_icon = {
                        "icon_name": row["icon_name"],
                        "foreground_colour": row["foreground_colour"],
                        "background_colour": row["background_colour"],
                    }

                # contact image blob stays out of the list payload
                has_contact_image = bool(row.get("has_contact_image", 0))

                try:
                    is_unread = compute_lxmf_conversation_unread_from_latest_row(
                        row,
                    )
                except Exception:
                    is_unread = False

                # Add extra check for notification viewed state if unread
                if is_unread and filter_unread:
                    if app.database.messages.notification_viewed_covers(
                        viewed_map.get(other_user_hash),
                        row["timestamp"],
                    ):
                        is_unread = False
                        if filter_unread:
                            continue  # Skip this conversation if filtering unread and it's actually viewed

                has_attachments = bool(
                    row.get("has_attachments") in (1, True, "1")
                    or message_fields_have_attachments(row.get("fields")),
                )

                # add to conversations
                conversations.append(
                    {
                        "display_name": display_name,
                        "custom_display_name": row["custom_display_name"],
                        "contact_image": None,
                        "has_contact_image": has_contact_image,
                        "destination_hash": other_user_hash,
                        "is_unread": is_unread,
                        "is_tracking": tracking_states.get(other_user_hash, False),
                        "failed_messages_count": row["failed_count"],
                        "has_attachments": has_attachments,
                        "latest_message_title": row["title"],
                        "latest_message_preview": lxmf_sidebar_preview_for_conversation_latest_row(
                            row,
                            local_hash=local_hash,
                            peer_display_name=(
                                row.get("custom_display_name")
                                or display_name
                                or "Anonymous Peer"
                            ),
                        ),
                        "latest_message_created_at": row["created_at"],
                        "lxmf_user_icon": user_icon,
                        "is_contact": bool(row.get("is_contact", 0)),
                        "updated_at": row["created_at"],
                    },
                )

            return web.json_response(
                {
                    "conversations": conversations,
                },
            )
        except Exception as e:
            RNS.log(f"Error in lxmf_conversations_get: {e}", RNS.LOG_ERROR)
            status = 503 if sqlite_error_is_retryable(e) else 500
            return web.json_response(
                {
                    "message": (
                        "Database temporarily unavailable. Retry shortly."
                        if status == 503
                        else "Failed to load conversations"
                    ),
                },
                status=status,
            )

    @routes.post("/api/v1/lxmf/conversations/move-to-folder")
    async def lxmf_conversations_move_to_folder(request):
        data = await request.json()
        peer_hashes = data.get("peer_hashes", [])
        folder_id = data.get("folder_id")  # Can be None to remove from folder
        if not peer_hashes:
            return web.json_response(
                {"message": "peer_hashes is required"},
                status=400,
            )
        app.database.messages.move_conversations_to_folder(peer_hashes, folder_id)
        return web.json_response({"message": "Conversations moved"})

    @routes.post("/api/v1/lxmf/conversations/bulk-mark-as-read")
    async def lxmf_conversations_bulk_mark_read(request):
        data = await request.json()
        mark_all = bool(data.get("mark_all"))
        destination_hashes = data.get("destination_hashes", [])
        if mark_all:
            app.database.messages.mark_all_conversations_as_read()
            app.database.messages.mark_all_notifications_as_viewed()
            return web.json_response(
                {"message": "All conversations marked as read"},
            )
        if not destination_hashes:
            return web.json_response(
                {"message": "destination_hashes is required"},
                status=400,
            )
        app.database.messages.mark_conversations_as_read(destination_hashes)
        # Keep notification viewed state in sync so the bell never
        # disagrees with the conversation list.
        app.database.messages.mark_all_notifications_as_viewed(destination_hashes)
        return web.json_response({"message": "Conversations marked as read"})

    @routes.post("/api/v1/lxmf/conversations/bulk-delete")
    async def lxmf_conversations_bulk_delete(request):
        data = await request.json()
        destination_hashes = data.get("destination_hashes", [])
        if not destination_hashes:
            return web.json_response(
                {"message": "destination_hashes is required"},
                status=400,
            )
        local_hash = app.local_lxmf_destination.hexhash
        for dest_hash in destination_hashes:
            for message_hash in app.database.messages.list_message_hashes_for_peer(
                dest_hash,
            ):
                try:
                    app.message_router.cancel_outbound(bytes.fromhex(message_hash))
                except Exception:
                    pass
            app.message_handler.delete_conversation(local_hash, dest_hash)
        return web.json_response({"message": "Conversations deleted"})

    # mark lxmf conversation as read
    @routes.post("/api/v1/lxmf/conversations/{destination_hash}/mark-as-read")
    async def lxmf_conversations_mark_read(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # mark lxmf conversation as read
        app.database.messages.mark_conversation_as_read(destination_hash)
        # Keep notification viewed state in sync so the bell never
        # disagrees with the conversation list.
        app.database.messages.mark_notification_as_viewed(destination_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # mark notifications as viewed
