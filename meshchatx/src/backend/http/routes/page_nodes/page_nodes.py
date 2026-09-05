# SPDX-License-Identifier: 0BSD
"""HTTP routes: page_nodes/page_nodes."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.page_nodes._names import *  # noqa: F403


def register_page_nodes_page_nodes_routes(routes: Any, app: Any) -> None:

    # --- Page Node API ---

    @routes.get("/api/v1/page-nodes")
    async def page_nodes_list(request):
        return web.json_response(app.page_node_manager.list_nodes())

    @routes.post("/api/v1/page-nodes")
    async def page_nodes_create(request):
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return web.json_response({"message": "Name is required"}, status=400)
        announce_enabled = bool(data.get("announce_enabled", True))
        announce_interval_seconds = data.get("announce_interval_seconds")
        executable_pages_enabled = bool(data.get("executable_pages_enabled", False))
        node = app.page_node_manager.create_node(
            name,
            announce_enabled=announce_enabled,
            announce_interval_seconds=announce_interval_seconds,
            executable_pages_enabled=executable_pages_enabled,
        )
        return web.json_response(node.get_status())

    @routes.get("/api/v1/page-nodes/{node_id}")
    async def page_nodes_get(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response(node.get_status())

    @routes.delete("/api/v1/page-nodes/{node_id}")
    async def page_nodes_delete(request):
        node_id = request.match_info["node_id"]
        if app.page_node_manager.delete_node(node_id):
            return web.json_response({"message": "Node deleted"})
        return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/start")
    async def page_nodes_start(request):
        node_id = request.match_info["node_id"]
        try:
            dest_hash = app.page_node_manager.start_node(node_id)
            node = app.page_node_manager.get_node(node_id)
            if node and node.running:
                app._register_local_page_node_announce(node)
            return web.json_response(
                {"destination_hash": dest_hash, "message": "Node started"},
            )
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/stop")
    async def page_nodes_stop(request):
        node_id = request.match_info["node_id"]
        try:
            app.page_node_manager.stop_node(node_id)
            return web.json_response({"message": "Node stopped"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.post("/api/v1/page-nodes/{node_id}/announce")
    async def page_nodes_announce(request):
        node_id = request.match_info["node_id"]
        try:
            node = app.page_node_manager.get_node(node_id)
            if node is None or not node.running:
                return web.json_response(
                    {"message": "Node not running"},
                    status=400,
                )
            node.announce()
            app._register_local_page_node_announce(node)
            return web.json_response({"message": "Announced"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.put("/api/v1/page-nodes/{node_id}/rename")
    async def page_nodes_rename(request):
        node_id = request.match_info["node_id"]
        data = await request.json()
        new_name = data.get("name", "").strip()
        if not new_name:
            return web.json_response({"message": "Name is required"}, status=400)
        try:
            app.page_node_manager.rename_node(node_id, new_name)
            return web.json_response({"message": "Renamed"})
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.patch("/api/v1/page-nodes/{node_id}/announce-settings")
    async def page_nodes_update_announce_settings(request):
        node_id = request.match_info["node_id"]
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid request body: {e}"},
                status=400,
            )
        announce_enabled = (
            data.get("announce_enabled") if "announce_enabled" in data else None
        )
        announce_interval_seconds = (
            data.get("announce_interval_seconds")
            if "announce_interval_seconds" in data
            else None
        )
        executable_pages_enabled = (
            data.get("executable_pages_enabled")
            if "executable_pages_enabled" in data
            else None
        )
        try:
            node = app.page_node_manager.get_node(node_id)
            if node is None:
                return web.json_response({"message": "Node not found"}, status=404)
            node = app.page_node_manager.set_announce_settings(
                node_id,
                announce_enabled=announce_enabled,
                announce_interval_seconds=announce_interval_seconds,
            )
            if executable_pages_enabled is not None:
                node = app.page_node_manager.set_executable_pages_enabled(
                    node_id,
                    bool(executable_pages_enabled),
                )
            return web.json_response(node.get_status())
        except KeyError:
            return web.json_response({"message": "Node not found"}, status=404)

    @routes.get("/api/v1/page-nodes/{node_id}/pages")
    async def page_nodes_list_pages(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response({"pages": node.list_pages()})

    @routes.post("/api/v1/page-nodes/{node_id}/pages")
    async def page_nodes_add_page(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid request body: {e}"},
                status=400,
            )
        name = data.get("name", "")
        content = data.get("content", "")
        executable = data.get("executable") if "executable" in data else None
        if not name:
            return web.json_response(
                {"message": "Page name is required"},
                status=400,
            )
        try:
            saved_name = node.add_page(name, content, executable=executable)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OSError as e:
            return web.json_response(
                {"message": f"Failed to write page: {e}"},
                status=500,
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to save page: {e}"},
                status=500,
            )
        return web.json_response(
            {
                "name": saved_name,
                "executable": node.is_page_executable(saved_name),
                "message": "Page saved",
            },
        )

    @routes.get("/api/v1/page-nodes/{node_id}/pages/{page_name}")
    async def page_nodes_get_page(request):
        node_id = request.match_info["node_id"]
        page_name = request.match_info["page_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        content = node.get_page_content(page_name)
        if content is None:
            return web.json_response({"message": "Page not found"}, status=404)
        return web.json_response(
            {
                "name": page_name,
                "content": content,
                "executable": node.is_page_executable(page_name),
            },
        )

    @routes.delete("/api/v1/page-nodes/{node_id}/pages/{page_name}")
    async def page_nodes_delete_page(request):
        node_id = request.match_info["node_id"]
        page_name = request.match_info["page_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        if node.remove_page(page_name):
            return web.json_response({"message": "Page deleted"})
        return web.json_response({"message": "Page not found"}, status=404)

    @routes.get("/api/v1/page-nodes/{node_id}/files")
    async def page_nodes_list_files(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        return web.json_response({"files": node.list_files()})

    @routes.post("/api/v1/page-nodes/{node_id}/files")
    async def page_nodes_upload_file(request):
        node_id = request.match_info["node_id"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        try:
            reader = await request.multipart()
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid upload request: {e}"},
                status=400,
            )
        filename = None
        file_data = None
        try:
            while True:
                field = await reader.next()
                if field is None:
                    break
                name = field.name or ""
                if name == "file" or field.filename:
                    filename = field.filename or "upload"
                    file_data = await field.read()
                else:
                    with contextlib.suppress(Exception):
                        await field.read()
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to read upload: {e}"},
                status=400,
            )
        if file_data is None:
            return web.json_response({"message": "No file uploaded"}, status=400)
        try:
            saved_name = node.add_file(filename, file_data)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OSError as e:
            return web.json_response(
                {"message": f"Failed to write file: {e}"},
                status=500,
            )
        except Exception as e:
            return web.json_response(
                {"message": f"Failed to save file: {e}"},
                status=500,
            )
        return web.json_response({"name": saved_name, "message": "File uploaded"})

    @routes.delete("/api/v1/page-nodes/{node_id}/files/{file_name}")
    async def page_nodes_delete_file(request):
        node_id = request.match_info["node_id"]
        file_name = request.match_info["file_name"]
        node = app.page_node_manager.get_node(node_id)
        if not node:
            return web.json_response({"message": "Node not found"}, status=404)
        if node.remove_file(file_name):
            return web.json_response({"message": "File deleted"})
        return web.json_response({"message": "File not found"}, status=404)
