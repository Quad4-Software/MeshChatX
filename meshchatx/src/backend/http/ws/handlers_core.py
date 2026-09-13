# SPDX-License-Identifier: 0BSD
"""WebSocket handlers: handlers_core."""

from __future__ import annotations

import json
import traceback

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.constants import WsInboundType
from meshchatx.src.backend.websocket_config_guard import (
    sanitize_websocket_config_update,
)


async def handle_ping(app, client, data):
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "pong",
                },
            ),
        ),
    )

    # handle updating config


async def handle_config_set(app, client, data):
    from meshchatx.src.backend.websocket_runtime import send_ws_error

    config = sanitize_websocket_config_update(data.get("config"))
    request_id = data.get("request_id")
    rid = {}
    if request_id is not None:
        rid["request_id"] = request_id

    try:
        await app.update_config(config)
        try:
            AsyncUtils.run_async(app.send_config_to_websocket_clients())
        except Exception as e:
            print(f"Failed to broadcast config update: {e}")
        await client.send_str(
            json.dumps(
                {
                    "type": WsInboundType.CONFIG_SET,
                    "status": "success",
                    **rid,
                },
            ),
        )
    except Exception:
        print("config.set failed:\n" + traceback.format_exc())
        await send_ws_error(
            client,
            message="Config update failed",
            code="config_set_failed",
            request_id=request_id,
        )

    # handle canceling a download


async def handle_keyboard_shortcuts_get(app, client, data):
    shortcuts = app.database.misc.get_keyboard_shortcuts(
        app.identity.hash.hex(),
    )
    rid = {}
    if data.get("request_id") is not None:
        rid["request_id"] = data.get("request_id")
    AsyncUtils.run_async(
        client.send_str(
            json.dumps(
                {
                    "type": "keyboard_shortcuts",
                    **rid,
                    "shortcuts": [
                        {
                            "action": s["action"],
                            "keys": json.loads(s["keys"]),
                        }
                        for s in shortcuts
                    ],
                },
            ),
        ),
    )

    # handle updating/upserting a keyboard shortcut


async def handle_keyboard_shortcuts_set(app, client, data):
    action = data["action"]
    keys = json.dumps(data["keys"])
    app.database.misc.upsert_keyboard_shortcut(
        app.identity.hash.hex(),
        action,
        keys,
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {
                "type": WsInboundType.KEYBOARD_SHORTCUTS_GET,
                "request_id": data.get("request_id"),
            },
        ),
    )

    # handle deleting a keyboard shortcut


async def handle_keyboard_shortcuts_delete(app, client, data):
    action = data["action"]
    app.database.misc.delete_keyboard_shortcut(
        app.identity.hash.hex(),
        action,
    )
    # notify updated
    AsyncUtils.run_async(
        app.on_websocket_data_received(
            client,
            {
                "type": WsInboundType.KEYBOARD_SHORTCUTS_GET,
                "request_id": data.get("request_id"),
            },
        ),
    )


HANDLERS = {
    WsInboundType.PING: handle_ping,
    WsInboundType.CONFIG_SET: handle_config_set,
    WsInboundType.KEYBOARD_SHORTCUTS_GET: handle_keyboard_shortcuts_get,
    WsInboundType.KEYBOARD_SHORTCUTS_SET: handle_keyboard_shortcuts_set,
    WsInboundType.KEYBOARD_SHORTCUTS_DELETE: handle_keyboard_shortcuts_delete,
}
