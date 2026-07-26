# SPDX-License-Identifier: 0BSD
"""WebSocket inbound dispatch extracted from ReticulumMeshChat."""

from __future__ import annotations

from meshchatx.src.backend.http.live_names import inject_meshchat_names
from meshchatx.src.backend.demo_mode import demo_mode_blocks_ws_type
from meshchatx.src.backend.http.meshchat_names import (  # noqa: F401
    AsyncUtils,
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


def _ensure_meshchat_namespace() -> None:
    global _NS_READY
    if _NS_READY:
        return
    inject_meshchat_names(globals())
    for mod_name in _HANDLER_MODULES:
        mod = __import__(mod_name, fromlist=["*"])
        inject_meshchat_names(mod.__dict__)
    _NS_READY = True


async def dispatch_websocket_data(app, client, data):
    _ensure_meshchat_namespace()
    # get type from client data
    if not isinstance(data, dict):
        return

    _type = data.get("type")
    if not _type:
        return

    if demo_mode_blocks_ws_type(app, _type):
        logger.warning("Rejected WebSocket mutator in demo mode: %s", _type)
        AsyncUtils.run_async(
            client.send_str(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Demo mode is read-only",
                        "code": "demo_readonly",
                    },
                ),
            ),
        )
        return

    if websocket_type_requires_auth(_type):
        if not await app._websocket_session_authorized(client):
            logger.warning("Rejected unauthorized WebSocket mutator: %s", _type)
            AsyncUtils.run_async(
                client.send_str(
                    json.dumps(
                        {
                            "type": "error",
                            "message": "Authentication required",
                        },
                    ),
                ),
            )
            return

    handler = WS_HANDLERS.get(_type)
    if handler is None:
        print("unhandled client message type: " + _type)
        return
    await handler(app, client, data)
