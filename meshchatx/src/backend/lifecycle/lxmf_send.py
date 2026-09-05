# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: send_message."""

from __future__ import annotations

from typing import Any

from meshchatx.src.backend import reticulum_pathfinding

# ruff: noqa: F821


async def send_lxmf_message(
    app: Any,
    destination_hash: str,
    content: str,
    image_field: LxmfImageField = None,
    audio_field: LxmfAudioField = None,
    file_attachments_field: LxmfFileAttachmentsField = None,
    telemetry_data: bytes | None = None,
    commands: list | None = None,
    delivery_method: str | None = None,
    title: str = "",
    sender_identity_hash: str | None = None,
    reply_to_hash: str | None = None,
    reply_quoted_content: str | None = None,
    reaction_to_hash: str | None = None,
    reaction_emoji: str | None = None,
    app_extensions: dict | None = None,
    no_display: bool = False,
    context=None,
) -> LXMF.LXMessage:
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    g = mc.__dict__
    for _k in (
        "LXMF",
        "RNS",
        "AsyncUtils",
        "InterfaceEditor",
        "InterfaceConfigParser",
        "web",
        "json",
        "logger",
        "logging",
        "os",
        "sys",
        "time",
        "asyncio",
        "traceback",
        "copy",
        "shutil",
        "tempfile",
        "threading",
        "base64",
        "configparser",
        "sqlite3",
        "secrets",
        "re",
        "io",
        "contextlib",
        "datetime",
        "platform",
        "cast",
        "UTC",
        "Telemeter",
        "convert_lxmf_message_to_dict",
        "is_user_facing_lxmf_payload",
        "convert_db_lxmf_message_to_dict",
        "parse_stored_lxmf_fields",
        "lxmf_fields_are_reaction",
        "extract_reaction_from_lxmf_fields",
        "build_lxmf_reaction_field",
        "is_lxmf_outbound_progress_terminal",
        "convert_lxmf_state_to_string",
        "convert_lxmf_method_to_string",
        "message_fields_have_attachments",
        "LxmfFileAttachment",
        "LxmfFileAttachmentsField",
        "LxmfImageField",
        "LxmfAudioField",
    ):
        if _k in g:
            globals()[_k] = g[_k]
    ctx = context or app.current_context
    if not ctx:
        raise RuntimeError("No identity context available for sending message")

    if isinstance(content, bytes):
        content_str = content.decode("utf-8", errors="replace")
    else:
        content_str = content or ""
    quoted_str = reply_quoted_content or ""
    has_standard_reaction = reaction_to_hash is not None and reaction_emoji is not None
    is_reaction_only = bool(
        has_standard_reaction
        and not (content_str and content_str.strip())
        and image_field is None
        and audio_field is None
        and file_attachments_field is None
        and telemetry_data is None
        and commands is None
        and reply_to_hash is None
        and not (quoted_str and quoted_str.strip()),
    )

    # convert destination hash to bytes
    try:
        destination_hash_bytes = bytes.fromhex(destination_hash)
    except (TypeError, ValueError) as exc:
        msg = "Invalid destination hash."
        raise ValueError(msg) from exc

    wants_propagated = delivery_method == "propagated"
    is_local_self = app._is_self_lxmf_destination(destination_hash, ctx)
    if is_local_self and wants_propagated:
        msg = "Propagated delivery is not available for messages to yourapp."
        raise ValueError(msg)

    destination_identity = app.recall_identity(destination_hash)
    if destination_identity is None and is_local_self and ctx.identity:
        destination_identity = ctx.identity
    if destination_identity is None:
        msg = (
            "Could not recall destination identity. "
            "Wait for an announce from this peer, then try again."
        )
        raise LookupError(msg)

    delivery_hash_bytes = reticulum_pathfinding.lxmf_delivery_hash_bytes(
        destination_identity,
        destination_hash_bytes,
    )

    # Direct/opportunistic need a live peer path. Propagated needs a path to
    # the preferred propagation node (not the peer).
    prop_node_bytes = None
    if is_local_self:
        path_outcome = reticulum_pathfinding.OutboundPathOutcome(
            True,
            "local_self",
            False,
        )
    elif wants_propagated:
        router = ctx.message_router
        with contextlib.suppress(Exception):
            prop_node_bytes = router.get_outbound_propagation_node() if router else None
        if not isinstance(prop_node_bytes, (bytes, bytearray)) or not prop_node_bytes:
            msg = (
                "No preferred propagation node configured. "
                "Set one in Settings or Propagation Nodes, then try again."
            )
            raise ValueError(msg)
        prop_node_bytes = bytes(prop_node_bytes)
        local_propagation_destination = getattr(
            router,
            "propagation_destination",
            None,
        )
        local_propagation_hash = getattr(
            local_propagation_destination,
            "hash",
            None,
        )
        if (
            isinstance(local_propagation_hash, (bytes, bytearray))
            and bytes(local_propagation_hash) == prop_node_bytes
        ):
            path_outcome = reticulum_pathfinding.OutboundPathOutcome(
                True,
                "local_propagation_node",
                False,
            )
        else:
            path_outcome = await app._await_transport_path(prop_node_bytes)
    else:
        # Reticulum keeps a live path table, and entries expire when peers move or links drop.
        # We cannot replay "old" paths from the app layer. Transport.request_path refreshes discovery.
        # Wait on lxmf.delivery, not an identity hash or some other aspect dest.
        path_outcome = await app._await_transport_path(delivery_hash_bytes)

    # Direct/opportunistic: peer path. Propagated: preferred propagation node path.
    if not is_local_self and not path_outcome.path_available:
        if wants_propagated:
            msg = (
                "No path to preferred propagation node. "
                "Open Propagation Nodes or Path Finder, wait for a route, then try again."
            )
        else:
            msg = (
                "No path to destination. "
                "Use Path Finder or wait for a route, then try again."
            )
        raise TimeoutError(msg)

    # create destination for recipients lxmf delivery address
    lxmf_destination = RNS.Destination(
        destination_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )

    # determine how the user wants to send the message
    desired_delivery_method = None
    if delivery_method == "direct":
        desired_delivery_method = LXMF.LXMessage.DIRECT
    elif delivery_method == "opportunistic":
        desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC
    elif delivery_method == "propagated":
        desired_delivery_method = LXMF.LXMessage.PROPAGATED

    # determine how to send the message if the user didn't provide a method
    if desired_delivery_method is None:
        # send messages over a direct link by default
        desired_delivery_method = LXMF.LXMessage.DIRECT
        if (
            not ctx.message_router.delivery_link_available(delivery_hash_bytes)
            and RNS.Identity.current_ratchet_id(delivery_hash_bytes) is not None
        ):
            # since there's no link established to the destination, it's faster to send opportunistically
            # this is because it takes several packets to establish a link, and then we still have to send the message over it
            # oppotunistic mode will send the message in a single packet (if the message is small enough, otherwise it falls back to a direct link)
            # we will only do this if an encryption ratchet is available, so single packet delivery is more secure
            desired_delivery_method = LXMF.LXMessage.OPPORTUNISTIC

    # determine which identity to send from
    source_destination = ctx.local_lxmf_destination
    if sender_identity_hash is not None:
        if (
            ctx.forwarding_manager
            and sender_identity_hash in ctx.forwarding_manager.forwarding_destinations
        ):
            source_destination = ctx.forwarding_manager.forwarding_destinations[
                sender_identity_hash
            ]
        else:
            print(
                f"Warning: requested sender identity {sender_identity_hash} not found, using default.",
            )

    # create lxmf message
    lxmf_message = LXMF.LXMessage(
        lxmf_destination,
        source_destination,
        content,
        title=title,
        desired_method=desired_delivery_method,
    )
    lxmf_message.try_propagation_on_fail = (
        ctx.config.auto_send_failed_messages_to_propagation_node.get()
    )

    lxmf_message.fields = {}

    if not is_reaction_only:
        lxmf_message.fields[LXMF.FIELD_RENDERER] = LXMF.RENDERER_MARKDOWN

    if app._is_contact(destination_hash, context=ctx) and not is_reaction_only:
        lxmf_message.include_ticket = True

    # add file attachments field
    if file_attachments_field is not None:
        # create array of [[file_name, file_bytes], [file_name, file_bytes], ...]
        file_attachments = [
            [file_attachment.file_name, file_attachment.file_bytes]
            for file_attachment in file_attachments_field.file_attachments
        ]

        # set field attachments field
        lxmf_message.fields[LXMF.FIELD_FILE_ATTACHMENTS] = file_attachments

    # add image field
    if image_field is not None:
        lxmf_message.fields[LXMF.FIELD_IMAGE] = [
            image_field.image_type,
            image_field.image_bytes,
        ]

    # add audio field
    if audio_field is not None:
        audio_bytes = audio_field.audio_bytes
        if audio_field.audio_mode == LXMF.AM_OPUS_OGG:
            audio_bytes = app._convert_webm_opus_to_ogg(audio_bytes)
        lxmf_message.fields[LXMF.FIELD_AUDIO] = [
            audio_field.audio_mode,
            audio_bytes,
        ]

    # add telemetry field
    if telemetry_data is not None:
        lxmf_message.fields[LXMF.FIELD_TELEMETRY] = telemetry_data

    # add commands field
    if commands is not None:
        lxmf_message.fields[LXMF.FIELD_COMMANDS] = commands

    if reply_to_hash is not None:
        lxmf_message.fields[FIELD_REPLY_TO] = bytes.fromhex(reply_to_hash)
    if reply_quoted_content is not None and reply_quoted_content:
        lxmf_message.fields[FIELD_REPLY_QUOTE] = reply_quoted_content.encode(
            "utf-8",
        )

    if has_standard_reaction:
        lxmf_message.fields[FIELD_REACTION] = build_lxmf_reaction_field(
            reaction_to_hash,
            reaction_emoji or "",
        )
    elif app_extensions is not None:
        lxmf_message.fields[LXMF_APP_EXTENSIONS_FIELD] = app_extensions

    # add icon appearance if configured and not already sent to this destination
    current_icon_hash = app.get_current_icon_hash()
    if current_icon_hash is not None and not is_reaction_only:
        last_sent_icon_hash = app.database.misc.get_last_sent_icon_hash(
            destination_hash,
        )

        if last_sent_icon_hash != current_icon_hash:
            lxmf_user_icon_name = app.config.lxmf_user_icon_name.get()
            lxmf_user_icon_foreground_colour = (
                app.config.lxmf_user_icon_foreground_colour.get()
            )
            lxmf_user_icon_background_colour = (
                app.config.lxmf_user_icon_background_colour.get()
            )

            lxmf_message.fields[LXMF.FIELD_ICON_APPEARANCE] = [
                lxmf_user_icon_name,
                ColourUtils.hex_colour_to_byte_array(
                    lxmf_user_icon_foreground_colour,
                ),
                ColourUtils.hex_colour_to_byte_array(
                    lxmf_user_icon_background_colour,
                ),
            ]

            # update last sent icon hash for this destination
            ctx.database.misc.update_last_sent_icon_hash(
                destination_hash,
                current_icon_hash,
            )

    if is_local_self:
        lxmf_message.pack()
        lxmf_message.state = LXMF.LXMessage.DELIVERED
        lxmf_message.progress = 1.0
        local_peer = ctx.local_lxmf_destination.hexhash
        if not no_display:
            app.db_upsert_lxmf_message(
                lxmf_message,
                context=ctx,
                path_finding_measure=reticulum_pathfinding.format_outbound_path_finding_measure(
                    path_outcome,
                ),
                path_row_hash_hex=local_peer,
                state_override="delivered",
                method_override="local",
            )
            ws_payload = convert_lxmf_message_to_dict(
                lxmf_message,
                include_attachments=False,
                reticulum=app.reticulum,
                message_router=ctx.message_router,
            )
            ws_payload["state"] = "delivered"
            ws_payload["method"] = "local"
            ws_payload["progress"] = 100.0
            await app.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf_message_created",
                        "lxmf_message": ws_payload,
                    },
                ),
            )
        return lxmf_message

    # register delivery callbacks
    lxmf_message.register_delivery_callback(
        lambda msg: app.on_lxmf_sending_state_updated(msg, context=ctx),
    )
    lxmf_message.register_failed_callback(
        lambda msg: app.on_lxmf_sending_failed(msg, context=ctx),
    )

    # determine which router to use
    router = ctx.message_router
    if (
        sender_identity_hash is not None
        and ctx.forwarding_manager
        and sender_identity_hash in ctx.forwarding_manager.forwarding_routers
    ):
        router = ctx.forwarding_manager.forwarding_routers[sender_identity_hash]

    # send lxmf message to be routed to destination
    router.handle_outbound(lxmf_message)

    # upsert lxmf message to database
    if not no_display:
        path_row_hex = None
        if path_outcome.path_available:
            if wants_propagated and isinstance(prop_node_bytes, (bytes, bytearray)):
                path_row_hex = bytes(prop_node_bytes).hex()
            else:
                path_row_hex = delivery_hash_bytes.hex()
        app.db_upsert_lxmf_message(
            lxmf_message,
            context=ctx,
            path_finding_measure=reticulum_pathfinding.format_outbound_path_finding_measure(
                path_outcome,
            ),
            path_row_hash_hex=path_row_hex,
        )

    # tell all websocket clients that old failed message was deleted so it can remove from ui
    if not no_display:
        await app.websocket_broadcast(
            json.dumps(
                {
                    "type": "lxmf_message_created",
                    "lxmf_message": convert_lxmf_message_to_dict(
                        lxmf_message,
                        include_attachments=False,
                        reticulum=app.reticulum,
                        message_router=ctx.message_router,
                    ),
                },
            ),
        )

    # handle lxmf message progress loop without blocking or awaiting
    # otherwise other incoming websocket packets will not be processed until sending is complete
    # which results in the next message not showing up until the first message is finished
    if not no_display:
        AsyncUtils.run_async(
            app.handle_lxmf_message_progress(lxmf_message, context=ctx),
        )

    return lxmf_message
