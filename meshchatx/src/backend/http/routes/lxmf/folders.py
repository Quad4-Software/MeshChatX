# SPDX-License-Identifier: 0BSD
"""HTTP routes: lxmf folders."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.lxmf._names import *  # noqa: F403, F405


def register_lxmf_folders_routes(routes, app):

    @routes.get("/api/v1/lxmf/folders")
    async def lxmf_folders_get(request):
        unavailable = require_database(app)
        if unavailable is not None:
            return unavailable
        try:
            folders = app.database.messages.get_all_folders()
            return web.json_response([dict(f) for f in folders])
        except Exception as e:
            return http_for_database_exception(e)

    @routes.post("/api/v1/lxmf/folders")
    async def lxmf_folders_post(request):
        data = await request.json()
        name = data.get("name")
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        try:
            app.database.messages.create_folder(name)
            return web.json_response({"message": "Folder created"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/lxmf/folders/{id}")
    async def lxmf_folders_patch(request):
        folder_id = int(request.match_info["id"])
        data = await request.json()
        name = data.get("name")
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        app.database.messages.rename_folder(folder_id, name)
        return web.json_response({"message": "Folder renamed"})

    @routes.delete("/api/v1/lxmf/folders/{id}")
    async def lxmf_folders_delete(request):
        folder_id = int(request.match_info["id"])
        app.database.messages.delete_folder(folder_id)
        return web.json_response({"message": "Folder deleted"})

    @routes.get("/api/v1/lxmf/sieve-filters")
    async def lxmf_sieve_filters_get(request):
        raw = app.config.lxmf_sieve_filters_json.get()
        return web.json_response(
            {
                "filters": parse_lxmf_sieve_filters_json(raw),
            },
        )

    @routes.put("/api/v1/lxmf/sieve-filters")
    async def lxmf_sieve_filters_put(request):
        data = await request.json()
        filters = data.get("filters")
        if not isinstance(filters, list):
            return web.json_response(
                {"message": "filters must be a list"},
                status=400,
            )
        normalized = normalize_lxmf_sieve_filters(filters)
        folder_rows = app.database.messages.get_all_folders()
        valid_folder_ids = {f["id"] for f in folder_rows}
        for r in normalized:
            if r["action"] == "folder" and r["folder_id"] not in valid_folder_ids:
                return web.json_response(
                    {"message": f"Unknown folder_id {r['folder_id']}"},
                    status=400,
                )
        app.config.lxmf_sieve_filters_json.set(json.dumps(normalized))
        return web.json_response({"filters": normalized})

    @routes.get("/api/v1/lxmf/folders/export")
    async def lxmf_folders_export(request):
        folders = [dict(f) for f in app.database.messages.get_all_folders()]
        mappings = [
            dict(m) for m in app.database.messages.get_all_conversation_folders()
        ]
        return web.json_response({"folders": folders, "mappings": mappings})

    @routes.post("/api/v1/lxmf/folders/import")
    async def lxmf_folders_import(request):
        data = await request.json()
        folders = data.get("folders", [])
        mappings = data.get("mappings", [])

        # We'll try to recreate folders by name to avoid ID conflicts
        folder_name_to_new_id = {}
        for f in folders:
            try:
                app.database.messages.create_folder(f["name"])
            except Exception as e:
                logger.debug(f"Folder '{f['name']}' likely already exists: {e}")

        # Refresh folder list to get new IDs
        all_folders = app.database.messages.get_all_folders()
        for f in all_folders:
            folder_name_to_new_id[f["name"]] = f["id"]

        # Map old IDs to new IDs if possible, or just use names if we had them
        # Since IDs might change, we should have exported names too
        # Let's assume the export had folder names in mappings or we match by old folder info
        old_id_to_name = {f["id"]: f["name"] for f in folders}

        for m in mappings:
            peer_hash = m["peer_hash"]
            old_folder_id = m["folder_id"]
            folder_name = old_id_to_name.get(old_folder_id)
            if folder_name and folder_name in folder_name_to_new_id:
                new_folder_id = folder_name_to_new_id[folder_name]
                app.database.messages.move_conversation_to_folder(
                    peer_hash,
                    new_folder_id,
                )

        return web.json_response({"message": "Folders and mappings imported"})

    # mark lxmf conversation as read
