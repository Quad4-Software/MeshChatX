# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf messages."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.lxmf._names import *  # noqa: F403, F405


def register_lxmf_messages_routes(routes, app):

    # send lxmf message
    @routes.post("/api/v1/lxmf-messages/send")
    async def lxmf_messages_send(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        # get request body as json
        data = await request.json()

        if not isinstance(data, dict) or "lxmf_message" not in data:
            return web.json_response(
                {"message": "lxmf_message is required"},
                status=400,
            )
        lm = data["lxmf_message"]
        if not isinstance(lm, dict):
            return web.json_response(
                {"message": "lxmf_message must be an object"},
                status=400,
            )

        # get delivery method
        delivery_method = None
        if "delivery_method" in data:
            delivery_method = data["delivery_method"]

        try:
            destination_hash = lm["destination_hash"]
            content = lm["content"]
        except (KeyError, TypeError):
            return web.json_response(
                {"message": "destination_hash and content are required"},
                status=400,
            )

        raw_fields = lm.get("fields")
        fields = dict(raw_fields) if isinstance(raw_fields, dict) else {}
        app_extensions_payload = fields.pop("app_extensions", None)
        validated_app_extensions = (
            app_extensions_payload if isinstance(app_extensions_payload, dict) else None
        )

        image_field = None
        audio_field = None
        file_attachments_field = None
        telemetry_data = None
        commands = None

        try:
            if "image" in fields and isinstance(fields.get("image"), dict):
                image_bytes = base64.b64decode(fields["image"]["image_bytes"])
                detected = detect_image_format_from_magic(image_bytes)
                if detected is None or detected in {"webm", "tgs"}:
                    return web.json_response(
                        {"message": "Invalid image attachment"},
                        status=400,
                    )
                image_type = "jpg" if detected == "jpeg" else detected
                image_field = LxmfImageField(image_type, image_bytes)

            if "audio" in fields and isinstance(fields.get("audio"), dict):
                audio_mode = fields["audio"]["audio_mode"]
                audio_bytes = base64.b64decode(fields["audio"]["audio_bytes"])
                audio_field = LxmfAudioField(audio_mode, audio_bytes)

            if "file_attachments" in fields and isinstance(
                fields.get("file_attachments"),
                list,
            ):
                file_attachments = []
                for file_attachment in fields["file_attachments"]:
                    if not isinstance(file_attachment, dict):
                        continue
                    file_name = file_attachment["file_name"]
                    file_bytes = base64.b64decode(file_attachment["file_bytes"])
                    file_attachments.append(
                        LxmfFileAttachment(file_name, file_bytes),
                    )

                file_attachments_field = LxmfFileAttachmentsField(file_attachments)

            if "telemetry" in fields:
                telemetry_val = fields["telemetry"]
                if isinstance(telemetry_val, dict):
                    telemetry_data = Telemeter.pack(location=telemetry_val)
                elif isinstance(telemetry_val, str):
                    telemetry_data = base64.b64decode(telemetry_val)

            if "commands" in fields and isinstance(fields.get("commands"), list):
                commands = []
                for cmd in fields["commands"]:
                    new_cmd = {}
                    if not isinstance(cmd, dict):
                        continue
                    for k, v in cmd.items():
                        try:
                            if k.startswith("0x"):
                                new_cmd[int(k, 16)] = v
                            else:
                                new_cmd[int(k)] = v
                        except (ValueError, TypeError):
                            new_cmd[k] = v
                    commands.append(new_cmd)
        except (KeyError, TypeError, ValueError, binascii.Error):
            return web.json_response(
                {"message": "Invalid lxmf_message.fields"},
                status=400,
            )

        reply_to_hash = None
        if "reply_to_hash" in lm:
            reply_to_hash = lm["reply_to_hash"]
        reply_quoted_content = lm.get("reply_quoted_content") or None

        try:
            # send lxmf message to destination
            lxmf_message = await app.send_message(
                destination_hash=destination_hash,
                content=content,
                image_field=image_field,
                audio_field=audio_field,
                file_attachments_field=file_attachments_field,
                telemetry_data=telemetry_data,
                commands=commands,
                delivery_method=delivery_method,
                reply_to_hash=reply_to_hash,
                reply_quoted_content=reply_quoted_content,
                app_extensions=validated_app_extensions,
            )

            is_local_self = app._is_self_lxmf_destination(destination_hash)
            return web.json_response(
                {
                    "lxmf_message": convert_lxmf_message_to_dict(
                        lxmf_message,
                        include_attachments=False,
                        reticulum=app.reticulum,
                        message_router=app.current_context.message_router
                        if app.current_context
                        else None,
                        state_override="delivered" if is_local_self else None,
                        method_override="local" if is_local_self else None,
                    ),
                },
            )

        except Exception as e:
            detail = str(e).strip() or "Sending failed"
            status = 503
            if isinstance(e, (ValueError, LookupError)):
                status = 400
            elif isinstance(e, TimeoutError):
                status = 503
            body: dict[str, object] = {"message": detail}
            lower = detail.lower()
            failure_hint = None
            if "could not recall" in lower:
                failure_hint = "recall"
            elif "preferred propagation node configured" in lower:
                failure_hint = "no_propagation_node"
            elif "path to preferred propagation" in lower:
                failure_hint = "no_path_propagation_node"
            elif "no path" in lower:
                failure_hint = "no_path"
            elif "invalid destination" in lower:
                failure_hint = "invalid"
            elif status == 503:
                failure_hint = "router_error"
            ctx = app.current_context
            helptips_on = (
                ctx is not None
                and ctx.config is not None
                and ctx.config.delivery_helptips_enabled.get()
            )
            if helptips_on and destination_hash and status in (400, 503):
                from meshchatx.src.backend.delivery_diagnostics import (
                    build_delivery_diagnostics,
                )

                body["diagnostics"] = build_delivery_diagnostics(
                    app,
                    destination_hash,
                    failure_hint=failure_hint,
                )
            return web.json_response(body, status=status)

    @routes.post("/api/v1/lxmf-messages/reactions")
    async def lxmf_messages_reactions(request):
        data = await request.json()
        destination_hash = data.get("destination_hash")
        target_message_hash = data.get("target_message_hash")
        emoji = data.get("emoji", "")
        if not destination_hash or not target_message_hash or not emoji:
            return web.json_response(
                {
                    "message": "destination_hash, target_message_hash, and emoji are required",
                },
                status=422,
            )
        try:
            lxmf_message = await app.send_reaction(
                destination_hash=destination_hash,
                target_message_hash=target_message_hash,
                emoji=emoji,
            )
            return web.json_response(
                {
                    "lxmf_message": convert_lxmf_message_to_dict(
                        lxmf_message,
                        include_attachments=False,
                        reticulum=app.reticulum,
                        message_router=app.current_context.message_router
                        if app.current_context
                        else None,
                    ),
                },
            )
        except Exception as e:
            detail = str(e).strip() or "Reaction failed"
            status = 503
            if isinstance(e, (ValueError, LookupError)):
                status = 400
            elif isinstance(e, TimeoutError):
                status = 503
            return web.json_response(
                {
                    "message": detail,
                },
                status=status,
            )

    # cancel sending lxmf message

    # cancel sending lxmf message
    @routes.post("/api/v1/lxmf-messages/{hash}/cancel")
    async def lxmf_messages_cancel(request):
        # get path params
        message_hash = request.match_info.get("hash", None)

        # convert hash to bytes
        hash_as_bytes = bytes.fromhex(message_hash)

        # cancel outbound message by lxmf message hash
        app.message_router.cancel_outbound(hash_as_bytes)

        # get lxmf message from database
        lxmf_message = None
        db_lxmf_message = app.database.messages.get_lxmf_message_by_hash(
            message_hash,
        )
        if db_lxmf_message is not None:
            lxmf_message = convert_db_lxmf_message_to_dict(db_lxmf_message)

        return web.json_response(
            {
                "message": "ok",
                "lxmf_message": lxmf_message,
            },
        )

    # identify self on existing nomadnetwork link

    # delete lxmf message
    @routes.delete("/api/v1/lxmf-messages/{hash}")
    async def lxmf_messages_delete(request):
        # get path params
        message_hash = request.match_info.get("hash", None)

        # hash is required
        if message_hash is None:
            return web.json_response(
                {
                    "message": "hash is required",
                },
                status=422,
            )

        # delete lxmf messages from db where hash matches
        app.database.messages.delete_lxmf_message_by_hash(message_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # serve lxmf messages for conversation

    # serve lxmf messages for conversation
    @routes.get("/api/v1/lxmf-messages/conversation/{destination_hash}")
    async def lxmf_messages_conversation(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")
        order = request.query.get("order", "asc")
        count = request.query.get("count")
        after_id = request.query.get("after_id")

        local_hash = app.local_lxmf_destination.hash.hex()

        try:
            results = await asyncio.to_thread(
                app.message_handler.get_conversation_messages,
                local_hash,
                destination_hash,
                limit=app.message_handler.clamp_conversation_messages_limit(count),
                after_id=after_id if order == "asc" else None,
                before_id=after_id if order == "desc" else None,
            )
        except Exception as e:
            RNS.log(f"Error in lxmf_messages_conversation: {e}", RNS.LOG_ERROR)
            status = 503 if sqlite_error_is_retryable(e) else 500
            return web.json_response(
                {
                    "message": (
                        "Database temporarily unavailable. Retry shortly."
                        if status == 503
                        else "Failed to load conversation"
                    ),
                },
                status=status,
            )

        # convert to response json
        lxmf_messages = [
            convert_db_lxmf_message_to_dict(db_lxmf_message)
            for db_lxmf_message in results
        ]

        return web.json_response(
            {
                "lxmf_messages": lxmf_messages,
            },
        )

    # fetch lxmf message attachment

    # fetch lxmf message attachment
    @routes.get("/api/v1/lxmf-messages/attachment/{message_hash}/{attachment_type}")
    async def lxmf_message_attachment(request):
        message_hash = request.match_info.get("message_hash")
        attachment_type = request.match_info.get("attachment_type")
        file_index = request.query.get("file_index")

        # find message from database
        db_lxmf_message = app.database.messages.get_lxmf_message_by_hash(
            message_hash,
        )
        if db_lxmf_message is None:
            return web.json_response({"message": "Message not found"}, status=404)

        from meshchatx.src.backend.lxmf_utils import parse_stored_lxmf_fields

        fields = parse_stored_lxmf_fields(db_lxmf_message["fields"])
        if fields is None:
            return web.json_response(
                {"message": "Invalid attachment data"},
                status=400,
            )

        # handle image
        if attachment_type == "image" and "image" in fields:
            image_field = fields["image"]
            if not isinstance(image_field, dict):
                return web.json_response(
                    {"message": "Invalid image attachment"},
                    status=400,
                )
            image_bytes_b64 = image_field.get("image_bytes")
            if not isinstance(image_bytes_b64, str) or not image_bytes_b64:
                return web.json_response(
                    {"message": "Missing image data"},
                    status=400,
                )
            try:
                image_data = base64.b64decode(image_bytes_b64)
            except Exception:
                return web.json_response(
                    {"message": "Invalid image data"},
                    status=400,
                )
            allowed_image_types = {"png", "jpeg", "jpg", "gif", "webp", "bmp"}
            detected = detect_image_format_from_magic(image_data)
            if detected is None or detected not in allowed_image_types:
                return web.json_response(
                    {"message": "Invalid image attachment"},
                    status=400,
                )
            # Serve Content-Type from magic bytes, not the peer-declared type.
            image_type = "jpeg" if detected == "jpeg" else detected
            return web.Response(body=image_data, content_type=f"image/{image_type}")

        # handle audio
        if attachment_type == "audio" and "audio" in fields:
            audio_field = fields["audio"]
            if not isinstance(audio_field, dict):
                return web.json_response(
                    {"message": "Invalid audio attachment"},
                    status=400,
                )
            audio_bytes_b64 = audio_field.get("audio_bytes")
            if not isinstance(audio_bytes_b64, str) or not audio_bytes_b64:
                return web.json_response(
                    {"message": "Missing audio data"},
                    status=400,
                )
            try:
                audio_data = base64.b64decode(audio_bytes_b64)
            except Exception:
                return web.json_response(
                    {"message": "Invalid audio data"},
                    status=400,
                )
            return web.Response(
                body=audio_data,
                content_type="application/octet-stream",
            )

        # handle file attachments
        if attachment_type == "file" and "file_attachments" in fields:
            if file_index is not None:
                try:
                    index = int(file_index)
                    if index < 0:
                        return web.json_response(
                            {"message": "Invalid file index"},
                            status=400,
                        )
                    file_attachments = fields["file_attachments"]
                    if not isinstance(file_attachments, list) or index >= len(
                        file_attachments,
                    ):
                        return web.json_response(
                            {"message": "Invalid file index"},
                            status=400,
                        )
                    file_attachment = file_attachments[index]
                    if not isinstance(file_attachment, dict):
                        return web.json_response(
                            {"message": "Invalid file attachment"},
                            status=400,
                        )
                    file_bytes_b64 = file_attachment.get("file_bytes")
                    if not isinstance(file_bytes_b64, str) or not file_bytes_b64:
                        return web.json_response(
                            {"message": "Missing file data"},
                            status=400,
                        )
                    try:
                        file_data = base64.b64decode(file_bytes_b64)
                    except Exception:
                        return web.json_response(
                            {"message": "Invalid file data"},
                            status=400,
                        )
                    raw_name = file_attachment.get("file_name") or "download"
                    if not isinstance(raw_name, str):
                        raw_name = "download"
                    safe_name = (
                        os.path.basename(raw_name)
                        .replace('"', "_")
                        .replace("\r", "")
                        .replace("\n", "")
                        .replace("\x00", "")
                    ) or "download"
                    return web.Response(
                        body=file_data,
                        content_type="application/octet-stream",
                        headers={
                            "Content-Disposition": f'attachment; filename="{safe_name}"',
                        },
                    )
                except (ValueError, IndexError):
                    pass

        return web.json_response({"message": "Attachment not found"}, status=404)

    @routes.get("/api/v1/lxmf-messages/{message_hash}/uri")
    async def lxmf_message_uri(request):
        """Build a reticulum:// URI; prefer the router cache over DB-only state."""
        from meshchatx.src.backend.meshchat_utils import (
            find_lxm_by_content_hash_for_paper_uri,
            hex_identifier_to_bytes,
            lxmf_message_try_paper_uri_string,
            normalized_meshchat_lxmf_message_hash_hex,
        )

        raw_hash = request.match_info.get("message_hash")
        nh = normalized_meshchat_lxmf_message_hash_hex(raw_hash)
        if not nh:
            return web.json_response(
                {"message": "Invalid message hash"},
                status=400,
            )
        hb = hex_identifier_to_bytes(nh)
        if hb is None:
            return web.json_response(
                {"message": "Invalid message hash"},
                status=400,
            )

        lxm = find_lxm_by_content_hash_for_paper_uri(app.message_router, hb)

        if not lxm:
            return web.json_response(
                {
                    "message": "Original message bytes not available for URI generation",
                },
                status=404,
            )

        uri, err_detail = lxmf_message_try_paper_uri_string(lxm)
        if not uri:
            body = {
                "message": "Could not serialize this LXMF payload as a Paper URI",
            }
            if err_detail:
                body["detail"] = err_detail
            return web.json_response(body, status=422)

        return web.json_response({"uri": uri})

    # delete lxmf messages for conversation

    # delete lxmf messages for conversation
    @routes.delete("/api/v1/lxmf-messages/conversation/{destination_hash}")
    async def lxmf_messages_conversation_delete(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get source hash from local lxmf destination
        local_hash = app.local_lxmf_destination.hash.hex()

        for message_hash in app.database.messages.list_message_hashes_for_peer(
            destination_hash,
        ):
            try:
                app.message_router.cancel_outbound(bytes.fromhex(message_hash))
            except Exception:
                pass

        # delete lxmf messages from db where "source to destination" or "destination to source"
        app.message_handler.delete_conversation(local_hash, destination_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )
