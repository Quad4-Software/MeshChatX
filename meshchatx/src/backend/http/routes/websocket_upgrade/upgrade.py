# SPDX-License-Identifier: 0BSD
"""HTTP routes: websocket_upgrade/upgrade."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.websocket_upgrade._names import *  # noqa: F403


def register_websocket_upgrade_upgrade_routes(routes: Any, app: Any) -> None:
    # handle websocket clients

    @routes.get("/ws")
    async def ws(request):
        forbidden = _reject_forbidden_ws_origin(app, request)
        if forbidden is not None:
            return forbidden
        forbidden_session = await _reject_forbidden_ws_session(app, request)
        if forbidden_session is not None:
            return forbidden_session
        max_clients = int(getattr(app, "max_websocket_clients", 64) or 64)
        if len(app.websocket_clients) >= max_clients:
            return web.json_response(
                {"error": "Too many websocket clients"},
                status=503,
            )

        # Control + chunked Nomad frames. Whole-file success under the Nomad
        # app cap still fits (10 MiB raw + base64) under 50 MiB legacy until
        # Phase 4 fully switches large transfers to chunks only.
        max_msg = int(
            getattr(app, "websocket_max_msg_size", None) or (50 * 1024 * 1024),
        )
        websocket_response = web.WebSocketResponse(
            max_msg_size=max_msg,
        )
        await websocket_response.prepare(request)
        # aiohttp WebSocketResponse does not expose .request, so keep it for
        # session checks on authenticated mutators (nomadnet downloads, etc).
        websocket_response._meshchatx_request = request
        init_client_runtime(websocket_response)

        # add client to connected clients list
        app.websocket_clients.append(websocket_response)
        session = app.active_sessions.add(
            ip=request.remote,
            user_agent=request.headers.get("User-Agent"),
        )
        websocket_response._meshchatx_session_id = session["id"]

        # send config to all clients
        await app.send_config_to_websocket_clients()
        await app.send_active_sessions_to_websocket_clients()

        # handle websocket messages until disconnected
        async for msg in websocket_response:
            message = cast("WSMessage", msg)
            if message.type == WSMsgType.TEXT:
                touch_client_activity(websocket_response)
                try:
                    data = json.loads(message.data)
                except Exception as e:
                    print("failed to process client message")
                    print(e)
                    await send_ws_error(
                        websocket_response,
                        message="Invalid JSON",
                        code="invalid_json",
                    )
                    continue
                counters = getattr(app, "ws_counters", None)
                if counters is not None:
                    counters.msgs_in += 1
                bucket = get_client_bucket(websocket_response)
                msg_type = data.get("type") if isinstance(data, dict) else None
                cost = message_rate_cost(
                    msg_type if isinstance(msg_type, str) else None
                )
                if not bucket.consume(cost):
                    if counters is not None:
                        counters.rate_limit_hits += 1
                    strikes = int(
                        getattr(websocket_response, "_meshchatx_rate_strikes", 0) or 0,
                    )
                    strikes += 1
                    websocket_response._meshchatx_rate_strikes = strikes
                    await send_ws_error(
                        websocket_response,
                        message="Rate limit exceeded",
                        code="rate_limited",
                        request_id=data.get("request_id")
                        if isinstance(data, dict)
                        else None,
                        retry_after=WS_RATE_RETRY_AFTER_SEC,
                    )
                    if strikes >= WS_RATE_ABUSE_STRIKES:
                        await websocket_response.close()
                        break
                    continue
                websocket_response._meshchatx_rate_strikes = 0
                try:
                    await app.on_websocket_data_received(websocket_response, data)
                except Exception as e:
                    print("failed to process client message")
                    print(e)
                    await send_ws_error(
                        websocket_response,
                        message="Handler failed",
                        code="handler_failed",
                        request_id=data.get("request_id")
                        if isinstance(data, dict)
                        else None,
                    )
            elif message.type == WSMsgType.BINARY:
                touch_client_activity(websocket_response)
                try:
                    await app.on_websocket_binary_received(
                        websocket_response,
                        message.data,
                    )
                except Exception as e:
                    print("failed to process binary client message")
                    print(e)
            elif message.type == WSMsgType.ERROR:
                print(f"ws connection error {websocket_response.exception()}")

            if client_is_idle(websocket_response):
                counters = getattr(app, "ws_counters", None)
                if counters is not None:
                    counters.idle_closes += 1
                try:
                    await websocket_response.close()
                except Exception:
                    pass
                break

        # websocket closed
        try:
            app.websocket_clients.remove(websocket_response)
        except ValueError:
            pass
        app._detach_active_session(websocket_response)
        app._cancel_rns_link_tasks_for_client(websocket_response)
        await app.send_active_sessions_to_websocket_clients()

        return websocket_response

    @routes.get("/ws/telephone/audio")
    async def telephone_audio_ws(request):
        forbidden = _reject_forbidden_ws_origin(app, request)
        if forbidden is not None:
            return forbidden
        forbidden_session = await _reject_forbidden_ws_session(app, request)
        if forbidden_session is not None:
            return forbidden_session
        websocket_response = web.WebSocketResponse(
            # Cap well above a normal PCM frame (tens of KB) but far below prior 5 MiB.
            max_msg_size=256 * 1024,
        )
        await websocket_response.prepare(request)
        init_client_runtime(websocket_response)

        if getattr(app, "demo_mode", False):
            await websocket_response.send_str(
                json.dumps(
                    {
                        "type": "error",
                        "message": "Demo mode is read-only",
                        "code": "demo_readonly",
                    },
                ),
            )
            await websocket_response.close()
            return websocket_response

        # Chaquopy Android and headless/web deployments have no usable LXST
        # host audio device, so always allow the websocket bridge.
        web_audio_allowed = (
            app.web_audio_bridge.config_enabled() or app.web_audio_required()
        )
        if not web_audio_allowed:
            await websocket_response.send_str(
                json.dumps(
                    {"type": "error", "message": "Web audio is disabled in config"},
                ),
            )
            await websocket_response.close()
            return websocket_response

        await app.web_audio_bridge.send_status(websocket_response)
        attached = app.web_audio_bridge.attach_client(websocket_response)
        if not attached:
            await websocket_response.send_str(
                json.dumps(
                    {"type": "error", "message": "No active call to attach"},
                ),
            )

        async for msg in websocket_response:
            message = cast("WSMessage", msg)
            touch_client_activity(websocket_response)
            if message.type == WSMsgType.BINARY:
                # Only accept PCM after a successful attach for this socket.
                if websocket_response in app.web_audio_bridge.clients:
                    app.web_audio_bridge.push_client_frame(message.data)
            elif message.type == WSMsgType.TEXT:
                try:
                    data = json.loads(message.data)
                    if data.get("type") == "attach":
                        app.web_audio_bridge.attach_client(websocket_response)
                    elif data.get("type") == "ping":
                        await websocket_response.send_str(
                            json.dumps({"type": "pong"}),
                        )
                except Exception as e:
                    logging.exception(
                        f"Error processing websocket text message: {e}",
                    )
            elif message.type == WSMsgType.ERROR:
                print(f"telephone audio ws error {websocket_response.exception()}")

        app.web_audio_bridge.detach_client(websocket_response)
        return websocket_response
