# SPDX-License-Identifier: 0BSD

import base64
import json

import LXMF

from meshchatx.src.backend.telemetry_utils import Telemeter

# Columba-compatible app extensions (emoji reactions, reply metadata, etc.)
LXMF_APP_EXTENSIONS_FIELD = 16

# Raw LXMF integer field identifiers used when classifying "user-facing" payloads
LXMF_FILE_ATTACHMENTS_FIELD = LXMF.FIELD_FILE_ATTACHMENTS
LXMF_IMAGE_FIELD = LXMF.FIELD_IMAGE
LXMF_AUDIO_FIELD = LXMF.FIELD_AUDIO


def lxmf_fields_are_columba_reaction(lxmf_fields: dict) -> bool:
    if not isinstance(lxmf_fields, dict):
        return False
    val = lxmf_fields.get(LXMF_APP_EXTENSIONS_FIELD)
    return isinstance(val, dict) and "reaction_to" in val


def is_user_facing_lxmf_payload(fields, content, title) -> bool:
    """Determine whether an LXMF message represents a user-visible item.

    Messages that should NOT raise the notification bell:
      - reactions (Columba app_extensions.reaction_to with no other payload)
      - telemetry-only messages (FIELD_TELEMETRY / fields["telemetry"] with no body)
      - icon-only / appearance-only updates (no body, no attachment)
      - empty pings (no content, no title, no attachment)

    The helper is intentionally tolerant: ``fields`` may be the rich dict
    produced by :func:`convert_lxmf_message_to_dict` (string keys), the raw
    LXMF integer-keyed dict, or a JSON-string from the database.
    """
    import json as _json

    if isinstance(fields, str):
        try:
            fields = _json.loads(fields) if fields else {}
        except (ValueError, TypeError):
            fields = {}
    if not isinstance(fields, dict):
        fields = {}

    app_ext = fields.get("app_extensions")
    if not isinstance(app_ext, dict):
        raw_app_ext = fields.get(LXMF_APP_EXTENSIONS_FIELD)
        if isinstance(raw_app_ext, dict):
            app_ext = raw_app_ext
    if isinstance(app_ext, dict) and "reaction_to" in app_ext:
        return False

    def _has_text(value):
        if value is None:
            return False
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:
                return False
        return bool(str(value).strip())

    if _has_text(content):
        return True
    if _has_text(title):
        return True

    image = fields.get("image")
    if isinstance(image, dict) and (
        image.get("image_size") or image.get("image_bytes")
    ):
        return True
    if image is None and fields.get(LXMF_IMAGE_FIELD) is not None:
        return True

    audio = fields.get("audio")
    if isinstance(audio, dict) and (
        audio.get("audio_size") or audio.get("audio_bytes")
    ):
        return True
    if audio is None and fields.get(LXMF_AUDIO_FIELD) is not None:
        return True

    file_attachments = fields.get("file_attachments")
    if isinstance(file_attachments, list) and len(file_attachments) > 0:
        return True
    raw_files = fields.get(LXMF_FILE_ATTACHMENTS_FIELD)
    if isinstance(raw_files, list) and len(raw_files) > 0:
        return True

    return False


