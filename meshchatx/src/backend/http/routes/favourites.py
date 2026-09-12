# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites."""

from __future__ import annotations

import asyncio
import json
import logging

from aiohttp import web

from meshchatx.src.backend.announce_manager import (
    filter_announced_dicts_by_search_query,
)
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.db_availability import (
    http_for_database_exception,
    require_database,
)
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_not_found,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_body_limited,
    read_json_limited,
)
from meshchatx.src.backend.meshchat_utils import convert_db_favourite_to_dict
from meshchatx.src.backend.nomadnet_downloader import (
    drop_cached_link,
    get_cached_active_link,
)

logger = logging.getLogger(__name__)


def register_favourites_routes(routes, app):
    # announce
    @routes.get(API_V1_PREFIX + "/announce")
    async def announce_trigger(request):
        await app.announce()

        return web.json_response(
            {
                "message": "announcing",
            },
        )

    # serve announces

    # serve announces
    @routes.get(API_V1_PREFIX + "/announces")
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

    @routes.post(API_V1_PREFIX + "/announces/query")
    async def announces_query(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
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

    # serve favourites

    # serve favourites
    @routes.get(API_V1_PREFIX + "/favourites")
    async def favourites_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        aspect = request.query.get("aspect", None)
        try:
            results = app.database.announces.get_favourites(aspect=aspect)
            favourites = [
                convert_db_favourite_to_dict(favourite) for favourite in results
            ]
            return web.json_response(
                {
                    "favourites": favourites,
                },
            )
        except Exception as e:
            logger.exception("favourites_get failed")
            return http_for_database_exception(e)

    # add favourite

    # add favourite
    @routes.post(API_V1_PREFIX + "/favourites/add")
    async def favourites_add(request):
        # get request data
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash = data.get("destination_hash", None)
        display_name = data.get("display_name", None)
        aspect = data.get("aspect", None)

        # destination hash is required
        if destination_hash is None:
            return http_error(422, "destination_hash is required")

        # display name is required
        if display_name is None:
            return http_error(422, "display_name is required")

        # aspect is required
        if aspect is None:
            return http_error(422, "aspect is required")

        # upsert favourite
        app.database.announces.upsert_favourite(
            destination_hash,
            display_name,
            aspect,
        )
        return web.json_response(
            {
                "message": "Favourite has been added!",
            },
        )

    # rename favourite

    # rename favourite
    @routes.post(API_V1_PREFIX + "/favourites/{destination_hash}/rename")
    async def favourites_rename(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get request data
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        raw_name = data.get("display_name")
        if raw_name is None:
            display_name = ""
        elif isinstance(raw_name, str):
            display_name = raw_name.strip()
        else:
            display_name = str(raw_name).strip()

        favourite = app.database.announces.get_favourite_by_destination_hash(
            destination_hash,
        )
        if favourite is None:
            return http_not_found("Favourite not found")

        # update display name if provided
        if len(display_name) > 0:
            app.database.announces.upsert_custom_display_name(
                destination_hash,
                display_name,
            )
            app.database.announces.upsert_favourite(
                destination_hash,
                display_name,
                favourite["aspect"],
            )

        return web.json_response(
            {
                "message": "Favourite has been renamed",
            },
        )

    @routes.post(API_V1_PREFIX + "/favourites/{destination_hash}/identify-on-connect")
    async def favourites_identify_on_connect(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")

        enabled = bool(data.get("enabled"))
        aspect = data.get("aspect") or "nomadnetwork.node"
        if not isinstance(aspect, str) or not aspect.strip():
            aspect = "nomadnetwork.node"
        else:
            aspect = aspect.strip()

        raw_name = data.get("display_name")
        if isinstance(raw_name, str):
            display_name = raw_name.strip()
        elif raw_name is None:
            display_name = ""
        else:
            display_name = str(raw_name).strip()

        existing = app.database.announces.get_favourite_by_destination_hash(
            destination_hash,
        )
        if existing is not None:
            if not display_name:
                display_name = existing["display_name"] or ""
            if data.get("aspect") is None:
                aspect = existing["aspect"] or aspect

        if not display_name:
            display_name = "Unknown Node"

        app.database.announces.upsert_favourite(
            destination_hash,
            display_name,
            aspect,
            identify_on_connect=enabled,
        )

        identified_now = False
        cache_dropped = False
        try:
            dest_bytes = bytes.fromhex(destination_hash)
        except ValueError:
            dest_bytes = None

        if dest_bytes is not None:
            if enabled:
                link = get_cached_active_link(dest_bytes)
                identity = getattr(app, "identity", None)
                if link is not None and identity is not None:
                    try:
                        link.identify(identity)
                        identified_now = True
                    except Exception:
                        logger.exception(
                            "favourites_identify_on_connect identify failed",
                        )
            else:
                cache_dropped = bool(drop_cached_link(dest_bytes))

        favourite = app.database.announces.get_favourite_by_destination_hash(
            destination_hash,
        )
        return web.json_response(
            {
                "message": "Identify on connect updated",
                "identify_on_connect": enabled,
                "identified_now": identified_now,
                "cache_dropped": cache_dropped,
                "favourite": (
                    convert_db_favourite_to_dict(favourite)
                    if favourite is not None
                    else None
                ),
            },
        )

    # delete favourite

    # delete favourite
    @routes.delete(API_V1_PREFIX + "/favourites/{destination_hash}")
    async def favourites_delete(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # delete favourite
        app.database.announces.delete_favourite(destination_hash)
        return web.json_response(
            {
                "message": "Favourite has been deleted!",
            },
        )

    # bulk import favourites

    # bulk import favourites
    @routes.post(API_V1_PREFIX + "/favourites/import")
    async def favourites_import(request):
        try:
            data = await read_json_limited(request)
            entries = data.get("favourites", [])
            if not isinstance(entries, list):
                return http_bad_request(
                    "Invalid import format: favourites must be an array",
                )
            seen = {}
            no_hash = []
            for entry in entries:
                h = entry.get("destination_hash")
                if h:
                    seen[h] = entry
                else:
                    no_hash.append(entry)
            unique_entries = list(seen.values()) + no_hash
            imported = 0
            skipped = 0
            for entry in unique_entries:
                dest_hash = entry.get("destination_hash")
                display_name = entry.get("display_name", "")
                aspect = entry.get("aspect")
                if not dest_hash or not aspect:
                    skipped += 1
                    continue
                identify_raw = entry.get("identify_on_connect")
                identify_on_connect = None
                if identify_raw is not None:
                    identify_on_connect = bool(identify_raw)
                try:
                    app.database.announces.upsert_favourite(
                        dest_hash,
                        display_name,
                        aspect,
                        identify_on_connect=identify_on_connect,
                    )
                    imported += 1
                except Exception:
                    skipped += 1
            return web.json_response(
                {
                    "message": "Favourites import complete",
                    "imported": imported,
                    "skipped": skipped,
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            return http_unexpected(f"Failed to import favourites: {e!s}")

    @routes.get(API_V1_PREFIX + "/favourites/layout")
    async def favourites_layout_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            layout = app.database.announces.get_favourites_layout()
            return web.json_response({"layout": layout})
        except Exception as e:
            logger.exception("favourites_layout_get failed")
            return http_for_database_exception(e)

    @routes.put(API_V1_PREFIX + "/favourites/layout")
    async def favourites_layout_put(request):
        from meshchatx.src.backend.favourites_layout import (
            MAX_LAYOUT_JSON_BYTES,
            layout_payload_too_large,
        )

        content_length = request.content_length
        if content_length is not None and layout_payload_too_large(
            content_length,
        ):
            return http_payload_too_large("favourites layout exceeds size limit")
        try:
            raw = await read_body_limited(request, MAX_LAYOUT_JSON_BYTES + 1)
        except PayloadTooLargeError:
            return http_payload_too_large("favourites layout exceeds size limit")
        except Exception:
            return http_bad_request("Invalid request body")
        if layout_payload_too_large(len(raw)):
            return http_payload_too_large("favourites layout exceeds size limit")
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return http_bad_request("Invalid JSON body")
        layout = data.get("layout") if isinstance(data, dict) else None
        try:
            saved = app.database.announces.set_favourites_layout(layout)
        except ValueError as e:
            return http_bad_request(str(e))
        return web.json_response({"layout": saved})

    # serve archived pages
