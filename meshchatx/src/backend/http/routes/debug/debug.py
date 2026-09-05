# SPDX-License-Identifier: 0BSD
"""HTTP routes: debug/debug."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.debug._names import *  # noqa: F403


def register_debug_debug_routes(routes: Any, app: Any) -> None:
    # serve debug logs

    @routes.get("/api/v1/debug/logs")
    async def get_debug_logs(request):
        search = request.query.get("search")
        level = request.query.get("level")
        module = request.query.get("module")
        is_anomaly = parse_bool_query_param(request.query.get("is_anomaly"))
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))

        logs = memory_log_handler.get_logs(
            limit=limit,
            offset=offset,
            search=search,
            level=level,
            module=module,
            is_anomaly=is_anomaly,
        )
        total = memory_log_handler.get_total_count(
            search=search,
            level=level,
            module=module,
            is_anomaly=is_anomaly,
        )

        from meshchatx.src.backend.log_redaction import redact_diagnostic_text

        redacted_logs = []
        for entry in logs or []:
            if not isinstance(entry, dict):
                redacted_logs.append(entry)
                continue
            entry_copy = dict(entry)
            message = entry_copy.get("message")
            if isinstance(message, str):
                entry_copy["message"] = redact_diagnostic_text(message)
            redacted_logs.append(entry_copy)

        return web.json_response(
            {
                "logs": redacted_logs,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    @routes.get("/api/v1/debug/websocket")
    async def get_websocket_debug(request):
        counters = getattr(app, "ws_counters", None)
        clients = getattr(app, "websocket_clients", None) or []
        snap = (
            counters.snapshot(client_count=len(clients))
            if counters is not None
            else {"clients": len(clients)}
        )
        seq_state = getattr(app, "ws_seq_state", None)
        if seq_state is not None:
            snap["seq"] = int(seq_state.seq)
        snap["max_msg_size"] = int(
            getattr(app, "websocket_max_msg_size", 0) or 0,
        )
        wt = getattr(app, "webtransport_state", None)
        if wt is not None:
            snap["webtransport"] = wt.status_dict()
        return web.json_response({"websocket": snap})

    @routes.get("/api/v1/debug/access-attempts")
    async def get_access_attempts(request):
        search = request.query.get("search")
        outcome = request.query.get("outcome") or None
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))
        if not app.database:
            return web.json_response(
                {"attempts": [], "total": 0, "limit": limit, "offset": offset},
            )
        dao = app.database.access_attempts
        attempts = dao.list_attempts(
            limit=limit,
            offset=offset,
            search=search,
            outcome=outcome,
        )
        total = dao.count_attempts(search=search, outcome=outcome)
        return web.json_response(
            {
                "attempts": attempts,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
        )

    @routes.get("/api/v1/diagnostics/memory")
    async def get_memory_diagnostics(request):
        if app._mem_diag is None:
            return web.json_response(
                {"enabled": False, "message": "Pass --memory-diag to enable"},
            )
        # tracemalloc.snapshot() + gc.get_objects() are CPU-bound and
        # block the event loop for tens of seconds, so run off-loop.
        report = await asyncio.to_thread(app._mem_diag.report)
        return web.json_response(report)

    @routes.post("/api/v1/diagnostics/memory/snapshot")
    async def take_memory_snapshot(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        await asyncio.to_thread(app._mem_diag.snapshot)
        gc_result = await asyncio.to_thread(app._mem_diag.find_cyclic_garbage)
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(
            {
                "status": "ok",
                "snapshot_count": len(app._mem_diag._snapshots),
                "gc_collected": gc_result,
                "gc_stats": stats,
            },
        )

    @routes.get("/api/v1/diagnostics/memory/heap")
    async def get_heap_analysis(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        top_n = int(request.query.get("top_n", 40))
        by_type = await asyncio.to_thread(app._mem_diag.heap_by_type, top_n=top_n)
        by_cat = await asyncio.to_thread(app._mem_diag.heap_by_category)
        acc = await asyncio.to_thread(app._mem_diag.accumulating_types)
        growth = await asyncio.to_thread(app._mem_diag.type_growth_since_start)
        return web.json_response(
            {
                "by_type": by_type,
                "by_category": by_cat,
                "accumulating": acc,
                "growth_since_start": growth,
            },
        )

    @routes.get("/api/v1/diagnostics/memory/gc")
    async def get_gc_stats(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"enabled": False, "message": "Pass --memory-diag to enable"},
            )
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(stats)

    @routes.post("/api/v1/diagnostics/memory/gc/collect")
    async def force_gc_collect(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        result = await asyncio.to_thread(app._mem_diag.find_cyclic_garbage)
        if app._mem_diag.enabled:
            await asyncio.to_thread(app._mem_diag.snapshot)
        stats = await asyncio.to_thread(app._mem_diag.gc_stats)
        return web.json_response(
            {
                "status": "ok",
                "gc_collected": result,
                "gc_stats": stats,
                "snapshot_count": len(app._mem_diag._snapshots),
            },
        )

    @routes.get("/api/v1/diagnostics/memory/referrers")
    async def get_referrers(request):
        if app._mem_diag is None or not app._mem_diag.enabled:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        type_name = request.query.get("type", "")
        if not type_name:
            return web.json_response(
                {"error": "Specify ?type=<TypeName>"},
                status=400,
            )
        result = await asyncio.to_thread(
            app._mem_diag.find_referrers,
            type_name,
        )
        return web.json_response(result)

    @routes.post("/api/v1/diagnostics/memory/reset")
    async def reset_memory_diagnostics(request):
        if app._mem_diag is None:
            return web.json_response(
                {"error": "Memory diagnostics not enabled"},
                status=400,
            )
        await asyncio.to_thread(app._mem_diag.reset)
        await asyncio.to_thread(app._mem_diag.start)
        return web.json_response({"status": "ok", "message": "Diagnostics reset"})

    @routes.get("/api/v1/bug-reports/issues")
    async def list_bug_issues(request):
        manager = _bug_manager()
        limit = int(request.query.get("limit", 50))
        status = request.query.get("status") or None
        return web.json_response(manager.list_issues(limit=limit, status=status))

    @routes.get("/api/v1/bug-reports/issues/{fingerprint}")
    async def get_bug_issue(request):
        manager = _bug_manager()
        fingerprint = request.match_info.get("fingerprint") or ""
        try:
            return web.json_response(manager.get_issue(fingerprint))
        except LookupError:
            return web.json_response({"error": "issue not found"}, status=404)

    @routes.post("/api/v1/bug-reports/local")
    async def record_local_bug(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        manager = _bug_manager()
        result = await asyncio.to_thread(manager.record_local, data)
        return web.json_response(result)

    @routes.post("/api/v1/bug-reports/issues/{fingerprint}/status")
    async def set_bug_issue_status(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        manager = _bug_manager()
        fingerprint = request.match_info.get("fingerprint") or ""
        status = str((data or {}).get("status") or "")
        try:
            result = manager.set_issue_status(fingerprint, status)
            return web.json_response(result)
        except LookupError:
            return web.json_response({"error": "issue not found"}, status=404)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
