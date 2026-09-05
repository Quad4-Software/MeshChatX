# SPDX-License-Identifier: 0BSD

"""Typed containers for LXMF attachment payloads used across the backend."""

from __future__ import annotations

import os


class LxmfAudioField:
    """In-memory LXMF audio attachment (mode code plus raw bytes)."""

    __slots__ = ("audio_mode", "audio_bytes")

    def __init__(self, audio_mode: int, audio_bytes: bytes) -> None:
        self.audio_mode = audio_mode
        self.audio_bytes = audio_bytes


class LxmfImageField:
    """In-memory LXMF image attachment (type string plus raw bytes)."""

    __slots__ = ("image_type", "image_bytes")

    def __init__(self, image_type: str, image_bytes: bytes) -> None:
        self.image_type = image_type
        self.image_bytes = image_bytes


def _safe_attachment_basename(file_name: str) -> str:
    """Return a basename safe to publish to mesh peers (no host paths)."""
    raw = file_name if isinstance(file_name, str) else ""
    base = os.path.basename(raw.replace("\\", "/").strip())
    if not base or base in (".", ".."):
        return "attachment"
    return base


class LxmfFileAttachment:
    """Single file attachment with a peer-visible basename and bytes."""

    __slots__ = ("file_name", "file_bytes")

    def __init__(self, file_name: str, file_bytes: bytes) -> None:
        self.file_name = _safe_attachment_basename(file_name)
        self.file_bytes = file_bytes


class LxmfFileAttachmentsField:
    """List wrapper for multiple LXMF file attachments."""

    __slots__ = ("file_attachments",)

    def __init__(self, file_attachments: list[LxmfFileAttachment]) -> None:
        self.file_attachments = file_attachments
