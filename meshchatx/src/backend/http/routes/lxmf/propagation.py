# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf propagation."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.lxmf._names import *  # noqa: F403, F405


def register_lxmf_propagation_routes(routes, app):

    @routes.get("/api/v1/lxmf/propagation-node/status")
    async def propagation_node_status(request):
        router = app.message_router
        current_state = None
        current_progress = 0.0
        transfer_size = None
        if router is not None:
            try:
                current_state = router.propagation_transfer_state
                current_progress = router.propagation_transfer_progress
                transfer_size = getattr(
                    router,
                    "propagation_transfer_size",
                    None,
                )
                # COMPLETE is terminal, so reset to idle so the UI does not keep
                # looking "busy" after a finished auto/manual sync.
                if current_state == router.PR_COMPLETE:
                    with contextlib.suppress(Exception):
                        router.propagation_transfer_state = router.PR_IDLE
                        router.propagation_transfer_progress = 0.0
                        if hasattr(router, "propagation_transfer_size"):
                            router.propagation_transfer_size = None
            except Exception:
                pass
        sync_metrics = app._collect_propagation_sync_metrics()
        progress_raw = current_progress
        try:
            progress_pct = float(progress_raw) * 100
        except (TypeError, ValueError):
            progress_pct = 0.0
        last_result = getattr(
            app.message_router,
            "propagation_transfer_last_result",
            None,
        )
        if not isinstance(last_result, (int, float, str, type(None))):
            last_result = None
        if current_state is None:
            current_state = 0
        transfer_size_bytes = None
        if isinstance(transfer_size, (int, float)) and transfer_size > 0:
            transfer_size_bytes = int(transfer_size)
        inbound_delivery_count = 0
        inbound_deliveries = []
        if router is not None:
            inbound_deliveries = list_inbound_deliveries(router)
            inbound_delivery_count = len(inbound_deliveries)
        return web.json_response(
            {
                "propagation_node_status": {
                    "state": convert_propagation_node_state_to_string(
                        current_state,
                    ),
                    "progress": progress_pct,
                    "transfer_size_bytes": transfer_size_bytes,
                    "inbound_delivery_count": inbound_delivery_count,
                    "inbound_deliveries": inbound_deliveries,
                    "messages_received": last_result,
                    "messages_stored": sync_metrics["messages_stored"],
                    "delivery_confirmations": sync_metrics["delivery_confirmations"],
                    "messages_hidden": sync_metrics["messages_hidden"],
                },
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    # sync propagation node

    # sync propagation node
    @routes.post("/api/v1/lxmf/propagation-node/sync")
    async def propagation_node_sync(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        # ensure propagation node is configured before attempting to sync
        outbound_node = app.message_router.get_outbound_propagation_node()
        if outbound_node is None:
            return web.json_response(
                {
                    "message": "A propagation node must be configured to sync messages.",
                },
                status=400,
            )

        # proactively request path, but do not block/fail here.
        # LXMF internally manages PR_PATH_REQUESTED and retries.
        if not RNS.Transport.has_path(outbound_node):
            with contextlib.suppress(Exception):
                RNS.Transport.request_path(outbound_node)

        # request messages from propagation node
        await app.sync_propagation_nodes(force=True)

        return web.json_response(
            {
                "message": "Sync is starting",
            },
        )

    # stop syncing propagation node

    # stop syncing propagation node
    @routes.post("/api/v1/lxmf/propagation-node/stop-sync")
    async def propagation_node_stop_sync(request):
        from meshchatx.src.backend.demo_mode import demo_mode_block_response

        blocked = demo_mode_block_response(app)
        if blocked is not None:
            return blocked
        app.stop_propagation_node_sync()

        return web.json_response(
            {
                "message": "Sync is stopping",
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/cancel-inbound")
    async def propagation_node_cancel_inbound(request):
        router = app.message_router
        data = {}
        with contextlib.suppress(Exception):
            data = await request.json()
        if not isinstance(data, dict):
            data = {}
        resource_hash = data.get("resource_hash")
        result = cancel_inbound_deliveries(router, resource_hash=resource_hash)
        if not result.get("ok"):
            status = 503 if "unavailable" in str(result.get("error") or "") else 400
            return web.json_response(
                {
                    "message": result.get(
                        "error",
                        "Failed to cancel inbound deliveries",
                    ),
                    "cancelled": result.get("cancelled", 0),
                },
                status=status,
            )
        cancelled = int(result.get("cancelled") or 0)
        if resource_hash:
            message = (
                "Cancelled inbound delivery"
                if cancelled
                else "Inbound delivery was not active"
            )
        else:
            message = f"Cancelled {cancelled} inbound deliveries"
        return web.json_response(
            {
                "message": message,
                "cancelled": cancelled,
                "resource_hash": result.get("resource_hash"),
                "inbound_delivery_count": len(list_inbound_deliveries(router)),
                "inbound_deliveries": list_inbound_deliveries(router),
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/stop")
    async def propagation_node_stop(request):
        app.config.lxmf_local_propagation_node_enabled.set(False)
        app.stop_local_propagation_node()
        AsyncUtils.run_async(app.send_config_to_websocket_clients())
        return web.json_response(
            {
                "message": "Local propagation node stopped",
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    @routes.post("/api/v1/lxmf/propagation-node/restart")
    async def propagation_node_restart(request):
        app.config.lxmf_local_propagation_node_enabled.set(True)
        app.restart_local_propagation_node()
        AsyncUtils.run_async(app.send_config_to_websocket_clients())
        return web.json_response(
            {
                "message": "Local propagation node restarted",
                "local_propagation_node": app.get_local_propagation_node_stats(),
            },
        )

    # serve propagation nodes

    # serve propagation nodes
    @routes.get("/api/v1/lxmf/propagation-nodes")
    async def propagation_nodes_get(request):
        ctx = app.current_context
        if not ctx or not getattr(ctx, "running", False) or ctx.database is None:
            return web.json_response(
                {
                    "message": "Application is initializing or switching identity",
                },
                status=503,
            )
        database = ctx.database
        # get query params
        limit = request.query.get("limit", None)

        # get lxmf.propagation announces
        limit_int = None
        if limit is not None:
            try:
                limit_int = max(0, int(limit))
            except (ValueError, TypeError):
                limit_int = None
        results = database.announces.get_announces(
            aspect="lxmf.propagation",
            limit=limit_int,
        )

        related_index = database.announces.index_announces_by_identity_aspect(
            database.announces.get_announces_for_identity_hashes(
                [a.get("identity_hash") for a in results],
                aspects=["lxmf.delivery", "nomadnetwork.node"],
            ),
        )

        # process announces
        lxmf_propagation_nodes = []
        local_identity_hash = ctx.identity.hash.hex() if ctx else None
        local_destination_hash_raw = (
            getattr(ctx.message_router.propagation_destination, "hexhash", None)
            if ctx
            else None
        )
        if local_destination_hash_raw is None and ctx:
            local_destination_hash_raw = getattr(
                ctx.message_router.propagation_destination,
                "hash",
                None,
            )
        if isinstance(local_destination_hash_raw, bytes):
            local_destination_hash = local_destination_hash_raw.hex()
        elif isinstance(local_destination_hash_raw, str):
            local_destination_hash = local_destination_hash_raw
        else:
            local_destination_hash = None
        local_stats = app.get_local_propagation_node_stats(context=ctx) if ctx else None
        for announce in results:
            ident = announce.get("identity_hash")
            lxmf_delivery_announce = related_index.get((ident, "lxmf.delivery"))
            nomadnetwork_node_announce = related_index.get(
                (ident, "nomadnetwork.node"),
            )

            # get a display name from other announces belonging to the propagation nodes identity
            operator_display_name = None
            if (
                lxmf_delivery_announce is not None
                and lxmf_delivery_announce["app_data"] is not None
            ):
                operator_display_name = parse_lxmf_display_name(
                    lxmf_delivery_announce["app_data"],
                    None,
                )
            elif (
                nomadnetwork_node_announce is not None
                and nomadnetwork_node_announce["app_data"] is not None
            ):
                operator_display_name = parse_nomadnetwork_node_display_name(
                    nomadnetwork_node_announce["app_data"],
                    None,
                )

            # parse app_data so we can see if propagation is enabled or disabled for this node
            is_propagation_enabled = None
            per_transfer_limit = None
            propagation_node_data = parse_lxmf_propagation_node_app_data(
                announce["app_data"],
            )
            if propagation_node_data is not None:
                is_propagation_enabled = propagation_node_data["enabled"]
                per_transfer_limit = propagation_node_data["per_transfer_limit"]

            # ensure created_at and updated_at have Z suffix for UTC if they don't have a timezone
            created_at = str(announce["created_at"])
            if created_at and "+" not in created_at and "Z" not in created_at:
                created_at += "Z"

            updated_at = str(announce["updated_at"])
            if updated_at and "+" not in updated_at and "Z" not in updated_at:
                updated_at += "Z"

            is_local_node = (
                announce["identity_hash"] == local_identity_hash
                or announce["destination_hash"] == local_destination_hash
            )
            if is_local_node and isinstance(local_stats, dict):
                local_running = local_stats.get("is_running")
                if isinstance(local_running, bool):
                    is_propagation_enabled = local_running

            lxmf_propagation_nodes.append(
                {
                    "destination_hash": announce["destination_hash"],
                    "identity_hash": announce["identity_hash"],
                    "operator_display_name": operator_display_name,
                    "is_propagation_enabled": is_propagation_enabled,
                    "per_transfer_limit": per_transfer_limit,
                    "is_local_node": is_local_node,
                    "local_node_stats": (local_stats if is_local_node else None),
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )

        if (
            ctx is not None
            and local_destination_hash is not None
            and not any(
                node["destination_hash"] == local_destination_hash
                for node in lxmf_propagation_nodes
            )
        ):
            now_iso = datetime.now(UTC).isoformat()
            lxmf_propagation_nodes.insert(
                0,
                {
                    "destination_hash": local_destination_hash,
                    "identity_hash": local_identity_hash,
                    "operator_display_name": ctx.config.display_name.get(),
                    "is_propagation_enabled": (
                        local_stats.get("is_running")
                        if isinstance(local_stats, dict)
                        and isinstance(local_stats.get("is_running"), bool)
                        else ctx.config.lxmf_local_propagation_node_enabled.get()
                    ),
                    "per_transfer_limit": int(
                        getattr(
                            ctx.message_router,
                            "propagation_per_transfer_limit",
                            0,
                        ),
                    ),
                    "is_local_node": True,
                    "local_node_stats": local_stats,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                },
            )

        return web.json_response(
            {
                "lxmf_propagation_nodes": lxmf_propagation_nodes,
            },
        )

    # get path to destination
    async def path_table(request):
        limit = request.query.get("limit", None)
        offset = request.query.get("offset", None)
        destination_hashes = None
        if request.method == "POST":
            try:
                body = await request.json()
                destination_hashes = body.get("destination_hashes")
                if destination_hashes and not isinstance(destination_hashes, list):
                    destination_hashes = None
            except Exception:
                pass

        all_paths = []
        if hasattr(app, "reticulum") and app.reticulum:
            try:
                all_paths = app.reticulum.get_path_table()
            except Exception:
                pass

        if destination_hashes:
            hash_set = {h.lower() for h in destination_hashes if isinstance(h, str)}
            all_paths = [p for p in all_paths if p["hash"].hex().lower() in hash_set]

        total_count = len(all_paths)

        # apply pagination if requested
        if limit is not None or offset is not None:
            try:
                start = int(offset) if offset else 0
                end = (start + int(limit)) if limit else total_count
                paginated_paths = all_paths[start:end]
            except (ValueError, TypeError):
                paginated_paths = all_paths
        else:
            paginated_paths = all_paths

        path_table = []
        for path in paginated_paths:
            path["hash"] = path["hash"].hex()
            path["via"] = path["via"].hex()
            path_table.append(path)

        return web.json_response(
            {
                "path_table": path_table,
                "total_count": total_count,
            },
        )
