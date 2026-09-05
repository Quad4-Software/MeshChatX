# SPDX-License-Identifier: 0BSD
"""HTTP routes: favourites CRUD."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.favourites._names import *  # noqa: F403


def register_favourites_favourites_crud_routes(routes: Any, app: Any) -> None:
    # serve favourites

    # serve favourites
    @routes.get("/api/v1/favourites")
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
    @routes.post("/api/v1/favourites/add")
    async def favourites_add(request):
        # get request data
        data = await request.json()
        destination_hash = data.get("destination_hash", None)
        display_name = data.get("display_name", None)
        aspect = data.get("aspect", None)

        # destination hash is required
        if destination_hash is None:
            return web.json_response(
                {
                    "message": "destination_hash is required",
                },
                status=422,
            )

        # display name is required
        if display_name is None:
            return web.json_response(
                {
                    "message": "display_name is required",
                },
                status=422,
            )

        # aspect is required
        if aspect is None:
            return web.json_response(
                {
                    "message": "aspect is required",
                },
                status=422,
            )

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
    @routes.post("/api/v1/favourites/{destination_hash}/rename")
    async def favourites_rename(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # get request data
        data = await request.json()
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
            return web.json_response(
                {"message": "Favourite not found"},
                status=404,
            )

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

    @routes.post("/api/v1/favourites/{destination_hash}/identify-on-connect")
    async def favourites_identify_on_connect(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )
        if not isinstance(data, dict):
            return web.json_response(
                {"message": "Invalid request body"},
                status=400,
            )

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
    @routes.delete("/api/v1/favourites/{destination_hash}")
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
    @routes.post("/api/v1/favourites/import")
    async def favourites_import(request):
        try:
            data = await request.json()
            entries = data.get("favourites", [])
            if not isinstance(entries, list):
                return web.json_response(
                    {
                        "message": "Invalid import format: favourites must be an array",
                    },
                    status=400,
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
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to import favourites: {e!s}"},
                status=500,
            )
