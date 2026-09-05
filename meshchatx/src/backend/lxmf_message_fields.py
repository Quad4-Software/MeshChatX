# SPDX-License-Identifier: MIT

import os


# helper class for passing around an lxmf audio field
class LxmfAudioField:
    def __init__(self, audio_mode: int, audio_bytes: bytes):
        self.audio_mode = audio_mode
        self.audio_bytes = audio_bytes


# helper class for passing around an lxmf image field
class LxmfImageField:
    def __init__(self, image_type: str, image_bytes: bytes):
        self.image_type = image_type
        self.image_bytes = image_bytes


# helper class for passing around an lxmf file attachment
class LxmfFileAttachment:
    def __init__(self, file_name: str, file_bytes: bytes):
        # Mesh peers see this name. Never publish host absolute paths.
        raw = file_name if isinstance(file_name, str) else ""
        base = os.path.basename(raw.replace("\\", "/").strip())
        if not base or base in (".", ".."):
            base = "attachment"
        self.file_name = base
        self.file_bytes = file_bytes


# helper class for passing around an lxmf file attachments field
class LxmfFileAttachmentsField:
    def __init__(self, file_attachments: list[LxmfFileAttachment]):
        self.file_attachments = file_attachments
