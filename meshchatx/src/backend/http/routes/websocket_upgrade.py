# SPDX-License-Identifier: 0BSD
"""HTTP routes: websocket_upgrade."""

from __future__ import annotations

import json
import logging
from typing import cast

from aiohttp import (
    WSMessage,
    WSMsgType,
    web,
)
from aiohttp_session import get_session

from meshchatx.src.backend.app_security_settings import get_trusted_proxy_cidrs
from meshchatx.src.backend.http.errors import (
    http_forbidden,
    http_unauthorized,
    http_unavailable,
)
from meshchatx.src.backend.websocket_config_guard import websocket_origin_allowed
from meshchatx.src.backend.websocket_runtime import (
    WS_IDLE_TIMEOUT_SEC,
    WS_RATE_ABUSE_STRIKES,
    WS_RATE_RETRY_AFTER_SEC,
    client_is_idle,
    get_client_bucket,
    init_client_runtime,
    message_rate_cost,
    send_ws_error,
    touch_client_activity,
    websocket_origin_policy_allows,
)
from meshchatx.src.path_utils import is_loopback_bind_host


async def _reject_forbidden_ws_session(app, request):
    """Defense in depth: identity-bound session when password auth is on."""
    if not getattr(app, "auth_enabled", False):
        return None
    try:
        session = await get_session(request)
    except Exception:
        return http_unauthorized("Authentication required")
    identity_hash = None
    identity = getattr(app, "identity", None)
    if identity is not None and getattr(identity, "hash", None) is not None:
        identity_hash = identity.hash.hex()
    if not (
        session.get("authenticated", False)
        and identity_hash
        and session.get("identity_hash") == identity_hash
        and app._auth_session_epoch_valid(session)
    ):
        return http_unauthorized("Authentication required")
    return None


async def _ws_rate_gate(app, websocket_response, cost: float, request_id=None) -> bool:
    """Consume *cost* tokens; on exhaustion warn, strike, and close at the cap.

    Returns True when the frame may proceed, False when it was rejected.
    """
    bucket = get_client_bucket(websocket_response)
    if bucket.consume(cost):
        websocket_response._meshchatx_rate_strikes = 0
        return True
    counters = getattr(app, "ws_counters", None)
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
        request_id=request_id,
        retry_after=WS_RATE_RETRY_AFTER_SEC,
    )
    if strikes >= WS_RATE_ABUSE_STRIKES:
        await websocket_response.close()
    return False


def _reject_forbidden_ws_origin(app, request):
    listen_host = getattr(app, "listen_host", None)
    auth_enabled = bool(getattr(app, "auth_enabled", False))
    if websocket_origin_policy_allows(
        request,
        listen_host=listen_host,
        auth_enabled=auth_enabled,
        trusted_proxy_cidrs=get_trusted_proxy_cidrs(app.storage_dir),
        origin_allowed_fn=websocket_origin_allowed,
        is_loopback_fn=is_loopback_bind_host,
    ):
        return None
    return http_forbidden("Forbidden origin")


def register_websocket_upgrade_routes(routes, app):
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
            return http_unavailable("Too many websocket clients")

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
        try:
            while True:
                try:
                    message = cast(
                        "WSMessage",
                        await websocket_response.receive(
                            timeout=WS_IDLE_TIMEOUT_SEC,
                        ),
                    )
                except TimeoutError:
                    # No inbound frame within the idle window. Close only when
                    # activity is actually stale so receive-only listeners on a
                    # busy broadcast stream keep their socket.
                    if not client_is_idle(websocket_response):
                        continue
                    counters = getattr(app, "ws_counters", None)
                    if counters is not None:
                        counters.idle_closes += 1
                    break
                if message.type in (
                    WSMsgType.CLOSE,
                    WSMsgType.CLOSING,
                    WSMsgType.CLOSED,
                    WSMsgType.ERROR,
                ):
                    if message.type == WSMsgType.ERROR:
                        print(
                            f"ws connection error {websocket_response.exception()}",
                        )
                    break
                if message.type == WSMsgType.TEXT:
                    touch_client_activity(websocket_response)
                    counters = getattr(app, "ws_counters", None)
                    if counters is not None:
                        counters.msgs_in += 1
                    try:
                        data = json.loads(message.data)
                    except Exception as e:
                        print("failed to process client message")
                        print(e)
                        # Malformed frames still consume tokens so a garbage
                        # flood cannot bypass the rate limiter.
                        if not await _ws_rate_gate(app, websocket_response, 1.0):
                            if websocket_response.closed:
                                break
                            continue
                        await send_ws_error(
                            websocket_response,
                            message="Invalid JSON",
                            code="invalid_json",
                        )
                        continue
                    msg_type = data.get("type") if isinstance(data, dict) else None
                    cost = message_rate_cost(
                        msg_type.strip() if isinstance(msg_type, str) else None
                    )
                    if not await _ws_rate_gate(
                        app,
                        websocket_response,
                        cost,
                        request_id=data.get("request_id")
                        if isinstance(data, dict)
                        else None,
                    ):
                        if websocket_response.closed:
                            break
                        continue
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
                    # Binary frames carry a msgpack envelope; price them like a
                    # normal message before the decode dispatch.
                    if not await _ws_rate_gate(app, websocket_response, 1.0):
                        if websocket_response.closed:
                            break
                        continue
                    try:
                        await app.on_websocket_binary_received(
                            websocket_response,
                            message.data,
                        )
                    except Exception as e:
                        print("failed to process binary client message")
                        print(e)

                if client_is_idle(websocket_response):
                    counters = getattr(app, "ws_counters", None)
                    if counters is not None:
                        counters.idle_closes += 1
                    break
        finally:
            # websocket closed or handler failed: always release client state.
            try:
                await websocket_response.close()
            except Exception:
                pass
            try:
                app.websocket_clients.remove(websocket_response)
            except ValueError:
                pass
            app._detach_active_session(websocket_response)
            app._cancel_rns_link_tasks_for_client(websocket_response)
            app._clear_page_file_grants_for_client(websocket_response)
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

        max_audio_clients = 8
        if len(app.web_audio_bridge.clients) >= max_audio_clients:
            await websocket_response.close(code=1008, message=b"Too many audio clients")
            return websocket_response

        await app.web_audio_bridge.send_status(websocket_response)
        attached = app.web_audio_bridge.attach_client(websocket_response)
        if not attached:
            await websocket_response.send_str(
                json.dumps(
                    {"type": "error", "message": "No active call to attach"},
                ),
            )

        try:
            while True:
                try:
                    message = cast(
                        "WSMessage",
                        await websocket_response.receive(
                            timeout=WS_IDLE_TIMEOUT_SEC,
                        ),
                    )
                except TimeoutError:
                    if not client_is_idle(websocket_response):
                        continue
                    break
                if message.type in (
                    WSMsgType.CLOSE,
                    WSMsgType.CLOSING,
                    WSMsgType.CLOSED,
                    WSMsgType.ERROR,
                ):
                    if message.type == WSMsgType.ERROR:
                        print(
                            f"telephone audio ws error "
                            f"{websocket_response.exception()}",
                        )
                    break
                touch_client_activity(websocket_response)
                if message.type == WSMsgType.BINARY:
                    # Only accept PCM after a successful attach for this socket.
                    # Audio frames are real-time paced so they bypass the
                    # message bucket but stay bounded by max_msg_size.
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
        finally:
            app.web_audio_bridge.detach_client(websocket_response)
            try:
                await websocket_response.close()
            except Exception:
                pass
        return websocket_response
