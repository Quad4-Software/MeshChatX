# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: on_lxmf_delivery."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def handle_lxmf_delivery(app: Any, lxmf_message: LXMF.LXMessage, context=None):
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
    """Handle inbound LXMF delivery from Reticulum (synchronous callback)."""
    ctx = context or app.current_context
    if not ctx or not ctx.running or not ctx.database:
        logger.warning(
            "Dropping inbound LXMF delivery: context not ready "
            "(ctx=%s running=%s database=%s)",
            ctx is not None,
            getattr(ctx, "running", None) if ctx else None,
            ctx.database is not None if ctx else None,
        )
        return

    try:
        source_hash = lxmf_message.source_hash.hex()
        unverified_reason = getattr(lxmf_message, "unverified_reason", None)

        if unverified_reason == LXMF.LXMessage.SIGNATURE_INVALID:
            logger.warning("Invalid LXMF signature from %s, dropping", source_hash)
            return

        # check if source is blocked - reject immediately
        if app.is_destination_blocked(source_hash, context=ctx):
            print(f"Rejecting LXMF message from blocked source: {source_hash}")
            return

        # track incoming message timestamps for flood protection
        app._lxmf_incoming_timestamps.append(time.time())
        app._lxmf_incoming_timestamps = prune_lxmf_incoming_timestamps(
            app._lxmf_incoming_timestamps,
        )
        app._check_lxmf_flood_protection(context=ctx)

        if ctx.config.block_all_from_strangers.get() and not app._is_contact(
            source_hash,
            context=ctx,
        ):
            print(
                f"Blocking entire message from stranger: {source_hash}",
            )
            return

        is_sideband_telemetry_request = False
        lxmf_fields = lxmf_message.get_fields()

        # FIELD_COMMANDS (9) is the LXMF-standard command slot.
        # Field 0x01 is FIELD_EMBEDDED_LXMS on the wire. Sideband also put
        # telemetry requests there historically, so only treat Sideband-shaped
        # entries as commands and leave packed embedded LXMs alone.
        commands = []
        if LXMF.FIELD_COMMANDS in lxmf_fields:
            commands.extend(
                extract_sideband_command_entries(lxmf_fields[LXMF.FIELD_COMMANDS]),
            )
        embedded_field = getattr(LXMF, "FIELD_EMBEDDED_LXMS", 0x01)
        if embedded_field in lxmf_fields and embedded_field != LXMF.FIELD_COMMANDS:
            commands.extend(
                extract_sideband_command_entries(lxmf_fields[embedded_field]),
            )

        if commands:
            for command in commands:
                if (
                    (
                        isinstance(command, dict)
                        and (
                            SidebandCommands.TELEMETRY_REQUEST in command
                            or str(SidebandCommands.TELEMETRY_REQUEST) in command
                            or f"0x{SidebandCommands.TELEMETRY_REQUEST:02x}" in command
                        )
                    )
                    or (
                        isinstance(command, (list, tuple))
                        and SidebandCommands.TELEMETRY_REQUEST in command
                    )
                    or command == SidebandCommands.TELEMETRY_REQUEST
                    or str(command) == str(SidebandCommands.TELEMETRY_REQUEST)
                ):
                    is_sideband_telemetry_request = True
                if (
                    isinstance(command, dict)
                    and SidebandCommands.PLUGIN_COMMAND in command
                    and lxmf_signature_validated(lxmf_message)
                ):
                    plugin_command = command.get(SidebandCommands.PLUGIN_COMMAND)
                    if isinstance(plugin_command, bytes):
                        plugin_command = plugin_command.decode(
                            "utf-8",
                            errors="replace",
                        )
                    if isinstance(plugin_command, str) and plugin_command.strip():
                        try:
                            app.sideband_plugin_loader.handle_plugin_command(
                                plugin_command,
                                lxmf_message,
                            )
                        except Exception as exc:
                            print(f"Sideband plugin command failed: {exc}")

        # Respond to telemetry requests as a side effect. Do not return early:
        # spam, stranger-attachment, and drop policies must still run.
        if is_sideband_telemetry_request:
            if not ctx.config.telemetry_enabled.get():
                print(f"Telemetry is disabled, ignoring request from {source_hash}")
            elif not lxmf_signature_validated(lxmf_message):
                print(
                    f"Ignoring unsigned telemetry request from {source_hash}",
                )
            else:
                contact = ctx.database.contacts.get_contact_by_identity_hash(
                    source_hash,
                )
                if not contact or not contact.get("is_telemetry_trusted"):
                    print(
                        f"Telemetry request from untrusted peer {source_hash}, ignoring",
                    )
                else:
                    lat, lon = app._resolve_location_for_telemetry()
                    if lat is not None and lon is not None:
                        print(f"Responding to telemetry request from {source_hash}")
                        app.handle_telemetry_request(source_hash)
                    else:
                        if not hasattr(app, "_telemetry_no_location_warned"):
                            app._telemetry_no_location_warned = set()
                        if source_hash not in app._telemetry_no_location_warned:
                            if len(app._telemetry_no_location_warned) >= 256:
                                app._telemetry_no_location_warned.clear()
                            app._telemetry_no_location_warned.add(source_hash)
                            print(
                                f"Cannot respond to telemetry request from {source_hash}: No location set. "
                                "Set manual coordinates in Settings > Location to respond.",
                            )

        # check for spam keywords
        is_spam = False
        message_title = lxmf_message.title if hasattr(lxmf_message, "title") else ""
        message_content = (
            lxmf_message.content if hasattr(lxmf_message, "content") else ""
        )
        if isinstance(message_content, bytes):
            message_content = message_content.decode("utf-8", errors="replace")
        elif message_content is None:
            message_content = ""
        if isinstance(message_title, bytes):
            message_title = message_title.decode("utf-8", errors="replace")
        elif message_title is None:
            message_title = ""

        is_reaction_only = lxmf_is_reaction_only_delivery(
            lxmf_fields,
            message_title,
            message_content,
        )

        # check spam keywords (reaction+body must not skip spam)
        if not is_reaction_only and app.check_spam_keywords(
            message_title,
            message_content,
            context=ctx,
        ):
            is_spam = True
            print(
                f"Marking LXMF message as spam due to keyword match: {source_hash}",
            )

        # reject attachments from blocked sources (already checked above, but double-check)
        attachments_stripped = False
        if has_attachments(lxmf_fields):
            if app.is_destination_blocked(source_hash, context=ctx):
                print(
                    f"Rejecting LXMF message with attachments from blocked source: {source_hash}",
                )
                return
            # reject attachments from spam sources
            if is_spam:
                print(
                    f"Rejecting LXMF message with attachments from spam source: {source_hash}",
                )
                return
            # strip attachments from strangers (non-contacts) if setting is enabled
            if (
                ctx.config.block_attachments_from_strangers.get()
                and not app._is_contact(source_hash, context=ctx)
            ):
                for key in (
                    LXMF.FIELD_FILE_ATTACHMENTS,
                    LXMF.FIELD_IMAGE,
                    LXMF.FIELD_AUDIO,
                ):
                    if key in lxmf_fields:
                        del lxmf_fields[key]
                lxmf_message.fields = lxmf_fields
                attachments_stripped = True
                print(
                    f"Stripped attachments from stranger: {source_hash}",
                )

        # upsert lxmf message to database with spam flag
        app.db_upsert_lxmf_message(
            lxmf_message,
            is_spam=is_spam,
            attachments_stripped=attachments_stripped,
            context=ctx,
        )
        app._maybe_store_path_at_send_for_lxmf(ctx, lxmf_message)

        # handle forwarding
        if lxmf_signature_validated(lxmf_message):
            app.handle_forwarding(lxmf_message, context=ctx)

        app._apply_lxmf_sieve_folder_rule(
            source_hash,
            context=ctx,
            message_title=message_title,
            message_content=message_content,
        )
        app._apply_lxmf_sieve_banish_rule(
            source_hash,
            context=ctx,
            message_title=message_title,
            message_content=message_content,
        )
        app._apply_message_blocklist_banish_rule(
            source_hash,
            context=ctx,
            message_title=message_title,
            message_content=message_content,
        )

        # handle telemetry
        try:
            if lxmf_signature_validated(lxmf_message):
                message_fields = lxmf_message.get_fields()

                # Single telemetry entry
                if LXMF.FIELD_TELEMETRY in message_fields:
                    app.process_incoming_telemetry(
                        source_hash,
                        message_fields[LXMF.FIELD_TELEMETRY],
                        lxmf_message,
                        context=ctx,
                    )

                # Telemetry stream (multiple entries)
                if (
                    hasattr(LXMF, "FIELD_TELEMETRY_STREAM")
                    and LXMF.FIELD_TELEMETRY_STREAM in message_fields
                ):
                    stream = message_fields[LXMF.FIELD_TELEMETRY_STREAM]
                    if isinstance(stream, (list, tuple)):
                        sender_trusted = False
                        contact = ctx.database.contacts.get_contact_by_identity_hash(
                            source_hash,
                        )
                        if contact and contact.get("is_telemetry_trusted"):
                            sender_trusted = True
                        for entry in stream:
                            if not isinstance(entry, (list, tuple)) or len(entry) < 3:
                                continue
                            entry_source = normalize_lxmf_destination_hash(entry[0])
                            if not entry_source:
                                continue
                            if entry_source != source_hash and not sender_trusted:
                                continue
                            entry_timestamp = _valid_number(entry[1])
                            if entry_timestamp is None:
                                continue
                            entry_data = entry[2]
                            app.process_incoming_telemetry(
                                entry_source,
                                entry_data,
                                lxmf_message,
                                timestamp_override=int(entry_timestamp),
                                context=ctx,
                            )
        except Exception as e:
            print(f"Failed to handle telemetry in LXMF message: {e}")

        # update lxmf user icon if icon appearance field is available
        try:
            if lxmf_signature_validated(lxmf_message):
                message_fields = lxmf_message.get_fields()
                icon_appearance = parse_lxmf_icon_appearance(
                    message_fields.get(LXMF.FIELD_ICON_APPEARANCE),
                )
                if icon_appearance:
                    icon_name, foreground_colour, background_colour = icon_appearance

                    local_hash = (
                        ctx.local_lxmf_destination.hexhash
                        if ctx.local_lxmf_destination
                        else None
                    )
                    source_hash = lxmf_message.source_hash.hex()

                    # ignore our own icon and empty payloads to avoid overwriting peers with our appearance
                    if (source_hash and local_hash and source_hash == local_hash) or (
                        not icon_name or not foreground_colour or not background_colour
                    ):
                        pass
                    else:
                        local_icon_name = ctx.config.lxmf_user_icon_name.get()
                        local_icon_fg = (
                            ctx.config.lxmf_user_icon_foreground_colour.get()
                        )
                        local_icon_bg = (
                            ctx.config.lxmf_user_icon_background_colour.get()
                        )

                        # if incoming icon matches our own, skip storing and clear any mistaken stored copy
                        # for now, but this will need to be updated later if two users do have the same icon
                        if (
                            local_icon_name
                            and local_icon_fg
                            and local_icon_bg
                            and icon_name == local_icon_name
                            and foreground_colour == local_icon_fg
                            and background_colour == local_icon_bg
                        ):
                            ctx.database.misc.delete_user_icon(source_hash)
                        else:
                            app.update_lxmf_user_icon(
                                source_hash,
                                icon_name,
                                foreground_colour,
                                background_colour,
                                context=ctx,
                            )
        except Exception as e:
            print("LXMF user icon update from message fields failed")
            print(e)

        sender_name = ctx.database.announces.get_custom_display_name(source_hash)
        if not sender_name:
            announce = ctx.database.announces.get_announce_by_hash(source_hash)
            if announce and announce["app_data"]:
                sender_name = parse_lxmf_display_name(
                    app_data_base64=announce["app_data"],
                    default_value=None,
                )

        if not sender_name:
            sender_name = source_hash[:8]

        msg_dict = convert_lxmf_message_to_dict(
            lxmf_message,
            include_attachments=False,
            reticulum=app.reticulum,
        )
        app._merge_stored_path_fields_from_db(
            ctx,
            lxmf_message.hash.hex(),
            msg_dict,
        )

        suppress_notifications = app._lxmf_sieve_suppresses_notifications(
            source_hash,
            context=ctx,
            message_title=message_title,
            message_content=message_content,
        )

        AsyncUtils.run_async(
            app.websocket_broadcast(
                json.dumps(
                    {
                        "type": "lxmf.delivery",
                        "remote_identity_name": sender_name,
                        "lxmf_message": msg_dict,
                        "sieve_suppress_notifications": suppress_notifications,
                    },
                ),
            ),
        )

    except Exception as e:
        # do nothing on error
        print(f"lxmf_delivery error: {e}")


# handles lxmf message forwarding logic
