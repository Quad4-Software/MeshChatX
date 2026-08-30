# SPDX-License-Identifier: 0BSD
"""WebSocket inbound dispatch extracted from ReticulumMeshChat."""

from __future__ import annotations

from meshchatx.src.backend.demo_mode import demo_mode_blocks_ws_type
from meshchatx.src.backend.http.live_names import inject_meshchat_names
from meshchatx.src.backend.http.meshchat_names import (
    json,
    logger,
    websocket_type_requires_auth,
)
from meshchatx.src.backend.http.ws.handlers_core import HANDLERS as _CORE_HANDLERS
from meshchatx.src.backend.http.ws.handlers_lxmf import HANDLERS as _LXMF_HANDLERS
from meshchatx.src.backend.http.ws.handlers_nomad import HANDLERS as _NOMAD_HANDLERS
from meshchatx.src.backend.http.ws.handlers_rns_link import (
    HANDLERS as _RNS_LINK_HANDLERS,
)
from meshchatx.src.backend.websocket_runtime import (
    apply_subscribe,
    send_ws_error,
    touch_client_activity,
    validate_ws_envelope,
)

_NS_READY = False

WS_HANDLERS = {}
WS_HANDLERS.update(_CORE_HANDLERS)
WS_HANDLERS.update(_NOMAD_HANDLERS)
WS_HANDLERS.update(_LXMF_HANDLERS)
WS_HANDLERS.update(_RNS_LINK_HANDLERS)

_HANDLER_MODULES = (
    "meshchatx.src.backend.http.ws.handlers_core",
    "meshchatx.src.backend.http.ws.handlers_nomad",
    "meshchatx.src.backend.http.ws.handlers_lxmf",
    "meshchatx.src.backend.http.ws.handlers_rns_link",
)

_KNOWN_TYPES = frozenset(WS_HANDLERS.keys()) | frozenset(
    {
        "ws.subscribe",
        "ws.unsubscribe",
        "sync.subscribe",
        "ws.caps",
    },
)


def _ensure_meshchat_namespace() -> None:
    global _NS_READY
    if _NS_READY:
        return
    inject_meshchat_names(globals())
    for mod_name in _HANDLER_MODULES:
        mod = __import__(mod_name, fromlist=["*"])
        inject_meshchat_names(mod.__dict__)
    _NS_READY = True


async def _handle_runtime_control(app, client, data, msg_type: str) -> bool:
    """Handle subscribe / caps / sync. Returns True if handled."""
    if msg_type == "ws.subscribe":
        changed = apply_subscribe(client, data.get("topics"), subscribe=True)
        await client.send_str(
            json.dumps(
                {
                    "type": "ws.subscribe",
                    "status": "success",
                    "topics": sorted(
                        getattr(client, "_meshchatx_ws_topics", []) or [],
                    ),
                    "changed": changed,
                    "request_id": data.get("request_id"),
                },
            ),
        )
        return True
    if msg_type == "ws.unsubscribe":
        changed = apply_subscribe(client, data.get("topics"), subscribe=False)
        await client.send_str(
            json.dumps(
                {
                    "type": "ws.unsubscribe",
                    "status": "success",
                    "topics": sorted(
                        getattr(client, "_meshchatx_ws_topics", []) or [],
                    ),
                    "changed": changed,
                    "request_id": data.get("request_id"),
                },
            ),
        )
        return True
    if msg_type == "sync.subscribe":
        since = data.get("since_seq")
        seq_state = getattr(app, "ws_seq_state", None)
        if seq_state is None:
            hint = {"status": "ok", "resync": False}
        else:
            hint = seq_state.gap_hint(int(since or 0))
        await client.send_str(
            json.dumps(
                {
                    "type": "sync.subscribe",
                    "request_id": data.get("request_id"),
                    **hint,
                },
            ),
        )
        return True
    if msg_type == "ws.caps":
        if data.get("binary_rns_link") is True:
            client._meshchatx_binary_rns_link = True
        await client.send_str(
            json.dumps(
                {
                    "type": "ws.caps",
                    "status": "success",
                    "binary_rns_link": bool(
                        getattr(client, "_meshchatx_binary_rns_link", False),
                    ),
                    "request_id": data.get("request_id"),
                },
            ),
        )
        return True
    return False


async def dispatch_websocket_data(app, client, data):
    _ensure_meshchat_namespace()
    touch_client_activity(client)

    msg_type, envelope_err = validate_ws_envelope(data, _KNOWN_TYPES)
    if envelope_err:
        await send_ws_error(
            client,
            message="Invalid message",
            code=envelope_err,
            request_id=data.get("request_id") if isinstance(data, dict) else None,
        )
        return
    if not msg_type:
        return

    if await _handle_runtime_control(app, client, data, msg_type):
        return

    if demo_mode_blocks_ws_type(app, msg_type):
        logger.warning("Rejected WebSocket mutator in demo mode: %s", msg_type)
        await send_ws_error(
            client,
            message="Demo mode is read-only",
            code="demo_readonly",
            request_id=data.get("request_id") if isinstance(data, dict) else None,
        )
        return

    if websocket_type_requires_auth(msg_type):
        if not await app._websocket_session_authorized(client):
            logger.warning("Rejected unauthorized WebSocket mutator: %s", msg_type)
            await send_ws_error(
                client,
                message="Authentication required",
                code="auth_required",
                request_id=data.get("request_id") if isinstance(data, dict) else None,
            )
            return

    handler = WS_HANDLERS.get(msg_type)
    if handler is None:
        await send_ws_error(
            client,
            message="Unhandled message type",
            code="unhandled_type",
            request_id=data.get("request_id") if isinstance(data, dict) else None,
        )
        return
    try:
        await handler(app, client, data)
    except Exception:
        logger.exception("WebSocket handler failed for %s", msg_type)
        await send_ws_error(
            client,
            message="Handler failed",
            code="handler_failed",
            request_id=data.get("request_id") if isinstance(data, dict) else None,
        )
