# SPDX-License-Identifier: 0BSD

import base64
import contextlib
import json
import math
import signal
import threading

import LXMF
import RNS.vendor.umsgpack as msgpack
from LXMF import LXMRouter


def create_lxmf_router(
    identity,
    storagepath,
    propagation_cost=None,
    max_inbound_syncs=None,
    sequential_validation=None,
    static_sequential=None,
):
    """Construct an LXMF.LXMRouter without signal-handler crashes off the main thread.

    signal.signal only works on the main thread; on workers it is temporarily
    replaced with a no-op while the router is created.
    """
    if propagation_cost is None:
        propagation_cost = 0

    kwargs = {
        "identity": identity,
        "storagepath": storagepath,
        "propagation_cost": propagation_cost,
    }
    if max_inbound_syncs is not None:
        kwargs["max_inbound_syncs"] = max_inbound_syncs
    if sequential_validation is not None:
        kwargs["sequential_validation"] = sequential_validation
    if static_sequential is not None:
        kwargs["static_sequential"] = static_sequential

    if threading.current_thread() != threading.main_thread():
        original_signal = signal.signal
        try:
            signal.signal = lambda s, h: None
            return LXMF.LXMRouter(**kwargs)
        finally:
            signal.signal = original_signal
    else:
        return LXMF.LXMRouter(**kwargs)


def list_inbound_deliveries(router) -> list[dict]:
    """Serialize active inbound LXMF delivery resources (LXMF 1.1+ / RNS 1.4+)."""
    if router is None or not hasattr(router, "inbound_resources"):
        return []
    items: list[dict] = []
    try:
        resources = router.inbound_resources() or []
    except Exception:
        return []
    for resource in resources:
        try:
            resource_hash = getattr(resource, "hash", None)
            if resource_hash is None and hasattr(resource, "get_hash"):
                resource_hash = resource.get_hash()
            if resource_hash is None:
                continue
            if isinstance(resource_hash, (bytes, bytearray)):
                hash_hex = bytes(resource_hash).hex()
            else:
                hash_hex = str(resource_hash)
            size = None
            transfer_size = None
            progress = None
            with contextlib.suppress(Exception):
                size = int(resource.get_data_size() or 0)
            with contextlib.suppress(Exception):
                transfer_size = int(resource.get_transfer_size() or 0)
            with contextlib.suppress(Exception):
                progress_raw = float(resource.get_progress() or 0.0)
                progress = max(0.0, min(100.0, progress_raw * 100.0))
            items.append(
                {
                    "hash": hash_hex,
                    "size_bytes": size,
                    "transfer_size_bytes": transfer_size,
                    "progress": progress,
                },
            )
        except Exception:
            continue
    return items


def cancel_inbound_deliveries(router, resource_hash: str | None = None) -> dict:
    """Cancel one or all active inbound LXMF delivery resources.

    Returns a result dict with ok, cancelled count, and optional error.
    """
    if router is None:
        return {"ok": False, "error": "router unavailable", "cancelled": 0}

    cleaned = str(resource_hash or "").strip().lower().replace(":", "")
    if cleaned:
        if not hasattr(router, "cancel_inbound"):
            return {
                "ok": False,
                "error": "inbound delivery cancellation is unavailable",
                "cancelled": 0,
            }
        try:
            hash_bytes = bytes.fromhex(cleaned)
        except ValueError:
            return {"ok": False, "error": "invalid resource_hash", "cancelled": 0}
        if not hash_bytes:
            return {"ok": False, "error": "invalid resource_hash", "cancelled": 0}
        try:
            ok = bool(router.cancel_inbound(hash_bytes))
        except Exception as exc:
            return {"ok": False, "error": str(exc), "cancelled": 0}
        return {
            "ok": ok,
            "cancelled": 1 if ok else 0,
            "resource_hash": cleaned,
            "error": None if ok else "resource not active",
        }

    if not hasattr(router, "cancel_all_inbound"):
        return {
            "ok": False,
            "error": "inbound delivery cancellation is unavailable",
            "cancelled": 0,
        }
    try:
        cancelled = int(router.cancel_all_inbound() or 0)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "cancelled": 0}
    return {"ok": True, "cancelled": cancelled}


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


