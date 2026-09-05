# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: lxmf_forwarding."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F821


def handle_forwarding(app: Any, lxmf_message: LXMF.LXMessage, context=None):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v
    try:
        ctx = context or app.current_context
        if not ctx:
            return
        if not lxmf_signature_validated(lxmf_message):
            return

        source_hash = lxmf_message.source_hash.hex()
        destination_hash = lxmf_message.destination_hash.hex()

        # extract fields for potential forwarding
        lxmf_fields = lxmf_message.get_fields()
        image_field = None
        audio_field = None
        file_attachments_field = None

        if LXMF.FIELD_IMAGE in lxmf_fields:
            parsed_image = parse_lxmf_image_field_value(
                lxmf_fields[LXMF.FIELD_IMAGE],
            )
            if parsed_image:
                image_field = LxmfImageField(parsed_image[0], parsed_image[1])

        if LXMF.FIELD_AUDIO in lxmf_fields:
            parsed_audio = parse_lxmf_audio_field_value(
                lxmf_fields[LXMF.FIELD_AUDIO],
            )
            if parsed_audio:
                audio_field = LxmfAudioField(parsed_audio[0], parsed_audio[1])

        if LXMF.FIELD_FILE_ATTACHMENTS in lxmf_fields:
            parsed_files = parse_lxmf_file_attachments_field_value(
                lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS],
            )
            if parsed_files:
                attachments = [
                    LxmfFileAttachment(name, data) for name, data in parsed_files
                ]
                file_attachments_field = LxmfFileAttachmentsField(attachments)

        app_extensions = None
        if LXMF_APP_EXTENSIONS_FIELD in lxmf_fields and isinstance(
            lxmf_fields[LXMF_APP_EXTENSIONS_FIELD],
            dict,
        ):
            app_extensions = lxmf_fields[LXMF_APP_EXTENSIONS_FIELD]

        # check if this message is for an alias identity (REPLY PATH)
        mapping = ctx.database.messages.get_forwarding_mapping(
            alias_hash=destination_hash,
        )

        if mapping:
            # this is a reply from User C to User B (alias). Forward to User A.
            print(
                f"Forwarding reply from {source_hash} back to original sender {mapping['original_sender_hash']}",
            )
            AsyncUtils.run_async(
                app.send_message(
                    destination_hash=mapping["original_sender_hash"],
                    content=lxmf_message.content,
                    title=lxmf_message.title if hasattr(lxmf_message, "title") else "",
                    image_field=image_field,
                    audio_field=audio_field,
                    file_attachments_field=file_attachments_field,
                    app_extensions=app_extensions,
                    context=ctx,
                ),
            )
            return

        # check if this message matches a forwarding rule (FORWARD PATH)
        # we check for rules that apply to the destination of this message
        rules = ctx.database.misc.get_forwarding_rules(
            identity_hash=destination_hash,
            active_only=True,
        )

        for rule in rules:
            # check source filter if set
            if rule["source_filter_hash"] and rule["source_filter_hash"] != source_hash:
                continue

            # find or create mapping for this (Source, Final Recipient) pair
            mapping = ctx.forwarding_manager.get_or_create_mapping(
                source_hash,
                rule["forward_to_hash"],
                destination_hash,
            )

            # forward to User C from Alias Identity
            print(
                f"Forwarding message from {source_hash} to {rule['forward_to_hash']} via alias {mapping['alias_hash']}",
            )
            AsyncUtils.run_async(
                app.send_message(
                    destination_hash=rule["forward_to_hash"],
                    content=lxmf_message.content,
                    title=lxmf_message.title if hasattr(lxmf_message, "title") else "",
                    sender_identity_hash=mapping["alias_hash"],
                    image_field=image_field,
                    audio_field=audio_field,
                    file_attachments_field=file_attachments_field,
                    app_extensions=app_extensions,
                    context=ctx,
                ),
            )
    except Exception as e:
        print(f"Error in handle_forwarding: {e}")
        import traceback

        traceback.print_exc()
