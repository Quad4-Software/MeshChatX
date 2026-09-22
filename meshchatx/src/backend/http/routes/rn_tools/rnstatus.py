# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rnstatus."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_error_from_exception,
)
from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403


def register_rn_tools_rnstatus_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    # --- RNS FileSync ---

    @routes.get("/api/v1/rnstatus")
    async def rnstatus(request):
        include_link_stats = request.query.get("include_link_stats", "false") in (
            "true",
            "1",
        )
        sorting = request.query.get("sorting")
        sort_reverse = request.query.get("sort_reverse", "false") in ("true", "1")
        show_all = request.query.get("show_all", "false") in ("true", "1")
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(
            app.rnstatus_handler,
            "RNStatus",
        )
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return http_bad_request("Invalid timeout")

        try:
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_status,
                )

                if not identity_path and not identity_name:
                    return http_bad_request(
                        "identity_path or identity_name is required for remote queries"
                    )
                stats, link_count = await asyncio.to_thread(
                    fetch_remote_status,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    include_link_stats=include_link_stats,
                    timeout=timeout,
                )
                status = app.rnstatus_handler.get_status(
                    include_link_stats=include_link_stats,
                    sorting=sorting,
                    sort_reverse=sort_reverse,
                    stats=stats,
                    link_count=link_count,
                    include_local_blackhole=False,
                    show_all=show_all,
                )
                status["remote"] = remote
            else:
                status = app.rnstatus_handler.get_status(
                    include_link_stats=include_link_stats,
                    sorting=sorting,
                    sort_reverse=sort_reverse,
                    show_all=show_all,
                )
            return web.json_response(status)
        except (ValueError, FileNotFoundError) as e:
            return http_bad_request(str(e))
        except TimeoutError as e:
            return http_error(504, str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
