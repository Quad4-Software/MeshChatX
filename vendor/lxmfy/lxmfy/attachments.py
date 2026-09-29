from dataclasses import dataclass
from enum import IntEnum

import LXMF


class AttachmentType(IntEnum):
    """Enumerates the different types of attachments supported.

    FILE: Represents a generic file attachment.
    IMAGE: Represents an image attachment.
    AUDIO: Represents an audio attachment.
    """

    FILE = 0x05
    IMAGE = 0x06
    AUDIO = 0x07


@dataclass
class Attachment:
    """Represents a generic attachment.

    Attributes:
        type: The type of the attachment (AttachmentType).
        name: The name of the attachment.
        data: The binary data of the attachment.
        format: Optional format specifier (e.g., "png" for images).

    """

    type: AttachmentType
    name: str
    data: bytes
    format: str | None = None


@dataclass
class IconAppearance:
    """Represents LXMF icon appearance data."""

    icon_name: str
    fg_color: bytes  # Must be 3 bytes, e.g., b'\xff\x00\x00' for red
    bg_color: bytes  # Must be 3 bytes


def create_file_attachment(filename: str, data: bytes) -> list:
    """Create a file attachment list."""
    return [filename, data]


def create_image_attachment(image_format: str, data: bytes) -> list:
    """Create an image attachment list."""
    return [image_format, data]


def create_audio_attachment(mode: int, data: bytes) -> list:
    """Create an audio attachment list."""
    return [mode, data]


def pack_attachment(attachment: Attachment) -> dict:
    """Packs an Attachment object into a dictionary suitable for LXMF transmission.

    Args:
        attachment: The Attachment object to pack.

    Returns:
        A dictionary containing the attachment data, formatted according to the
        attachment type.

    Raises:
        ValueError: If the attachment type is not supported.

    """
    if attachment.type == AttachmentType.FILE:
        return {
            LXMF.FIELD_FILE_ATTACHMENTS: [
                create_file_attachment(attachment.name, attachment.data),
            ],
        }
    if attachment.type == AttachmentType.IMAGE:
        return {
            LXMF.FIELD_IMAGE: create_image_attachment(
                attachment.format or "webp",
                attachment.data,
            ),
        }
    if attachment.type == AttachmentType.AUDIO:
        try:
            mode = int(attachment.format) if attachment.format is not None else 0
        except (ValueError, TypeError):
            mode = 0

        return {
            LXMF.FIELD_AUDIO: create_audio_attachment(
                mode,
                attachment.data,
            ),
        }
    raise ValueError(f"Unsupported attachment type: {attachment.type}")


def pack_icon_appearance_field(appearance: IconAppearance) -> dict:
    """Packs an IconAppearance object into a dictionary suitable for LXMF transmission.

    Args:
        appearance: The IconAppearance object to pack.

    Returns:
        A dictionary containing the icon appearance data.

    Raises:
        ValueError: If fg_color or bg_color are not 3 bytes.

    """
    if not (isinstance(appearance.fg_color, bytes) and len(appearance.fg_color) == 3):
        raise ValueError("fg_color must be 3 bytes (e.g., b'\\xff\\x00\\x00')")
    if not (isinstance(appearance.bg_color, bytes) and len(appearance.bg_color) == 3):
        raise ValueError("bg_color must be 3 bytes (e.g., b'\\x00\\xff\\x00')")

    return {
        LXMF.FIELD_ICON_APPEARANCE: [
            appearance.icon_name,
            appearance.fg_color,
            appearance.bg_color,
        ],
    }
