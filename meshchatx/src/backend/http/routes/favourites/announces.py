# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites announces."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.favourites._names import *  # noqa: F403


def register_favourites_announces_routes(routes: Any, app: Any) -> None:
    # announce
    @routes.get("/api/v1/announce")
    async def announce_trigger(request):
        await app.announce()

        return web.json_response(
            {
                "message": "announcing",
            },
        )

    # serve announces

    # serve announces
    @routes.get("/api/v1/announces")
    async def announces_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable

        try:
            return await _announces_get_impl(request)
        except Exception as e:
            logger.exception("announces_get failed")
            return http_for_database_exception(e)

    async def _announces_get_impl(request):
        # get query params
        aspect = request.query.get("aspect", None)
        identity_hash = request.query.get("identity_hash", None)
        destination_hash = request.query.get("destination_hash", None)
        search_query = request.query.get("search", None)

        try:
            limit = request.query.get("limit")
            limit = int(limit) if limit is not None and limit != "" else None
        except ValueError:
            limit = None

        try:
            offset = request.query.get("offset")
            offset = int(offset) if offset is not None else 0
        except ValueError:
            offset = 0

        if not search_query and limit is None:
            limit = app._default_announce_fetch_limit(aspect)

        search_max = 2000
        if app.current_context and app.current_context.config:
            sm = app.current_context.config.announce_search_max_fetch.get()
            if sm is not None and sm > 0:
                search_max = min(int(sm), 10_000)

        include_blocked = (
            request.query.get("include_blocked", "false").lower() == "true"
        )

        blocked_identity_hashes = None
        if not include_blocked:
            blocked = await asyncio.to_thread(
                app.database.misc.get_blocked_destinations,
            )
            blocked_identity_hashes = [b["destination_hash"] for b in blocked]

        if search_query:
            # limit here is the caller's desired page size for the
            # paginated, filtered results below, not the number of rows
            # to scan for matches. Always scan up to search_max rows so
            # matches outside the most-recent page are still found.
            db_limit = search_max
        else:
            db_limit = limit
        db_offset = offset if not search_query else 0

        results = await asyncio.to_thread(
            app.announce_manager.get_filtered_announces,
            aspect=aspect,
            identity_hash=identity_hash,
            destination_hash=destination_hash,
            query=None,
            blocked_identity_hashes=blocked_identity_hashes,
            limit=db_limit,
            offset=db_offset,
        )

        total_count = 0
        if not search_query:
            if db_limit is None:
                total_count = len(results)
            else:
                total_count = await asyncio.to_thread(
                    app.announce_manager.get_filtered_announces_count,
                    aspect=aspect,
                    identity_hash=identity_hash,
                    destination_hash=destination_hash,
                    query=None,
                    blocked_identity_hashes=blocked_identity_hashes,
                )

        # pre-fetch icons and other data to avoid N+1 queries in convert_db_announce_to_dict
        all_announces = await asyncio.to_thread(
            app._batch_convert_announces_to_api_dicts,
            results,
            aspect,
        )

        # apply search query filter if provided
        if search_query:
            all_announces = filter_announced_dicts_by_search_query(
                all_announces,
                search_query,
            )

            # Re-calculate total_count after search filter
            total_count = len(all_announces)
            # apply pagination after search
            start = offset
            end = start + (limit if limit is not None else total_count)
            paginated_results = all_announces[start:end]
        else:
            # We already paginated in DB, and total_count was calculated before processing
            paginated_results = all_announces

        return web.json_response(
            {
                "announces": paginated_results,
                "total_count": total_count,
            },
        )

    @routes.post("/api/v1/announces/query")
    async def announces_query(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        destination_hashes = data.get("destination_hashes")
        aspects = data.get("aspects")
        if not isinstance(destination_hashes, list) or not destination_hashes:
            return web.json_response({"announces": [], "total_count": 0})
        if not isinstance(aspects, list) or not aspects:
            aspects = ["lxmf.delivery", "nomadnetwork.node"]

        blocked_identity_hashes = None
        if app.current_context and app.current_context.config:
            blocked = await asyncio.to_thread(
                app.database.misc.get_blocked_destinations,
            )
            blocked_identity_hashes = [b["destination_hash"] for b in blocked]

        results = await asyncio.to_thread(
            app.announce_manager.get_announces_for_destination_hashes,
            destination_hashes=destination_hashes,
            aspects=aspects,
            blocked_identity_hashes=blocked_identity_hashes,
        )
        all_announces = await asyncio.to_thread(
            app._batch_convert_announces_to_api_dicts,
            results,
            None,
            False,
        )
        return web.json_response(
            {
                "announces": all_announces,
                "total_count": len(all_announces),
            },
        )
