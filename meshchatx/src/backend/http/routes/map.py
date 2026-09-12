# SPDX-License-Identifier: 0BSD
"""HTTP routes: map."""

from __future__ import annotations

import base64
import binascii
import json
import math
import os
import secrets

import RNS
from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error,
    http_error_from_exception,
    http_forbidden,
    http_not_found,
    http_payload_too_large,
    http_unavailable,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    UPLOAD_LIMITS,
    PayloadTooLargeError,
    read_json_limited,
    write_field_to_path,
)
from meshchatx.src.backend.map_geo_validator import GeoValidationError
from meshchatx.src.backend.map_manager import (
    MAX_EXPORT_TILES,
    MAX_EXPORT_ZOOM,
    TRANSPARENT_TILE,
    is_mbtiles_filename,
)
from meshchatx.src.backend.map_overlay_export import OverlayExportError
from meshchatx.src.backend.map_overlay_sources import OverlaySourceParseError
from meshchatx.src.backend.privacy_mode import OutboundHttpBlockedError
from meshchatx.src.path_utils import is_path_within_dir


def register_map_routes(routes, app):
    # get offline map metadata
    @routes.get(API_V1_PREFIX + "/map/offline")
    async def get_map_offline_metadata(request):
        metadata = app.map_manager.get_metadata()
        if not metadata:
            app.map_manager.ensure_starter_mbtiles()
            metadata = app.map_manager.get_metadata()
        if metadata:
            return web.json_response(metadata)
        return web.json_response({"loaded": False})

    @routes.post(API_V1_PREFIX + "/map/mbtiles/restore-starter")
    async def restore_starter_mbtiles(request):
        path = app.map_manager.ensure_starter_mbtiles(force_restore=True)
        if not path:
            return http_unexpected("Could not restore starter tiles")
        return web.json_response(
            {
                "message": "Starter tiles restored",
                "path": path,
                "metadata": app.map_manager.get_metadata(),
            },
        )

    # get map tile

    # get map tile
    @routes.get(API_V1_PREFIX + "/map/tiles/{z}/{x}/{y}")
    async def get_map_tile(request):
        try:
            z = int(request.match_info.get("z"))
            x = int(request.match_info.get("x"))
            y_str = request.match_info.get("y")
            # remove .png if present
            y_str = y_str.removesuffix(".png")
            y = int(y_str)

            tile_data = app.map_manager.get_tile(z, x, y)
            if tile_data:
                return web.Response(body=tile_data, content_type="image/png")

            # If tile not found, return a transparent 1x1 PNG instead of 404
            # to avoid browser console errors in offline mode.
            return web.Response(body=TRANSPARENT_TILE, content_type="image/png")
        except Exception:
            return web.Response(status=400)

    # list available MBTiles files

    # list available MBTiles files
    @routes.get(API_V1_PREFIX + "/map/mbtiles")
    async def list_mbtiles(request):
        return web.json_response(app.map_manager.list_mbtiles())

    # delete an MBTiles file

    # delete an MBTiles file
    @routes.delete(API_V1_PREFIX + "/map/mbtiles/{filename}")
    async def delete_mbtiles(request):
        filename = request.match_info.get("filename")
        if app.map_manager.delete_mbtiles(filename):
            return web.json_response({"message": "File deleted"})
        return http_not_found("File not found")

    # set active MBTiles file

    # set active MBTiles file
    @routes.post(API_V1_PREFIX + "/map/mbtiles/active")
    async def set_active_mbtiles(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        filename = data.get("filename")
        if filename is not None and (
            not isinstance(filename, str) or "\x00" in filename
        ):
            return http_bad_request("Invalid filename")
        if not filename:
            app.config.map_offline_path.set(None)
            app.config.map_offline_enabled.set(False)
            return web.json_response({"message": "Offline map disabled"})

        mbtiles_dir = app.map_manager.get_mbtiles_dir()
        safe_name = os.path.basename(filename)
        file_path = os.path.join(mbtiles_dir, safe_name)
        if not is_path_within_dir(file_path, mbtiles_dir):
            return http_bad_request("Invalid filename")
        if os.path.exists(file_path):
            app.map_manager.close()
            app.config.map_offline_path.set(file_path)
            app.config.map_offline_enabled.set(True)
            return web.json_response(
                {
                    "message": "Active map updated",
                    "metadata": app.map_manager.get_metadata(),
                },
            )
        return http_not_found("File not found")

    # map drawings

    # map drawings
    @routes.get(API_V1_PREFIX + "/map/drawings")
    async def get_map_drawings(request):
        identity_hash = app.identity.hash.hex()
        rows = app.database.map_drawings.get_drawings(identity_hash)
        drawings = [dict(row) for row in rows]
        return web.json_response({"drawings": drawings})

    @routes.post(API_V1_PREFIX + "/map/drawings")
    async def save_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        drawing_data = data.get("data")
        app.database.map_drawings.upsert_drawing(identity_hash, name, drawing_data)
        return web.json_response({"message": "Drawing saved successfully"})

    @routes.delete(API_V1_PREFIX + "/map/drawings/{drawing_id}")
    async def delete_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        drawing_id = request.match_info.get("drawing_id")
        deleted = app.database.map_drawings.delete_drawing(
            drawing_id,
            identity_hash,
        )
        if not deleted:
            return http_not_found("Drawing not found")
        return web.json_response({"message": "Drawing deleted successfully"})

    @routes.patch(API_V1_PREFIX + "/map/drawings/{drawing_id}")
    async def update_map_drawing(request):
        identity_hash = app.identity.hash.hex()
        drawing_id = request.match_info.get("drawing_id")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        name = data.get("name")
        drawing_data = data.get("data")
        updated = app.database.map_drawings.update_drawing(
            drawing_id,
            identity_hash,
            name,
            drawing_data,
        )
        if not updated:
            return http_not_found("Drawing not found")
        return web.json_response({"message": "Drawing updated successfully"})

    @routes.get(API_V1_PREFIX + "/map/overlays")
    async def list_map_overlays(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        identity_hash = app.identity.hash.hex()
        overlays = app.map_overlay_manager.list_overlays(identity_hash)
        return web.json_response({"overlays": overlays})

    @routes.post(API_V1_PREFIX + "/map/overlays")
    async def create_map_overlays(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.create_overlays(
                identity_hash,
                data,
            )
        except OverlaySourceParseError as exc:
            return http_bad_request(exc.code)
        except GeoValidationError as exc:
            return http_bad_request(exc.code)
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/map/overlays/export")
    async def export_map_overlays_many(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        fmt = str(data.get("format") or "geojson").lower()
        ids = data.get("ids") or []
        if not isinstance(ids, list):
            return http_bad_request("missing_ids")
        try:
            overlay_ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return http_bad_request("missing_ids")
        identity_hash = app.identity.hash.hex()
        try:
            body, content_type, filename = app.map_overlay_manager.export_many(
                identity_hash,
                overlay_ids,
                fmt,
            )
        except OverlayExportError as exc:
            status = 404 if exc.code == "cache_missing" else 400
            return http_error(status, exc.code)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    @routes.get(API_V1_PREFIX + "/map/overlays/jobs/{job_id}")
    async def get_map_overlay_job(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        job_id = request.match_info.get("job_id")
        identity_hash = app.identity.hash.hex()
        job = app.map_overlay_manager.get_job(job_id, identity_hash=identity_hash)
        if not job:
            return http_not_found("not_found")
        return web.json_response(job)

    @routes.post(API_V1_PREFIX + "/map/overlays/jobs/{job_id}/cancel")
    async def cancel_map_overlay_job(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        job_id = request.match_info.get("job_id")
        identity_hash = app.identity.hash.hex()
        ok = app.map_overlay_manager.cancel_job(job_id, identity_hash=identity_hash)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"cancelled": True})

    @routes.post(API_V1_PREFIX + "/map/overlays/{overlay_id}/refresh")
    async def refresh_map_overlay(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return http_not_found("not_found")
        identity_hash = app.identity.hash.hex()
        try:
            result = await app.map_overlay_manager.refresh_overlay(
                identity_hash,
                overlay_id,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return http_error(status, exc.code)
        return web.json_response(result)

    @routes.patch(API_V1_PREFIX + "/map/overlays/{overlay_id}")
    async def patch_map_overlay(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return http_not_found("not_found")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        identity_hash = app.identity.hash.hex()
        try:
            overlay = app.map_overlay_manager.patch_overlay(
                identity_hash,
                overlay_id,
                data,
            )
        except OverlaySourceParseError as exc:
            status = 404 if exc.code == "not_found" else 400
            return http_error(status, exc.code)
        return web.json_response({"overlay": overlay})

    @routes.delete(API_V1_PREFIX + "/map/overlays/{overlay_id}")
    async def delete_map_overlay(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return http_not_found("not_found")
        identity_hash = app.identity.hash.hex()
        ok = app.map_overlay_manager.delete_overlay(identity_hash, overlay_id)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"deleted": True})

    @routes.get(API_V1_PREFIX + "/map/overlays/{overlay_id}/content")
    async def get_map_overlay_content(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return http_not_found("not_found")
        identity_hash = app.identity.hash.hex()
        cached = app.map_overlay_manager.read_cache_bytes(
            identity_hash,
            overlay_id,
        )
        if not cached:
            return http_not_found("cache_missing")
        data, fmt = cached
        from meshchatx.src.backend.map_overlay_export import CONTENT_TYPES

        return web.Response(
            body=data,
            headers={
                "Content-Type": CONTENT_TYPES.get(fmt, "application/octet-stream"),
            },
        )

    @routes.get(API_V1_PREFIX + "/map/overlays/{overlay_id}/export")
    async def export_map_overlay(request):
        if not app.map_overlay_manager:
            return http_unavailable("unavailable")
        try:
            overlay_id = int(request.match_info.get("overlay_id"))
        except (TypeError, ValueError):
            return http_not_found("not_found")
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
            return http_error(status, exc.code)
        return web.Response(
            body=body,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    # upload offline map
    @routes.post(API_V1_PREFIX + "/map/offline")
    async def upload_map_offline(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field.name != "file":
                return http_bad_request("No file field")

            filename = os.path.basename(field.filename or "")
            if not is_mbtiles_filename(filename):
                return http_bad_request("Invalid file format, must be .mbtiles")

            mbtiles_dir = app.map_manager.get_mbtiles_dir()
            if not os.path.exists(mbtiles_dir):
                os.makedirs(mbtiles_dir)

            dest_path = os.path.join(mbtiles_dir, filename)
            if not is_path_within_dir(dest_path, mbtiles_dir):
                return http_bad_request("Invalid filename")

            await write_field_to_path(
                field,
                dest_path,
                UPLOAD_LIMITS["map_offline_mbtiles"],
            )

            # close old connection and clear cache before update
            app.map_manager.close()

            # update config
            app.config.map_offline_path.set(dest_path)
            app.config.map_offline_enabled.set(True)

            # validate
            metadata = app.map_manager.get_metadata()
            if not metadata:
                # delete if invalid
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                app.config.map_offline_path.set(None)
                app.config.map_offline_enabled.set(False)
                return http_bad_request(
                    "Invalid MBTiles file or unsupported format (vector maps not supported)"
                )

            return web.json_response(
                {
                    "message": "Map uploaded successfully",
                    "metadata": metadata,
                },
            )
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception as e:
            RNS.log(f"Error uploading map: {e}", RNS.LOG_ERROR)
            return http_error_from_exception(e, fallback_status=500)

    # start map export

    # start map export
    @routes.post(API_V1_PREFIX + "/map/export")
    async def start_map_export(request):
        try:
            data = await read_json_limited(request)
            if not isinstance(data, dict):
                return http_bad_request("Invalid body")
            bbox = data.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
            try:
                min_zoom = int(data.get("min_zoom", 0))
                max_zoom = int(data.get("max_zoom", 10))
            except (TypeError, ValueError):
                return http_bad_request("Invalid zoom levels")
            name = data.get("name", "Exported Map")

            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                return http_bad_request("Invalid bbox")
            try:
                bbox = [float(v) for v in bbox]
            except (TypeError, ValueError):
                return http_bad_request("Invalid bbox")
            if not all(math.isfinite(v) for v in bbox):
                return http_bad_request("Invalid bbox")
            if not (0 <= min_zoom <= max_zoom <= MAX_EXPORT_ZOOM):
                return http_bad_request(
                    f"Invalid zoom range; "
                    f"allowed is 0 <= min_zoom <= max_zoom <= "
                    f"{MAX_EXPORT_ZOOM}."
                )

            app._require_outbound_http("map tile export")

            tile_count = app.map_manager.count_export_tiles(
                bbox,
                min_zoom,
                max_zoom,
                limit=MAX_EXPORT_TILES,
            )
            if tile_count > MAX_EXPORT_TILES:
                return http_bad_request(
                    f"Export would download more than "
                    f"{MAX_EXPORT_TILES} tiles; "
                    f"maximum allowed is {MAX_EXPORT_TILES}. "
                    "Shrink the area or lower max zoom."
                )

            export_id = secrets.token_hex(8)
            app.map_manager.start_export(export_id, bbox, min_zoom, max_zoom, name)

            return web.json_response({"export_id": export_id})
        except PayloadTooLargeError:
            return http_payload_too_large()
        except OutboundHttpBlockedError as e:
            return http_forbidden(str(e))
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # get map export status

    # get map export status
    @routes.get(API_V1_PREFIX + "/map/export/{export_id}")
    async def get_map_export_status(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status:
            return web.json_response(status)
        return http_not_found("Export not found")

    # download exported map

    # download exported map
    @routes.get(API_V1_PREFIX + "/map/export/{export_id}/download")
    async def download_map_export(request):
        export_id = request.match_info.get("export_id")
        status = app.map_manager.get_export_status(export_id)
        if status and status.get("status") == "completed":
            file_path = status.get("file_path")
            if os.path.exists(file_path):
                return web.FileResponse(
                    path=file_path,
                    headers={
                        "Content-Disposition": f'attachment; filename="map_export_{export_id}.mbtiles"',
                    },
                )
        return http_not_found("File not ready or not found")

    # cancel/delete map export

    # cancel/delete map export
    @routes.delete(API_V1_PREFIX + "/map/export/{export_id}")
    async def delete_map_export(request):
        export_id = request.match_info.get("export_id")
        if app.map_manager.cancel_export(export_id):
            return web.json_response({"message": "Export cancelled/deleted"})
        return http_not_found("Export not found")

    @routes.get(API_V1_PREFIX + "/map/data/status")
    async def map_data_status(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        return web.json_response(app.map_data_manager.status())

    @routes.get(API_V1_PREFIX + "/map/data/published")
    async def map_data_published(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        return web.json_response({"maps": app.map_data_manager.list_published()})

    @routes.get(API_V1_PREFIX + "/map/data/heard")
    async def map_data_heard(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        query = request.query.get("search") or request.query.get("q")
        try:
            limit = int(request.query.get("limit") or 250)
        except (TypeError, ValueError):
            limit = 250
        limit = max(1, min(limit, 2500))
        return web.json_response(
            {"announces": app.map_data_manager.list_heard(query=query, limit=limit)},
        )

    @routes.post(API_V1_PREFIX + "/map/data/publish")
    async def map_data_publish(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        name = str(data.get("name") or "map")
        hinted = data.get("format")
        raw_b64 = data.get("data_b64") or data.get("content_b64")
        if not isinstance(raw_b64, str) or not raw_b64.strip():
            return http_bad_request("missing_data")
        max_bytes = 512 * 1024
        try:
            configured = app.map_data_manager._cfg_max_bytes()
        except (TypeError, ValueError, AttributeError):
            configured = None
        if isinstance(configured, int) and configured >= 1:
            max_bytes = configured
        if len(raw_b64) > (max_bytes * 4 // 3) + 8:
            return http_bad_request("file_too_large")
        try:
            payload = base64.b64decode(raw_b64, validate=True)
        except (binascii.Error, ValueError):
            return http_bad_request("invalid_data")
        try:
            result = app.map_data_manager.publish_bytes(
                payload,
                name=name,
                hinted_format=hinted,
            )
        except MapDataError as exc:
            return http_bad_request(exc.code)
        except GeoValidationError as exc:
            return http_bad_request(exc.code)
        return web.json_response(result)

    @routes.delete(API_V1_PREFIX + "/map/data/published/{map_id}")
    async def map_data_unpublish(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        map_id = request.match_info.get("map_id")
        try:
            ok = app.map_data_manager.unpublish(map_id)
        except MapDataError as exc:
            return http_bad_request(exc.code)
        if not ok:
            return http_not_found("not_found")
        return web.json_response({"deleted": True})

    @routes.post(API_V1_PREFIX + "/map/data/announce")
    async def map_data_announce(_request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            return web.json_response(app.map_data_manager.announce())
        except MapDataError as exc:
            return http_bad_request(exc.code)

    @routes.patch(API_V1_PREFIX + "/map/data/config")
    async def map_data_config(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        return web.json_response(
            app.map_data_manager.update_settings(
                display_name=data.get("display_name"),
                announce_enabled=data.get("announce_enabled"),
                announce_interval=data.get("announce_interval"),
            ),
        )

    @routes.post(API_V1_PREFIX + "/map/data/catalog")
    async def map_data_catalog(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        try:
            result = await app.map_data_manager.fetch_catalog(dest)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        return web.json_response(result)

    @routes.post(API_V1_PREFIX + "/map/data/fetch")
    async def map_data_fetch(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        map_id = data.get("map_id")
        try:
            body = await app.map_data_manager.fetch_map_bytes(dest, map_id)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        return web.json_response(
            {
                "data_b64": base64.b64encode(body).decode("ascii"),
                "size": len(body),
            },
        )

    @routes.post(API_V1_PREFIX + "/map/data/add-overlay")
    async def map_data_add_overlay(request):
        if not app.map_data_manager:
            return http_unavailable("unavailable")
        from meshchatx.src.backend.map_data_manager import MapDataError

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except (json.JSONDecodeError, ValueError):
            return http_bad_request("invalid_json")
        dest = data.get("destination_hash")
        map_id = data.get("map_id")
        try:
            result = await app.map_data_manager.add_as_overlay(dest, map_id)
        except MapDataError as exc:
            status = 400
            if exc.code in (
                "missing_path",
                "link_failed",
                "job_timeout",
                "request_failed",
                "empty_response",
                "invalid_response",
            ):
                status = 503
            return http_error(status, exc.code)
        except OverlaySourceParseError as exc:
            return http_bad_request(exc.code)
        except GeoValidationError as exc:
            return http_bad_request(exc.code)
        return web.json_response(result)

    # MIME type fix middleware - ensures JavaScript files have correct Content-Type
