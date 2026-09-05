# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rnsh."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers


def register_rn_tools_rnsh_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    @routes.get("/api/v1/rnsh/sessions")
    async def rnsh_sessions_get(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        return web.json_response(manager.list_sessions())

    @routes.post("/api/v1/rnsh/sessions")
    async def rnsh_sessions_post(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        data = await request.json()
        try:
            session = manager.create_session(data or {})
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        autostart = bool((data or {}).get("autostart", True))
        if autostart:
            try:
                session.start()
            except Exception as e:
                with contextlib.suppress(Exception):
                    manager.remove_session(session.session_id)
                return web.json_response({"message": str(e)}, status=400)
        return web.json_response(
            {"session": session.to_dict(include_output_tail=True)},
        )

    @routes.delete("/api/v1/rnsh/sessions/{session_id}")
    async def rnsh_sessions_delete(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            manager.remove_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)
        return web.json_response({"message": "Session removed"})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/start")
    async def rnsh_session_start(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.start_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/stop")
    async def rnsh_session_stop(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.stop_session(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/input")
    async def rnsh_session_input(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        text = data.get("text")
        if not isinstance(text, str):
            return web.json_response(
                {"message": "Input text is required"},
                status=400,
            )
        add_newline = bool(data.get("newline", False))
        if add_newline and not text.endswith("\n"):
            text += "\n"
        try:
            session = manager.send_input(session_id, text)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.post("/api/v1/rnsh/sessions/{session_id}/resize")
    async def rnsh_session_resize(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        data = await request.json()
        rows = (data or {}).get("rows")
        cols = (data or {}).get("cols")
        try:
            session = manager.resize_session(session_id, rows, cols)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})

    @routes.get("/api/v1/rnsh/sessions/{session_id}/output")
    async def rnsh_session_output(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        cursor = request.query.get("cursor", 0)
        try:
            payload = manager.output_since(session_id, cursor)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response(payload)

    @routes.post("/api/v1/rnsh/sessions/{session_id}/clear")
    async def rnsh_session_clear(request):
        manager, error = _rnsh_require_manager()
        if error is not None:
            return error
        session_id = request.match_info.get("session_id", "")
        try:
            session = manager.clear_output(session_id)
        except KeyError:
            return web.json_response({"message": "Session not found"}, status=404)
        except Exception as e:
            return web.json_response({"message": str(e)}, status=400)
        return web.json_response({"session": session})
