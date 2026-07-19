"""Control-plane message encode and decode."""

from __future__ import annotations

from typing import Any

from RNS.vendor import umsgpack

MSG_FILE_LIST = "file_list"
MSG_FILE_LIST_REQUEST = "file_list_request"
MSG_FILE_REQUEST = "file_request"
MSG_DELTA_REQUEST = "delta_request"
MSG_EMPTY_FILE = "empty_file"
MSG_FILE_UPDATE = "file_update"
MSG_FILE_DELETION = "file_deletion"

KNOWN_TYPES = frozenset(
    {
        MSG_FILE_LIST,
        MSG_FILE_LIST_REQUEST,
        MSG_FILE_REQUEST,
        MSG_DELTA_REQUEST,
        MSG_EMPTY_FILE,
        MSG_FILE_UPDATE,
        MSG_FILE_DELETION,
    },
)


class ProtocolError(ValueError):
    """Raised for invalid protocol messages."""


def encode_message(payload: dict[str, Any]) -> bytes:
    if not isinstance(payload, dict) or "type" not in payload:
        raise ProtocolError("message must be a dict with type")
    return umsgpack.packb(payload)


def decode_message(raw: bytes) -> dict[str, Any]:
    data = umsgpack.unpackb(raw)
    if not isinstance(data, dict):
        raise ProtocolError("message must unpack to dict")
    msg_type = data.get("type")
    if not isinstance(msg_type, str) or msg_type not in KNOWN_TYPES:
        raise ProtocolError(f"unknown message type: {msg_type!r}")
    return data


def make_file_list(files: dict[str, dict[str, Any]], browser: bool = False) -> bytes:
    return encode_message(
        {
            "type": MSG_FILE_LIST,
            "files": files,
            "browser": bool(browser),
        },
    )


def make_file_list_request(browser: bool = False) -> bytes:
    return encode_message({"type": MSG_FILE_LIST_REQUEST, "browser": bool(browser)})


def make_file_request(path: str) -> bytes:
    return encode_message({"type": MSG_FILE_REQUEST, "path": path})


def make_delta_request(path: str, local_blocks: list[str]) -> bytes:
    return encode_message(
        {
            "type": MSG_DELTA_REQUEST,
            "path": path,
            "local_blocks": list(local_blocks),
        },
    )


def make_empty_file(path: str, file_hash: str | None) -> bytes:
    return encode_message(
        {
            "type": MSG_EMPTY_FILE,
            "path": path,
            "hash": file_hash,
        },
    )


def make_file_update(path: str, info: dict[str, Any]) -> bytes:
    return encode_message(
        {
            "type": MSG_FILE_UPDATE,
            "path": path,
            "info": info,
        },
    )


def make_file_deletion(path: str) -> bytes:
    return encode_message({"type": MSG_FILE_DELETION, "path": path})


def decode_metadata_value(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()
    return value
