# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rnprobe."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers


def register_rn_tools_rnprobe_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    @routes.post("/api/v1/rnprobe")
    async def rnprobe(request):
        data = await request.json()
        destination_hash_str = data.get("destination_hash", "")
        full_name = data.get("full_name", "")
        try:
            size = int(data.get("size", RNProbeHandler.DEFAULT_PROBE_SIZE))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid size"}, status=400)
        try:
            wait = float(data.get("wait", 0))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid wait"}, status=400)
        try:
            probes = int(data.get("probes", 1))
        except (TypeError, ValueError):
            return web.json_response({"message": "Invalid probes"}, status=400)

        timeout = None
        raw_timeout = data.get("timeout", 0)
        if raw_timeout is not None:
            try:
                t = float(raw_timeout)
            except (TypeError, ValueError):
                return web.json_response({"message": "Invalid timeout"}, status=400)
            if t != 0:
                timeout = t

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return web.json_response(
                {"message": f"Invalid destination hash: {e}"},
                status=400,
            )

        if not full_name:
            return web.json_response(
                {"message": "full_name is required"},
                status=400,
            )

        not_ready = app._require_rns_tool_handler(app.rnprobe_handler, "RNProbe")
        if not_ready is not None:
            return not_ready

        try:
            result = await app.rnprobe_handler.probe_destination(
                destination_hash=destination_hash,
                full_name=full_name,
                size=size,
                timeout=timeout,
                wait=wait,
                probes=probes,
            )
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )
