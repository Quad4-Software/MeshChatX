# SPDX-License-Identifier: 0BSD
"""HTTP routes: app_info shutdown."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.app_info._names import *  # noqa: F403, F405


def register_app_info_shutdown_routes(routes, app):

    # shutdown app
    @routes.post("/api/v1/app/shutdown")
    async def app_shutdown(request):
        # perform shutdown in a separate task so we can respond to the request
        async def do_shutdown():
            await asyncio.sleep(0.5)  # give some time for the response to be sent
            await app.shutdown(None)
            app.exit_app(0)

        asyncio.create_task(do_shutdown())
        return web.json_response({"message": "Shutting down..."})

    # get docs status
