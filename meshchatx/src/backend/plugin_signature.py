# SPDX-License-Identifier: 0BSD

"""Canonical plugin payloads and signature verification for ZIP/dir/WASM."""

from __future__ import annotations

import io
import os
import zipfile
from collections.abc import Iterable

from meshchatx.src.backend.plugin_rsg import SignatureInfo, verify_rsg_payload

PRIMARY_SIGNATURE_FILE = "meshchatx.plugin.rsg"
SIGNATURE_FILE_NAMES = (PRIMARY_SIGNATURE_FILE,)
FIXED_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def is_signature_basename(name: str) -> bool:
    base = os.path.basename(name.replace("\\", "/"))
    return base in SIGNATURE_FILE_NAMES


def build_canonical_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(entries.keys()):
            info = zipfile.ZipInfo(filename=name)
            info.date_time = FIXED_ZIP_DATE_TIME
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, entries[name])
    return buf.getvalue()


def canonical_dir_payload(directory: str) -> bytes:
    entries: dict[str, bytes] = {}
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            path = os.path.join(root, filename)
            rel = os.path.relpath(path, directory).replace("\\", "/")
            if is_signature_basename(rel):
                continue
            with open(path, "rb") as handle:
                entries[rel] = handle.read()
    return build_canonical_zip(entries)


def canonical_zip_payload_from_bytes(payload: bytes) -> bytes:
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            clean = os.path.normpath(info.filename.replace("\\", "/")).replace(
                "\\",
                "/",
            )
            if clean in {"", "."}:
                continue
            if clean.startswith("../") or clean.startswith("/"):
                raise ValueError(f"zip path traversal: {info.filename}")
            if is_signature_basename(clean):
                continue
            entries[clean] = archive.read(info.filename)
    return build_canonical_zip(entries)


def find_signature_in_dir(directory: str) -> bytes | None:
    for name in SIGNATURE_FILE_NAMES:
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                return handle.read()
    return None


def verify_dir_signature(directory: str) -> SignatureInfo:
    rsg_data = find_signature_in_dir(directory)
    if rsg_data is None:
        return SignatureInfo()
    try:
        payload = canonical_dir_payload(directory)
    except Exception as exc:
        return SignatureInfo(present=True, error=str(exc))
    return verify_rsg_payload(rsg_data, payload)


def verify_zip_signature(payload: bytes) -> SignatureInfo:
    rsg_data = None
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for info in archive.infolist():
                clean = os.path.normpath(info.filename.replace("\\", "/")).replace(
                    "\\",
                    "/",
                )
                if is_signature_basename(clean):
                    rsg_data = archive.read(info.filename)
                    break
        if not rsg_data:
            return SignatureInfo()
        canonical = canonical_zip_payload_from_bytes(payload)
    except Exception as exc:
        return SignatureInfo(present=True, error=str(exc))
    return verify_rsg_payload(rsg_data, canonical)


def verify_wasm_signature(data: bytes) -> SignatureInfo:
    from meshchatx.src.backend.plugin_wasm_bundle import (
        parse_wasm_bundle,
        wasm_payload_without_signature,
    )

    try:
        bundle = parse_wasm_bundle(data)
    except Exception as exc:
        return SignatureInfo(error=str(exc))
    if not bundle.signature:
        return SignatureInfo()
    try:
        payload = wasm_payload_without_signature(data)
    except Exception as exc:
        return SignatureInfo(present=True, error=str(exc))
    return verify_rsg_payload(bundle.signature, payload)


def verify_file_bytes_signature(
    rsg_data: bytes | None,
    payload: bytes,
) -> SignatureInfo:
    if not rsg_data:
        return SignatureInfo()
    return verify_rsg_payload(rsg_data, payload)


def verify_py_signature(py_path: str) -> SignatureInfo:
    rsg_path = py_path + ".rsg"
    if not os.path.isfile(rsg_path):
        return SignatureInfo()
    with open(py_path, "rb") as handle:
        message = handle.read()
    with open(rsg_path, "rb") as handle:
        rsg_data = handle.read()
    return verify_rsg_payload(rsg_data, message)


def require_valid_signature(info: SignatureInfo) -> None:
    if not info.present:
        return
    if info.valid:
        return
    if info.error:
        raise ValueError(f"invalid plugin signature: {info.error}")
    raise ValueError("invalid plugin signature")


def write_dir_signature(directory: str, rsg_data: bytes) -> None:
    if not rsg_data:
        raise ValueError("signature is required")
    path = os.path.join(directory, PRIMARY_SIGNATURE_FILE)
    with open(path, "wb") as handle:
        handle.write(rsg_data)


def embed_signature_in_zip_bytes(payload: bytes, rsg_data: bytes) -> bytes:
    if not rsg_data:
        raise ValueError("signature is required")
    entries: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            clean = os.path.normpath(info.filename.replace("\\", "/")).replace(
                "\\",
                "/",
            )
            if clean in {"", "."} or is_signature_basename(clean):
                continue
            entries[clean] = archive.read(info.filename)
    entries[PRIMARY_SIGNATURE_FILE] = rsg_data
    return build_canonical_zip(entries)


def enrich_signature_with_trust(info: SignatureInfo, lookup_trusted) -> SignatureInfo:
    if not info.valid or not info.signer:
        return info
    name, trusted = lookup_trusted(info.signer)
    return SignatureInfo(
        present=info.present,
        valid=info.valid,
        signer=info.signer,
        signer_name=name or info.signer_name,
        trusted=trusted,
        error=info.error,
    )


def collect_signature_file_names() -> Iterable[str]:
    return SIGNATURE_FILE_NAMES
