import base64
import contextlib
import json
import signal
import threading

import LXMF
import RNS.vendor.umsgpack as msgpack
from LXMF import LXMRouter


def create_lxmf_router(identity, storagepath, propagation_cost=None):
    """Construct an ``LXMF.LXMRouter`` without signal-handler crashes off the main thread.

    ``signal.signal`` only works on the main thread; on workers it is temporarily
    replaced with a no-op while the router is created.
    """
    if propagation_cost is None:
        propagation_cost = 0

    if threading.current_thread() != threading.main_thread():
        original_signal = signal.signal
        try:
            signal.signal = lambda s, h: None
            return LXMF.LXMRouter(
                identity=identity,
                storagepath=storagepath,
                propagation_cost=propagation_cost,
            )
        finally:
            signal.signal = original_signal
    else:
        return LXMF.LXMRouter(
            identity=identity,
            storagepath=storagepath,
            propagation_cost=propagation_cost,
        )


def parse_bool_query_param(value: str | None) -> bool:
    if value is None:
        return False
    value = value.lower()
    return value in {"1", "true", "yes", "on"}


def message_fields_have_attachments(fields_json: str | None):
    if not fields_json:
        return False
    try:
        fields = json.loads(fields_json)
    except Exception:
        return False
    if not isinstance(fields, dict):
        return False
    if "image" in fields or "audio" in fields:
        return True
    if "file_attachments" in fields and isinstance(
        fields["file_attachments"],
        list,
    ):
        return len(fields["file_attachments"]) > 0
    return False


def has_attachments(lxmf_fields: dict) -> bool:
    try:
        if LXMF.FIELD_FILE_ATTACHMENTS in lxmf_fields:
            return len(lxmf_fields[LXMF.FIELD_FILE_ATTACHMENTS]) > 0
        if LXMF.FIELD_IMAGE in lxmf_fields:
            return True
        if LXMF.FIELD_AUDIO in lxmf_fields:
            return True
        return False
    except Exception:
        return False


def convert_propagation_node_state_to_string(state):
    state_map = {
        LXMRouter.PR_IDLE: "idle",
        LXMRouter.PR_PATH_REQUESTED: "path_requested",
        LXMRouter.PR_LINK_ESTABLISHING: "link_establishing",
        LXMRouter.PR_LINK_ESTABLISHED: "link_established",
        LXMRouter.PR_REQUEST_SENT: "request_sent",
        LXMRouter.PR_RECEIVING: "receiving",
        LXMRouter.PR_RESPONSE_RECEIVED: "response_received",
        LXMRouter.PR_COMPLETE: "complete",
        LXMRouter.PR_NO_PATH: "no_path",
        LXMRouter.PR_LINK_FAILED: "link_failed",
        LXMRouter.PR_TRANSFER_FAILED: "transfer_failed",
        LXMRouter.PR_NO_IDENTITY_RCVD: "no_identity_received",
        LXMRouter.PR_NO_ACCESS: "no_access",
        LXMRouter.PR_FAILED: "failed",
    }

    if state in state_map:
        return state_map[state]
    return "unknown"


def convert_db_favourite_to_dict(favourite):
    created_at = str(favourite["created_at"])
    if created_at and "+" not in created_at and "Z" not in created_at:
        created_at += "Z"

    updated_at = str(favourite["updated_at"])
    if updated_at and "+" not in updated_at and "Z" not in updated_at:
        updated_at += "Z"

    return {
        "id": favourite["id"],
        "destination_hash": favourite["destination_hash"],
        "display_name": favourite["display_name"],
        "aspect": favourite["aspect"],
        "created_at": created_at,
        "updated_at": updated_at,
    }


def parse_lxmf_display_name(
    app_data_base64: str | bytes | None,
    default_value: str | None = "Anonymous Peer",
):
    if app_data_base64 is None:
        return default_value

    try:
        if isinstance(app_data_base64, bytes):
            app_data_bytes = app_data_base64
        else:
            app_data_bytes = base64.b64decode(app_data_base64)

        # Try manual parsing first to avoid LXMF library call.
        if len(app_data_bytes) > 0:
            if (
                app_data_bytes[0] >= 0x90 and app_data_bytes[0] <= 0x9F
            ) or app_data_bytes[0] == 0xDC:
                with contextlib.suppress(Exception):
                    peer_data = msgpack.unpackb(app_data_bytes)
                    if isinstance(peer_data, list) and len(peer_data) >= 1:
                        dn = peer_data[0]
                        if dn is not None:
                            if isinstance(dn, bytes):
                                return dn.decode("utf-8", errors="replace")
                            return str(dn)

        # If manual parsing didn't work, try using the library as a fallback.
        with contextlib.suppress(AttributeError, Exception):
            display_name = LXMF.display_name_from_app_data(app_data_bytes)
            if display_name is not None:
                return display_name
    except Exception as e:
        print(f"Failed to parse LXMF display name: {e}")

    return default_value


def parse_lxmf_stamp_cost(app_data_base64: str | bytes | None):
    if app_data_base64 is None:
        return None

    try:
        if isinstance(app_data_base64, bytes):
            app_data_bytes = app_data_base64
        else:
            app_data_bytes = base64.b64decode(app_data_base64)

        return LXMF.stamp_cost_from_app_data(app_data_bytes)
    except Exception as e:
        print(f"Failed to parse LXMF stamp cost: {e}")
        return None


def parse_nomadnetwork_node_display_name(
    app_data_base64: str | bytes | None,
    default_value: str | None = "Anonymous Node",
):
    if app_data_base64 is None:
        return default_value

    try:
        if isinstance(app_data_base64, bytes):
            app_data_bytes = app_data_base64
        else:
            app_data_bytes = base64.b64decode(app_data_base64)

        return app_data_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Failed to parse NomadNetwork display name: {e}")
        return default_value


def parse_lxmf_propagation_node_app_data(app_data_base64: str | bytes | None):
    if app_data_base64 is None:
        return None

    try:
        if isinstance(app_data_base64, bytes):
            app_data_bytes = app_data_base64
        else:
            app_data_bytes = base64.b64decode(app_data_base64)

        data = msgpack.unpackb(app_data_bytes)

        if not isinstance(data, list) or len(data) < 4:
            return None

        return {
            "enabled": bool(data[2]) if data[2] is not None else False,
            "timebase": int(data[1]) if data[1] is not None else 0,
            "per_transfer_limit": int(data[3]) if data[3] is not None else 0,
        }
    except Exception as e:
        print(f"Failed to parse LXMF propagation node app data: {e}")
        return None


def normalize_hex_identifier(value: str | None) -> str:
    """Return lowercase hex digits only (strips UUID hyphens, colons, whitespace)."""
    if not value or not isinstance(value, str):
        return ""
    return "".join(c for c in value.strip().lower() if c in "0123456789abcdef")


def hex_identifier_to_bytes(value: str | None) -> bytes | None:
    """Parse a hex identity or hash string for ``bytes.fromhex`` (tolerates UUID-style separators)."""
    h = normalize_hex_identifier(value)
    if not h or len(h) % 2:
        return None
    try:
        return bytes.fromhex(h)
    except ValueError:
        return None
