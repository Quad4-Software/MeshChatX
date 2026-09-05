# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance config."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.reticulum_instance._names import *  # noqa: F403, F405


def register_reticulum_instance_config_routes(routes, app):

    @routes.get("/api/v1/reticulum/config/raw")
    async def reticulum_config_raw_get(request):
        """Return the raw text of the Reticulum config file.

        Used by the Reticulum Config Editor utility (mostly for mobile
        clients where the file is stored inside private app storage and
        cannot easily be opened with an external editor).
        """
        try:
            app._ensure_reticulum_config(materialize=False)
            config_path = app._reticulum_config_file_path()
            if not os.path.exists(config_path):
                return web.json_response(
                    {"error": f"Reticulum config not found at {config_path}"},
                    status=404,
                )
            with open(config_path) as f:
                content = f.read()
            return web.json_response(
                {
                    "content": content,
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.put("/api/v1/reticulum/config/raw")
    async def reticulum_config_raw_put(request):
        """Persist new raw text to the Reticulum config file.

        The body must be JSON with a content string. Basic validation
        requires the [reticulum] and [interfaces] sections so we
        do not write a config that would prevent RNS from starting on the
        next reload.
        """
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400,
            )

        content = data.get("content")
        if not isinstance(content, str):
            return web.json_response(
                {"error": "Missing or invalid 'content' field"},
                status=400,
            )

        if "[reticulum]" not in content or "[interfaces]" not in content:
            return web.json_response(
                {
                    "error": "Config must include [reticulum] and [interfaces] sections",
                },
                status=400,
            )

        try:
            config_dir = app._normalize_reticulum_config_dir(
                app.reticulum_config_dir,
            )
            if not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            config_path = app._reticulum_config_file_path()
            previous_interfaces = {}
            if os.path.isfile(config_path):
                try:
                    from RNS.vendor.configobj import ConfigObj

                    previous_interfaces = ConfigObj(config_path).get("interfaces") or {}
                except Exception:
                    previous_interfaces = {}
            i2p_raw_error = i2p_support.validate_raw_config_i2p_policy(
                content,
                previous_interfaces=previous_interfaces,
            )
            if i2p_raw_error is not None:
                return web.json_response(
                    {"error": i2p_raw_error},
                    status=422,
                )
            with open(config_path, "w") as f:
                f.write(content)
            i2p_support.guard_i2p_interfaces_in_config(config_path)
            app._sync_interfaces_from_disk(replace=True)
            return web.json_response(
                {
                    "message": "Reticulum config saved",
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/reticulum/config/reset")
    async def reticulum_config_reset(request):
        """Restore the Reticulum config file to RNS stock defaults."""
        try:
            app.reticulum_config_dir = app._normalize_reticulum_config_dir(
                app.reticulum_config_dir,
            )
            config_path = app._reticulum_config_file_path()
            default_text = app._write_rns_reticulum_default_config_file(
                config_path,
            )
            app._sync_interfaces_from_disk(replace=True)
            return web.json_response(
                {
                    "message": "Reticulum config restored to defaults",
                    "content": default_text,
                    "path": config_path,
                },
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