_PROPAGATION_SYNC_TERMINAL_STATES = frozenset(
    {
        LXMRouter.PR_IDLE,
        LXMRouter.PR_COMPLETE,
        LXMRouter.PR_NO_PATH,
        LXMRouter.PR_LINK_FAILED,
        LXMRouter.PR_TRANSFER_FAILED,
        LXMRouter.PR_NO_IDENTITY_RCVD,
        LXMRouter.PR_NO_ACCESS,
        LXMRouter.PR_FAILED,
        LXMRouter.PR_PATH_TIMEOUT,
    },
)


def propagation_sync_is_terminal(state) -> bool:
    return state in _PROPAGATION_SYNC_TERMINAL_STATES


def propagation_sync_idle_like(state) -> bool:
    return state in {LXMRouter.PR_IDLE, LXMRouter.PR_COMPLETE}


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
        LXMRouter.PR_PATH_TIMEOUT: "path_timeout",
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


def parse_lxmf_icon_appearance(value):
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    icon_name, foreground, background = value[:3]
    if not isinstance(icon_name, str) or not 0 < len(icon_name) <= 64:
        return None
    if not icon_name.isprintable():
        return None
    if not all(isinstance(c, bytes) and len(c) == 3 for c in (foreground, background)):
        return None
    return icon_name, "#" + foreground.hex(), "#" + background.hex()


def lxmf_signature_validated(lxmf_message) -> bool:
    """True only when LXMF set signature_validated to the real bool True."""
    return getattr(lxmf_message, "signature_validated", False) is True


def normalize_lxmf_destination_hash(value) -> str | None:
    if isinstance(value, bytes):
        if len(value) == 0:
            return None
        return value.hex()
    if isinstance(value, str):
        h = value.strip().lower()
        return h or None
    return None