def convert_lxmf_message_to_dict(
    lxmf_message: LXMF.LXMessage,
    include_attachments: bool = True,
    reticulum=None,
):
    # handle fields
    fields = {}
    message_fields = lxmf_message.get_fields()
    is_reaction = False
    reaction_to = None
    reaction_emoji = None
    reaction_sender = None
    for field_type in message_fields:
        value = message_fields[field_type]

        # handle file attachments field
        if field_type == LXMF.FIELD_FILE_ATTACHMENTS and isinstance(value, list):
            file_attachments = []
            for file_attachment in value:
                if (
                    not isinstance(file_attachment, (list, tuple))
                    or len(file_attachment) < 2
                ):
                    continue
                file_name = file_attachment[0]
                file_data = file_attachment[1]
                if not isinstance(file_data, (bytes, bytearray)):
                    continue
                file_bytes = None
                if include_attachments:
                    file_bytes = base64.b64encode(file_data).decode(
                        "utf-8",
                    )

                file_attachments.append(
                    {
                        "file_name": str(file_name) if file_name else "",
                        "file_size": len(file_data),
                        "file_bytes": file_bytes,
                    },
                )

            fields["file_attachments"] = file_attachments

        # handle image field
        if (
            field_type == LXMF.FIELD_IMAGE
            and isinstance(value, (list, tuple))
            and len(value) >= 2
        ):
            image_type = value[0]
            image_data = value[1]
            if isinstance(image_data, (bytes, bytearray)):
                image_bytes = None
                if include_attachments:
                    image_bytes = base64.b64encode(image_data).decode("utf-8")

                fields["image"] = {
                    "image_type": image_type,
                    "image_size": len(image_data),
                    "image_bytes": image_bytes,
                }

        # handle audio field
        if (
            field_type == LXMF.FIELD_AUDIO
            and isinstance(value, (list, tuple))
            and len(value) >= 2
        ):
            audio_mode = value[0]
            audio_data = value[1]
            if isinstance(audio_data, (bytes, bytearray)):
                audio_bytes = None
                if include_attachments:
                    audio_bytes = base64.b64encode(audio_data).decode("utf-8")

                fields["audio"] = {
                    "audio_mode": audio_mode,
                    "audio_size": len(audio_data),
                    "audio_bytes": audio_bytes,
                }

        # handle telemetry field
        if field_type == LXMF.FIELD_TELEMETRY:
            fields["telemetry"] = Telemeter.from_packed(value)

        # handle commands field
        if field_type == LXMF.FIELD_COMMANDS or field_type == 0x01:
            processed_commands = []
            if isinstance(value, list):
                for cmd in value:
                    if isinstance(cmd, dict):
                        new_cmd = {}
                        for k, v in cmd.items():
                            if isinstance(k, int):
                                new_cmd[f"0x{k:02x}"] = v
                            else:
                                new_cmd[str(k)] = v
                        processed_commands.append(new_cmd)
                    else:
                        processed_commands.append(cmd)
            elif isinstance(value, dict):
                new_cmd = {}
                for k, v in value.items():
                    if isinstance(k, int):
                        new_cmd[f"0x{k:02x}"] = v
                    else:
                        new_cmd[str(k)] = v
                processed_commands.append(new_cmd)
            fields["commands"] = processed_commands

        # handle reply_to field
        if field_type == 0x30:
            fields["reply_to"] = value.hex() if isinstance(value, bytes) else value
        if field_type == 0x31:
            fields["reply_quoted_content"] = (
                value.decode("utf-8", errors="replace")
                if isinstance(value, bytes)
                else value
            )

        if field_type == LXMF_APP_EXTENSIONS_FIELD and isinstance(value, dict):
            fields["app_extensions"] = dict(value)
            if "reaction_to" in value:
                is_reaction = True
                reaction_to = value.get("reaction_to") or ""
                reaction_emoji = value.get("emoji") or ""
                reaction_sender = value.get("sender") or ""

    # convert 0.0-1.0 progress to 0.00-100 percentage
    progress_percentage = round(lxmf_message.progress * 100, 2)

    # get rssi
    rssi = lxmf_message.rssi
    if rssi is None and reticulum:
        rssi = reticulum.get_packet_rssi(lxmf_message.hash)

    # get snr
    snr = lxmf_message.snr
    if snr is None and reticulum:
        snr = reticulum.get_packet_snr(lxmf_message.hash)

    # get quality
    quality = lxmf_message.q
    if quality is None and reticulum:
        quality = reticulum.get_packet_q(lxmf_message.hash)

    # get reply_to_hash from fields if present
    reply_to_hash = None
    if 0x30 in message_fields:
        val = message_fields[0x30]
        reply_to_hash = val.hex() if isinstance(val, bytes) else val

    content = (
        lxmf_message.content.decode("utf-8", errors="replace")
        if lxmf_message.content
        else ""
    )

    # auto-detect reply from content if not present
    if not reply_to_hash and content and isinstance(content, str):
        import re

        match = re.search(r"^> ([a-fA-F0-9]{32})\s*\n?", content)
        if match:
            reply_to_hash = match.group(1)

    out = {
        "hash": lxmf_message.hash.hex(),
        "source_hash": lxmf_message.source_hash.hex(),
        "destination_hash": lxmf_message.destination_hash.hex(),
        "is_incoming": lxmf_message.incoming,
        "state": convert_lxmf_state_to_string(lxmf_message),
        "progress": progress_percentage,
        "method": convert_lxmf_method_to_string(lxmf_message),
        "delivery_attempts": lxmf_message.delivery_attempts,
        "next_delivery_attempt_at": getattr(
            lxmf_message,
            "next_delivery_attempt",
            None,
        ),  # attribute may not exist yet
        "title": lxmf_message.title.decode("utf-8", errors="replace")
        if lxmf_message.title
        else "",
        "content": content,
        "fields": fields,
        "timestamp": lxmf_message.timestamp,
        "rssi": rssi,
        "snr": snr,
        "quality": quality,
        "reply_to_hash": reply_to_hash,
        "is_reaction": is_reaction,
    }
    if is_reaction:
        out["reaction_to"] = reaction_to
        out["reaction_emoji"] = reaction_emoji
        out["reaction_sender"] = reaction_sender
    return out


