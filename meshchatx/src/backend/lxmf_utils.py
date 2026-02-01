import base64
import json

import LXMF

from meshchatx.src.backend.telemetry_utils import Telemeter


def convert_lxmf_message_to_dict(
    lxmf_message: LXMF.LXMessage,
    include_attachments: bool = True,
    reticulum=None,
):
    # handle fields
    fields = {}
    message_fields = lxmf_message.get_fields()
    for field_type in message_fields:
        value = message_fields[field_type]

        # handle file attachments field
        if field_type == LXMF.FIELD_FILE_ATTACHMENTS:
            # process file attachments
            file_attachments = []
            for file_attachment in value:
                file_name = file_attachment[0]
                file_data = file_attachment[1]
                file_bytes = None
                if include_attachments:
                    file_bytes = base64.b64encode(file_data).decode(
                        "utf-8",
                    )

                file_attachments.append(
                    {
                        "file_name": file_name,
                        "file_size": len(file_data),
                        "file_bytes": file_bytes,
                    },
                )

            # add to fields
            fields["file_attachments"] = file_attachments

        # handle image field
        if field_type == LXMF.FIELD_IMAGE:
            image_type = value[0]
            image_data = value[1]
            image_bytes = None
            if include_attachments:
                image_bytes = base64.b64encode(image_data).decode("utf-8")

            fields["image"] = {
                "image_type": image_type,
                "image_size": len(image_data),
                "image_bytes": image_bytes,
            }

        # handle audio field
        if field_type == LXMF.FIELD_AUDIO:
            audio_mode = value[0]
            audio_data = value[1]
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

    return {
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
    }


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

    return {
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
        "created_at": created_at,
        "updated_at": updated_at,
    }
