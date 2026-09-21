# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rnx."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_rn_tools_rnx_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    @routes.get("/api/v1/rnx/sessions")
    async def rnx_sessions_get(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.list_sessions())

    @routes.post("/api/v1/rnx/sessions")
    async def rnx_sessions_post(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        session = manager.create_session(data or {})
        autostart = bool((data or {}).get("autostart", True))
        if autostart:
            try:
                session.start()
            except Exception as e:
                with contextlib.suppress(Exception):
                    manager.remove_session(session.session_id)
                return http_error_from_exception(e, key="message")
        return web.json_response(
            {"session": session.to_dict(include_output_tail=True)},
        )

    @routes.delete("/api/v1/rnx/sessions/{session_id}")
    async def rnx_sessions_delete(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            manager.remove_session(session_id)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        return web.json_response({"message": "Session removed"})

    @routes.post("/api/v1/rnx/sessions/{session_id}/start")
    async def rnx_session_start(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.start_session(session_id)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/stop")
    async def rnx_session_stop(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.stop_session(session_id)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/input")
    async def rnx_session_input(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        text = data.get("text")
        if not isinstance(text, str):
            return http_bad_request("Input text is required")
        add_newline = bool(data.get("newline", False))
        if add_newline and not text.endswith("\n"):
            text += "\n"
        try:
            session = manager.send_input(session_id, text)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnx/sessions/{session_id}/resize")
    async def rnx_session_resize(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        rows = (data or {}).get("rows")
        cols = (data or {}).get("cols")
        try:
            session = manager.resize_session(session_id, rows, cols)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response({"session": session})

    @routes.get("/api/v1/rnx/sessions/{session_id}/output")
    async def rnx_session_output(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        cursor = request.query.get("cursor", 0)
        try:
            payload = manager.output_since(session_id, cursor)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response(payload)

    @routes.post("/api/v1/rnx/sessions/{session_id}/clear")
    async def rnx_session_clear(request):
        manager, error = _rnx_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.clear_output(session_id)
        except KeyError:
            return http_not_found("Session not found")
        except Exception as e:
            return http_error_from_exception(e, key="message")
        return web.json_response({"session": session})