def convert_lxmf_state_to_string(lxmf_message: LXMF.LXMessage):
    # convert state to string
    lxmf_message_state = "unknown"
    if lxmf_message.state == LXMF.LXMessage.GENERATING:
        lxmf_message_state = "generating"
    elif lxmf_message.state == LXMF.LXMessage.OUTBOUND:
        lxmf_message_state = "outbound"
    elif lxmf_message.state == LXMF.LXMessage.SENDING:
        lxmf_message_state = "sending"
    elif lxmf_message.state == LXMF.LXMessage.SENT:
        lxmf_message_state = "sent"
    elif lxmf_message.state == LXMF.LXMessage.DELIVERED:
        lxmf_message_state = "delivered"
    elif lxmf_message.state == LXMF.LXMessage.REJECTED:
        lxmf_message_state = "rejected"
    elif lxmf_message.state == LXMF.LXMessage.CANCELLED:
        lxmf_message_state = "cancelled"
    elif lxmf_message.state == LXMF.LXMessage.FAILED:
        lxmf_message_state = "failed"

    return lxmf_message_state


def convert_lxmf_method_to_string(lxmf_message: LXMF.LXMessage):
    # convert method to string
    lxmf_message_method = "unknown"
    if lxmf_message.method == LXMF.LXMessage.OPPORTUNISTIC:
        lxmf_message_method = "opportunistic"
    elif lxmf_message.method == LXMF.LXMessage.DIRECT:
        lxmf_message_method = "direct"
    elif lxmf_message.method == LXMF.LXMessage.PROPAGATED:
        lxmf_message_method = "propagated"
    elif lxmf_message.method == LXMF.LXMessage.PAPER:
        lxmf_message_method = "paper"

    return lxmf_message_method


