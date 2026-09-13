# SPDX-License-Identifier: 0BSD
"""HTTP routes: shell/static."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.shell._names import *  # noqa: F403


def register_shell_static_routes(routes: Any, app: Any) -> None:
    @routes.get("/")
    async def index(request):
        index_path = app.get_public_path("index.html")
        if not os.path.exists(index_path):
            return web.Response(
                text="""
                    <html>
                        <head><title>MeshChatX - Frontend Missing</title></head>
                        <body style="font-family: sans-serif; padding: 2rem; line-height: 1.5; background: #0f172a; color: #f8fafc;">
                            <h1 style="color: #38bdf8;">Frontend Missing</h1>
                            <p>The MeshChatX web interface files were not found.</p>
                            <p>If you are running from source, you must build the frontend first:</p>
                            <pre style="background: #1e293b; padding: 1rem; border-radius: 4px; color: #e2e8f0; border: 1px solid #334155;">pnpm install && pnpm run build-frontend</pre>
                            <p>For more information, see the <a href="https://github.com/Quad4-Software/MeshChatX" style="color: #38bdf8;">README</a>.</p>
                        </body>
                    </html>
                    """,
                content_type="text/html",
                status=500,
            )
        return web.FileResponse(
            path=index_path,
            headers={
                # don't allow browser to store page in cache, otherwise new app versions may get stale ui
                "Cache-Control": "no-cache, no-store",
            },
        )

    @routes.get("/manifest.json")
    async def manifest(request):
        return web.FileResponse(app.get_public_path("manifest.json"))

    @routes.get("/service-worker.js")
    async def service_worker(request):
        return web.FileResponse(
            path=app.get_public_path("service-worker.js"),
            headers={
                "Cache-Control": "no-cache, max-age=0, must-revalidate",
            },
        )

    @routes.get("/call.html")
    async def call_html_redirect(request):
        return web.HTTPFound("/#/popout/call")
