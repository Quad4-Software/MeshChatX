# SPDX-License-Identifier: 0BSD

"""Lifecycle helper: resend_failed_messages_for_destination."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from meshchatx.src.backend.auto_resend_guard import (
    AUTO_RESEND_COOLDOWN_SECONDS,
    MAX_AUTO_RESEND_ATTEMPTS,
    RECENT_SAME_CONTENT_SECONDS,
    cooldown_until,
    fields_have_attachments,
    fields_with_auto_resend_count,
    next_attempt_count,
    parse_fields_dict,
    should_skip_for_budget,
)

# ruff: noqa: F821


async def resend_failed_messages_for_destination(
    app: Any,
    destination_hash: str,
    context=None,
):
    mc = __import__("meshchatx.meshchat", fromlist=["*"])
    for _k, _v in mc.__dict__.items():
        if not _k.startswith("__"):
            globals()[_k] = _v

    ctx = context or app.current_context
    if not ctx:
        return

    identity_key = ""
    try:
        if ctx.identity is not None and getattr(ctx.identity, "hash", None):
            identity_key = ctx.identity.hash.hex()
    except Exception:
        identity_key = destination_hash

    lock = app._auto_resend_coordinator.lock_for(identity_key, destination_hash)
    async with lock:
        lookup_hash = destination_hash
        try:
            resolved = app.get_lxmf_destination_hash_for_identity_hash(
                destination_hash,
            )
            if isinstance(resolved, str) and resolved.strip():
                lookup_hash = resolved.strip()
        except Exception:
            lookup_hash = destination_hash

        failed_messages = ctx.database.messages.get_failed_messages_for_destination(
            lookup_hash,
        )
        now = time.time()

        for failed_message in failed_messages:
            try:
                message_hash = failed_message.get("hash")
                if not message_hash:
                    continue

                if should_skip_for_budget(
                    failed_message.get("fields"),
                    max_attempts=MAX_AUTO_RESEND_ATTEMPTS,
                ):
                    continue

                if ctx.database.messages.has_recent_outbound_with_content(
                    destination_hash,
                    failed_message.get("content"),
                    within_seconds=RECENT_SAME_CONTENT_SECONDS,
                    now=now,
                ):
                    continue

                fields = parse_fields_dict(failed_message.get("fields"))
                allow_attachments = ctx.config.allow_auto_resending_failed_messages_with_attachments.get()
                if not allow_attachments and fields_have_attachments(fields):
                    print(
                        "Not resending failed message with attachments, as setting is disabled",
                    )
                    continue

                claimed = (
                    ctx.database.messages.try_claim_failed_message_for_auto_resend(
                        message_hash,
                        cooldown_until=cooldown_until(
                            now,
                            seconds=AUTO_RESEND_COOLDOWN_SECONDS,
                        ),
                        now=now,
                    )
                )
                if not claimed:
                    continue

                # parse image field
                image_field = None
                if "image" in fields and isinstance(fields.get("image"), dict):
                    image_field = LxmfImageField(
                        fields["image"]["image_type"],
                        base64.b64decode(fields["image"]["image_bytes"]),
                    )

                # parse audio field
                audio_field = None
                if "audio" in fields and isinstance(fields.get("audio"), dict):
                    audio_field = LxmfAudioField(
                        fields["audio"]["audio_mode"],
                        base64.b64decode(fields["audio"]["audio_bytes"]),
                    )

                # parse file attachments field
                file_attachments_field = None
                if "file_attachments" in fields and isinstance(
                    fields.get("file_attachments"),
                    list,
                ):
                    file_attachments = [
                        LxmfFileAttachment(
                            file_attachment["file_name"],
                            base64.b64decode(file_attachment["file_bytes"]),
                        )
                        for file_attachment in fields["file_attachments"]
                        if isinstance(file_attachment, dict)
                    ]
                    file_attachments_field = LxmfFileAttachmentsField(
                        file_attachments,
                    )

                attempt = next_attempt_count(failed_message.get("fields"))
                ctx.database.messages.set_message_fields_json(
                    message_hash,
                    fields_with_auto_resend_count(
                        failed_message.get("fields"),
                        attempt,
                    ),
                )

                # send new message with failed message content
                new_message = await app.send_message(
                    failed_message["destination_hash"],
                    failed_message["content"],
                    image_field=image_field,
                    audio_field=audio_field,
                    file_attachments_field=file_attachments_field,
                    context=ctx,
                )

                # Only drop the old failed row after a replacement was queued.
                if new_message is None or getattr(new_message, "hash", None) is None:
                    continue

                new_hash = new_message.hash.hex()
                ctx.database.messages.set_auto_resend_count_on_message(
                    new_hash,
                    attempt,
                )

                ctx.database.messages.delete_lxmf_message_by_hash(message_hash)

                # tell all websocket clients that old failed message was deleted so it can remove from ui
                await app.websocket_broadcast(
                    json.dumps(
                        {
                            "type": "lxmf_message_deleted",
                            "hash": message_hash,
                        },
                    ),
                )

            except Exception as e:
                print(f"Resend of failed LXMF message aborted: {e}")