def convert_db_lxmf_message_to_dict(
    db_lxmf_message,
    include_attachments: bool = False,
):
    try:
        fields_str = db_lxmf_message.get("fields", "{}")
        fields = json.loads(fields_str) if fields_str else {}
    except (json.JSONDecodeError, TypeError):
        fields = {}

    if not isinstance(fields, dict):
        fields = {}

    is_reaction = False
    reaction_to = None
    reaction_emoji = None
    reaction_sender = None
    app = fields.get("app_extensions")
    if isinstance(app, dict) and "reaction_to" in app:
        is_reaction = True
        reaction_to = app.get("reaction_to") or ""
        reaction_emoji = app.get("emoji") or ""
        reaction_sender = app.get("sender") or ""

    # normalize commands if present
    if "commands" in fields:
        cmds = fields["commands"]
        if isinstance(cmds, list):
            new_cmds = []
            for cmd in cmds:
                if isinstance(cmd, dict):
                    new_cmd = {}
                    for k, v in cmd.items():
                        # normalize key to 0xXX format if it's a number string
                        try:
                            ki = None
                            if isinstance(k, int):
                                ki = k
                            elif isinstance(k, str):
                                if k.startswith("0x"):
                                    ki = int(k, 16)
                                else:
                                    ki = int(k)

                            if ki is not None:
                                new_cmd[f"0x{ki:02x}"] = v
                            else:
                                new_cmd[str(k)] = v
                        except (ValueError, TypeError):
                            new_cmd[str(k)] = v
                    new_cmds.append(new_cmd)
                else:
                    new_cmds.append(cmd)
            fields["commands"] = new_cmds

    # strip attachments if requested
    if not include_attachments:
        if "image" in fields:
            # keep type but strip bytes
            image_size = fields["image"].get("image_size") or 0
            b64_bytes = fields["image"].get("image_bytes")
            if not image_size and b64_bytes:
                # Optimized size calculation without full decoding
                image_size = (len(b64_bytes) * 3) // 4
                if b64_bytes.endswith("=="):
                    image_size -= 2
                elif b64_bytes.endswith("="):
                    image_size -= 1
            fields["image"] = {
                "image_type": fields["image"].get("image_type"),
                "image_size": image_size,
                "image_bytes": None,
            }
        if "audio" in fields:
            # keep mode but strip bytes
            audio_size = fields["audio"].get("audio_size") or 0
            b64_bytes = fields["audio"].get("audio_bytes")
            if not audio_size and b64_bytes:
                audio_size = (len(b64_bytes) * 3) // 4
                if b64_bytes.endswith("=="):
                    audio_size -= 2
                elif b64_bytes.endswith("="):
                    audio_size -= 1
            fields["audio"] = {
                "audio_mode": fields["audio"].get("audio_mode"),
                "audio_size": audio_size,
                "audio_bytes": None,
            }
        if "file_attachments" in fields:
            # keep file names but strip bytes
            for i in range(len(fields["file_attachments"])):
                file_size = fields["file_attachments"][i].get("file_size") or 0
                b64_bytes = fields["file_attachments"][i].get("file_bytes")
                if not file_size and b64_bytes:
                    file_size = (len(b64_bytes) * 3) // 4
                    if b64_bytes.endswith("=="):
                        file_size -= 2
                    elif b64_bytes.endswith("="):
                        file_size -= 1
                fields["file_attachments"][i] = {
                    "file_name": fields["file_attachments"][i].get("file_name"),
                    "file_size": file_size,
                    "file_bytes": None,
                }

    # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
    created_at = str(db_lxmf_message["created_at"])
    if created_at and "+" not in created_at and "Z" not in created_at:
        created_at += "Z"

    updated_at = str(db_lxmf_message["updated_at"])
    if updated_at and "+" not in updated_at and "Z" not in updated_at:
        updated_at += "Z"

    out = {
        "id": db_lxmf_message["id"],
        "hash": db_lxmf_message["hash"],
        "source_hash": db_lxmf_message["source_hash"],
        "destination_hash": db_lxmf_message["destination_hash"],
        "is_incoming": bool(db_lxmf_message["is_incoming"]),
        "state": db_lxmf_message["state"],
        "progress": db_lxmf_message["progress"],
        "method": db_lxmf_message["method"],
        "delivery_attempts": db_lxmf_message["delivery_attempts"],
        "next_delivery_attempt_at": db_lxmf_message["next_delivery_attempt_at"],
        "title": db_lxmf_message["title"],
        "content": db_lxmf_message["content"],
        "fields": fields,
        "timestamp": db_lxmf_message["timestamp"],
        "rssi": db_lxmf_message["rssi"],
        "snr": db_lxmf_message["snr"],
        "quality": db_lxmf_message["quality"],
        "is_spam": bool(db_lxmf_message["is_spam"]),
        "reply_to_hash": db_lxmf_message.get("reply_to_hash"),
        "attachments_stripped": bool(db_lxmf_message.get("attachments_stripped", 0)),
        "created_at": created_at,
        "updated_at": updated_at,
        "is_reaction": is_reaction,
    }
    if is_reaction:
        out["reaction_to"] = reaction_to
        out["reaction_emoji"] = reaction_emoji
        out["reaction_sender"] = reaction_sender
    return out


def compute_lxmf_conversation_unread_from_latest_row(row, *, require_user_facing=False):
    """Return whether the conversation row should appear as unread.

    Uses ``lxmf_conversation_read_state.last_read_at`` only. The latest message
    must be incoming; outbound-only threads are not unread (matches
    ``filter_unread`` in ``MessageHandler.get_conversations``).

    When ``require_user_facing`` is True, the row's latest message must also be
    user-facing (i.e. not a bare reaction / telemetry / icon-only payload).
    Used by the notification bell so silent system messages do not raise the
    unread badge.
    """
    from datetime import UTC, datetime

    if not row.get("is_incoming"):
        return False
    if require_user_facing and not is_user_facing_lxmf_payload(
        row.get("fields"),
        row.get("content"),
        row.get("title"),
    ):
        return False
    last_read_at_raw = row.get("last_read_at")
    if not last_read_at_raw:
        return True
    last_read_at = datetime.fromisoformat(last_read_at_raw)
    if last_read_at.tzinfo is None:
        last_read_at = last_read_at.replace(tzinfo=UTC)
    return row["timestamp"] > last_read_at.timestamp()
