# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import hashlib

from meshchatx.src.backend.plugin_signature import canonical_dir_payload

INTEGRITY_TAMPER_MESSAGE = "plugin files were modified outside MeshChatX"


def compute_dir_integrity_hash(dir_path: str) -> str:
    payload = canonical_dir_payload(dir_path)
    return hashlib.sha256(payload).hexdigest()


def verify_dir_integrity(dir_path: str, expected_hash: str) -> tuple[bool, str]:
    if not expected_hash:
        return True, ""
    current = compute_dir_integrity_hash(dir_path)
    if current != expected_hash:
        return False, current
    return True, current


def integrity_tamper_error() -> ValueError:
    return ValueError(INTEGRITY_TAMPER_MESSAGE)
