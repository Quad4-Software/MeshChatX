# SPDX-License-Identifier: 0BSD
"""HTTP routes: config/config."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.config._names import *  # noqa: F403


def register_config_config_routes(routes: Any, app: Any) -> None:

    # get config

    @routes.get("/api/v1/config")
    async def config_get(request):
        return web.json_response(
            {
                "config": app.get_config_dict(),
            },
        )

    @routes.patch("/api/v1/config")
    async def config_update(request):
        # get request body as json
        try:
            data = await request.json()
            await app.update_config(data)
            try:
                AsyncUtils.run_async(app.send_config_to_websocket_clients())
            except Exception as e:
                print(f"Failed to broadcast config update: {e}")

            return web.json_response(
                {
                    "config": app.get_config_dict(),
                },
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except Exception:
            import traceback

            print("config_update failed:\n" + traceback.format_exc())
            return web.json_response({"error": "config_update_failed"}, status=500)
