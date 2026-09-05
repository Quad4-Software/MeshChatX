# SPDX-License-Identifier: 0BSD
"""HTTP routes: map overlays."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.map._names import *  # noqa: F403, F405


def register_map_overlays_routes(routes, app):

    @routes.get("/api/v1/map/overlays")
    async def list_map_overlays(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        identity_hash = app.identity.hash.hex()
        overlays = app.map_overlay_manager.list_overlays(identity_hash)
        return web.json_response({"overlays": overlays})

    @routes.post("/api/v1/map/overlays")
    async def create_map_overlays(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.create_overlays(
                identity_hash,
                data,
            )
        except OverlaySourceParseError as exc:
            return web.json_response({"error": exc.code}, status=400)
        except GeoValidationError as exc:
            return web.json_response({"error": exc.code}, status=400)
        return web.json_response(result)

    @routes.post("/api/v1/map/overlays/export")
    async def export_map_overlays_many(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        fmt = str(data.get("format") or "geojson").lower()
        ids = data.get("ids") or []
        if not isinstance(ids, list):
            return web.json_response({"error": "missing_ids"}, status=400)
        try:
            overlay_ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return web.json_response({"error": "missing_ids"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            body, content_type, filename = app.map_overlay_manager.export_many(
                identity_hash,
                overlay_ids,
                fmt,
            )
        except OverlayExportError as exc:
            status = 404 if exc.code == "cache_missing" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @routes.get("/api/v1/map/overlays/jobs/{job_id}")
    async def get_map_overlay_job(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        job_id = request.match_info.get("job_id")
        identity_hash = app.identity.hash.hex()
        job = app.map_overlay_manager.get_job(job_id, identity_hash=identity_hash)
        if not job:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response(job)

    @routes.post("/api/v1/map/overlays/jobs/{job_id}/cancel")
    async def cancel_map_overlay_job(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        job_id = request.match_info.get("job_id")
        identity_hash = app.identity.hash.hex()
        ok = app.map_overlay_manager.cancel_job(job_id, identity_hash=identity_hash)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"cancelled": True})

    @routes.post("/api/v1/map/overlays/{overlay_id}/refresh")
    async def refresh_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.refresh_overlay(
                identity_hash,
                overlay_id,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.json_response(result)

    @routes.patch("/api/v1/map/overlays/{overlay_id}")
    async def patch_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        try:
            data = await request.json()
        except (json.JSONDecodeError, ValueError):
            return web.json_response({"error": "invalid_json"}, status=400)
        identity_hash = app.identity.hash.hex()
        try:
            overlay = app.map_overlay_manager.patch_overlay(
                identity_hash,
                overlay_id,
                data,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.json_response({"overlay": overlay})

    @routes.delete("/api/v1/map/overlays/{overlay_id}")
    async def delete_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        ok = app.map_overlay_manager.delete_overlay(identity_hash, overlay_id)
        if not ok:
            return web.json_response({"error": "not_found"}, status=404)
        return web.json_response({"deleted": True})

    @routes.get("/api/v1/map/overlays/{overlay_id}/content")
    async def get_map_overlay_content(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        identity_hash = app.identity.hash.hex()
        cached = app.map_overlay_manager.read_cache_bytes(
            identity_hash,
            overlay_id,
        )
        if not cached:
            return web.json_response({"error": "cache_missing"}, status=404)
        data, fmt = cached
        from meshchatx.src.backend.map_overlay_export import CONTENT_TYPES

        return web.Response(
            body=data,
            headers={
                "Content-Type": CONTENT_TYPES.get(fmt, "application/octet-stream"),
            },
        )

    @routes.get("/api/v1/map/overlays/{overlay_id}/export")
    async def export_map_overlay(request):
        if not app.map_overlay_manager:
            return web.json_response({"error": "unavailable"}, status=503)
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return web.json_response({"error": "not_found"}, status=404)
        fmt = str(request.rel_url.query.get("format") or "geojson").lower()
        identity_hash = app.identity.hash.hex()
        try:
            body, content_type, filename = app.map_overlay_manager.export_overlay(
                identity_hash,
                overlay_id,
                fmt,
            )
        except OverlayExportError as exc:
            status = 404 if exc.code == "cache_missing" else 400
            return web.json_response({"error": exc.code}, status=status)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