def parse_lxmf_image_field_value(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    image_type, image_data = value[0], value[1]
    if not isinstance(image_data, (bytes, bytearray)):
        return None
    if isinstance(image_type, bytes):
        image_type = image_type.decode("utf-8", errors="replace")
    if not isinstance(image_type, str) or not 0 < len(image_type) <= 32:
        return None
    if not image_type.isprintable():
        return None
    return image_type, bytes(image_data)


def parse_lxmf_audio_field_value(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    audio_mode, audio_data = value[0], value[1]
    if isinstance(audio_mode, bool) or not isinstance(audio_mode, int):
        return None
    if not isinstance(audio_data, (bytes, bytearray)):
        return None
    return audio_mode, bytes(audio_data)


def parse_lxmf_file_attachments_field_value(value):
    if not isinstance(value, list):
        return None
    attachments = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        file_name, file_data = item[0], item[1]
        if not isinstance(file_data, (bytes, bytearray)):
            continue
        if isinstance(file_name, bytes):
            file_name = file_name.decode("utf-8", errors="replace")
        if not isinstance(file_name, str) or not 0 < len(file_name) <= 255:
            continue
        if not file_name.isprintable():
            continue
        attachments.append((file_name, bytes(file_data)))
    return attachments


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
                                name = dn.decode("utf-8", errors="replace")
                            else:
                                name = str(dn)
                            return _clamp_lxmf_display_name(name)

        # If manual parsing didn't work, try using the library as a fallback.
        with contextlib.suppress(AttributeError, Exception):
            display_name = LXMF.display_name_from_app_data(app_data_bytes)
            if display_name is not None:
                return _clamp_lxmf_display_name(str(display_name))
    except Exception as e:
        print(f"Failed to parse LXMF display name: {e}")

    return default_value


_LXMF_DISPLAY_NAME_MAX_LEN = 256


def _clamp_lxmf_display_name(name: str) -> str:
    text = "".join(ch for ch in name if ch.isprintable() or ch in "\t ")
    text = text.strip()
    if not text:
        return ""
    return text[:_LXMF_DISPLAY_NAME_MAX_LEN]


def parse_lxmf_stamp_cost(app_data_base64: str | bytes | None):
    if app_data_base64 is None:
        return None

    try:
        if isinstance(app_data_base64, bytes):
            app_data_bytes = app_data_base64
        else:
            app_data_bytes = base64.b64decode(app_data_base64)

        cost = LXMF.stamp_cost_from_app_data(app_data_bytes)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            return None
        if not math.isfinite(cost):
            return None
        cost_i = int(cost)
        if cost_i < 0 or cost_i > 254:
            return None
        return cost_i
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
    """Parse a hex identity or hash string for bytes.fromhex (tolerates UUID-style separators)."""
    h = normalize_hex_identifier(value)
    if not h or len(h) % 2:
        return None
    try:
        return bytes.fromhex(h)
    except ValueError:
        return None


_IDENTITY_STORAGE_HASH_HEX_LEN = 32


def normalize_identity_storage_hash(value: str | None) -> str:
    """Return canonical 32-char hex identity directory name, or empty if invalid."""
    h = normalize_hex_identifier(value)
    if len(h) != _IDENTITY_STORAGE_HASH_HEX_LEN:
        return ""
    if hex_identifier_to_bytes(h) is None:
        return ""
    return h


_LXMF_CONTENT_HASH_HEX_LEN = 64


def normalized_meshchat_lxmf_message_hash_hex(value: str | None) -> str:
    """Return a canonical 64-char lowercase LXMF content hash, or empty if invalid."""
    if not value or not isinstance(value, str):
        return ""
    raw = value.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    if "@" in raw:
        raw = raw.split("@", 1)[1]
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    h = normalize_hex_identifier(raw)
    if len(h) != _LXMF_CONTENT_HASH_HEX_LEN:
        return ""
    if hex_identifier_to_bytes(h) is None:
        return ""
    return h


def _lxm_matches_content_hash(lxm, content_hash_bytes: bytes) -> bool:
    h = getattr(lxm, "hash", None)
    if isinstance(h, bytes) and h == content_hash_bytes:
        return True
    mid = getattr(lxm, "message_id", None)
    return isinstance(mid, bytes) and mid == content_hash_bytes


def find_lxm_by_content_hash_for_paper_uri(
    message_router,
    content_hash_bytes: bytes,
):
    """Return a live LXMessage from router outbound queues, or None.

    Paper URI generation needs packed bytes that only exist while the message is
    still in pending_outbound or pending_deferred_stamps.
    """
    if not message_router or not content_hash_bytes:
        return None
    for lxm in getattr(message_router, "pending_outbound", ()) or ():
        if _lxm_matches_content_hash(lxm, content_hash_bytes):
            return lxm
    deferred = getattr(message_router, "pending_deferred_stamps", None) or {}
    for lxm in deferred.values():
        if _lxm_matches_content_hash(lxm, content_hash_bytes):
            return lxm
    return None


def lxmf_message_try_paper_uri_string(lxm) -> tuple[str | None, str | None]:
    """Build an lxm:// Paper URI from a live message without mutating it.

    Returns (uri, None) on success, or (None, detail) on failure.
    """
    if lxm is None:
        return None, "No message"
    try:
        import copy

        dest = lxm.get_destination()
        src = lxm.get_source()
        if dest is None or src is None:
            return None, "Message is missing source or destination"
        fields = copy.deepcopy(lxm.get_fields() or {})
        content = lxm.content
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8", errors="replace")
        elif not isinstance(content, str):
            content = lxm.content_as_string() or ""
        title = lxm.title
        if isinstance(title, (bytes, bytearray)):
            title = title.decode("utf-8", errors="replace")
        elif not isinstance(title, str):
            title = lxm.title_as_string() or ""
        paper = LXMF.LXMessage(
            dest,
            src,
            content,
            title=title,
            fields=fields,
            desired_method=LXMF.LXMessage.PAPER,
        )
        uri = paper.as_uri(finalise=False)
        return uri, None
    except TypeError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def interval_action_due(
    enabled: bool,
    last_at: int | None,
    interval_seconds: int | None,
    now: float,
) -> bool:
    """Return whether a periodic action should run now.

    Used for auto-announce, propagation sync, and similar timers stored in config.
    If last_at is ahead of now (clock skew, restored DB, or bad values),
    the action is treated as due so scheduling does not stall until wall clock
    catches a corrupted future timestamp.
    """
    if not enabled:
        return False
    iv = interval_seconds if interval_seconds is not None else 0
    if iv <= 0:
        return False
    if last_at is None:
        return True
    if last_at > now:
        return True
    return now > last_at + iv
