# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe path_table."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.path_probe._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)



def register_path_probe_path_table_routes(routes, app):

    # get path table
    @routes.get("/api/v1/path-table")
    @routes.post("/api/v1/path-table")
    async def path_table(request):
        limit = request.query.get("limit", None)
        offset = request.query.get("offset", None)
        destination_hashes = None
        if request.method == "POST":
            try:
                body = await read_json_limited(request)
                destination_hashes = body.get("destination_hashes")
                if destination_hashes and not isinstance(destination_hashes, list):
                    destination_hashes = None
            except PayloadTooLargeError:
                return http_payload_too_large()
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

    # derive lxmf delivery address from an identity hash

    @routes.get("/api/v1/identity/{identity_hash}/lxmf-address")
    async def identity_lxmf_address(request):
        raw = request.match_info.get("identity_hash", "")
        norm = normalize_hex_identifier(raw)
        # Identity hashes are 16 bytes (32 hex); 32-byte (64 hex) forms are
        # tolerated to match parse_identity_hash.
        if len(norm) not in (32, 64):
            return http_bad_request("invalid identity hash")

        lxmf_hex = await asyncio.to_thread(
            app.get_lxmf_destination_hash_for_identity_hash,
            norm,
        )
        if not lxmf_hex:
            return http_not_found("no LXMF address could be derived for this identity")

        has_path = False
        try:
            has_path = RNS.Transport.has_path(bytes.fromhex(lxmf_hex))
        except Exception:
            pass

        return web.json_response(
            {
                "identity_hash": norm,
                "lxmf_destination_hash": lxmf_hex,
                "has_path": has_path,
            },
        )

    # send lxmf message
