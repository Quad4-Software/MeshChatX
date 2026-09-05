# SPDX-License-Identifier: 0BSD

"""LXMF constants and imports."""


# ruff: noqa: F401

import base64
import json

import LXMF

from meshchatx.src.backend.meshchat_utils import (
    parse_lxmf_audio_field_value,
    parse_lxmf_file_attachments_field_value,
    parse_lxmf_image_field_value,
)
from meshchatx.src.backend.telemetry_utils import Telemeter

# MeshChatX app extensions (field 16). not used for LXMF-standard reactions.
LXMF_APP_EXTENSIONS_FIELD = 16

# LXMF reply / reaction field standards (see LXMF.py FIELD_REPLY_* / FIELD_REACTION)
FIELD_REPLY_TO = getattr(LXMF, "FIELD_REPLY_TO", 0x30)
FIELD_REPLY_QUOTE = getattr(LXMF, "FIELD_REPLY_QUOTE", 0x31)
FIELD_REACTION = getattr(LXMF, "FIELD_REACTION", 0x40)
REACTION_TO = getattr(LXMF, "REACTION_TO", 0x00)
REACTION_CONTENT = getattr(LXMF, "REACTION_CONTENT", 0x01)

# Raw LXMF integer field identifiers used when classifying "user-facing" payloads
LXMF_FILE_ATTACHMENTS_FIELD = LXMF.FIELD_FILE_ATTACHMENTS
LXMF_IMAGE_FIELD = LXMF.FIELD_IMAGE
LXMF_AUDIO_FIELD = LXMF.FIELD_AUDIO
