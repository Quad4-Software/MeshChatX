# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rnpath."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_error_from_exception,
    http_payload_too_large,
    http_unavailable,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)

from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers


def register_rn_tools_rnpath_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    @routes.get("/api/v1/rnpath/table")
    async def rnpath_table(request):
        def _optional_int(raw, field_name):
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {field_name}") from None

        try:
            max_hops = _optional_int(request.query.get("max_hops"), "max_hops")
            hops = _optional_int(request.query.get("hops"), "hops")
            page = int(request.query.get("page", 1))
            limit = int(request.query.get("limit", 50))
        except ValueError as e:
            return http_bad_request(str(e))

        search = request.query.get("search")
        interface = request.query.get("interface")
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return http_bad_request("Invalid timeout")

        try:
            raw_table = None
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_path_table,
                )

                if not identity_path and not identity_name:
                    return http_bad_request(
                        "identity_path or identity_name is required for remote queries"
                    )
                raw_table = await asyncio.to_thread(
                    fetch_remote_path_table,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    max_hops=max_hops,
                    timeout=timeout,
                )
            result = app.rnpath_handler.get_path_table(
                max_hops=max_hops,
                search=search,
                interface=interface,
                hops=hops,
                page=page,
                limit=limit,
                raw_table=raw_table,
            )
            if remote:
                result["remote"] = remote
            return web.json_response(result)
        except (ValueError, FileNotFoundError) as e:
            return http_bad_request(str(e))
        except TimeoutError as e:
            return http_error(504, str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.get("/api/v1/rnpath/rates")
    async def rnpath_rates(request):
        remote = (request.query.get("remote") or "").strip()
        identity_path = (request.query.get("identity_path") or "").strip() or None
        identity_name = (request.query.get("identity_name") or "").strip() or None
        timeout_raw = request.query.get("timeout")

        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready

        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            return http_bad_request("Invalid timeout")

        try:
            raw_table = None
            if remote:
                from meshchatx.src.backend.remote_management_client import (
                    fetch_remote_rate_table,
                )

                if not identity_path and not identity_name:
                    return http_bad_request(
                        "identity_path or identity_name is required for remote queries"
                    )
                raw_table = await asyncio.to_thread(
                    fetch_remote_rate_table,
                    remote_transport_hash=remote,
                    identity_path=identity_path,
                    identity_name=identity_name,
                    reticulum_config_dir=getattr(app, "reticulum_config_dir", None),
                    timeout=timeout,
                )
            rates = app.rnpath_handler.get_rate_table(raw_table=raw_table)
            payload = {"rates": rates}
            if remote:
                payload["remote"] = remote
            return web.json_response(payload)
        except (ValueError, FileNotFoundError) as e:
            return http_bad_request(str(e))
        except TimeoutError as e:
            return http_error(504, str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rnpath/drop")
    async def rnpath_drop(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = data.get("destination_hash")
        if not destination_hash:
            return http_bad_request("destination_hash is required")
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.drop_path(destination_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rnpath/drop-via")
    async def rnpath_drop_via(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        transport_instance_hash = data.get("transport_instance_hash")
        if not transport_instance_hash:
            return http_bad_request("transport_instance_hash is required")
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.drop_all_via(transport_instance_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rnpath/drop-queues")
    async def rnpath_drop_queues(request):
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            app.rnpath_handler.drop_announce_queues()
            return web.json_response({"success": True})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rnpath/request")
    async def rnpath_request(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = data.get("destination_hash")
        if not destination_hash:
            return http_bad_request("destination_hash is required")
        not_ready = app._require_rns_tool_handler(app.rnpath_handler, "RNPath")
        if not_ready is not None:
            return not_ready
        try:
            success = app.rnpath_handler.request_path(destination_hash)
            return web.json_response({"success": success})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.get("/api/v1/rnpath/trace/{destination_hash}")
    async def rnpath_trace(request):
        destination_hash = request.match_info.get("destination_hash")
        if not destination_hash:
            return http_bad_request("destination_hash is required")
        try:
            if not app.rnpath_trace_handler:
                return http_unavailable(
                    "RNPathTraceHandler not initialized for current context"
                )
            result = await app.rnpath_trace_handler.trace_path(destination_hash)
            return web.json_response(result)
        except Exception:
            logger.exception("RN path trace route failed")
            return http_unexpected("Trace failed")

