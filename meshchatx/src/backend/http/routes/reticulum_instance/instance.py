# SPDX-License-Identifier: 0BSD
"""HTTP routes: reticulum_instance instance."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.reticulum_instance._names import *  # noqa: F403, F405
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_conflict,
    http_error_from_exception,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)



def register_reticulum_instance_instance_routes(routes, app):

    @routes.get("/api/v1/reticulum/instance")
    async def reticulum_instance_get(request):
        """Shared-instance, RPC, and hop-obfuscation settings (Sideband parity)."""
        return web.json_response(
            {"instance": app._build_reticulum_instance_settings()},
        )

    @routes.patch("/api/v1/reticulum/instance")
    async def reticulum_instance_patch(request):
        """Update [reticulum] shared-instance / hop-obfuscation options and reload."""
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")
        if not isinstance(data, dict):
            return http_bad_request("Invalid request body")

        reticulum_config = app._get_reticulum_section()
        changed = False

        bool_keys = (
            "share_instance",
            "local_hops_delta",
            "respond_to_probes",
            "enable_remote_management",
        )
        for key in bool_keys:
            if key not in data:
                continue
            reticulum_config[key] = app._format_rns_config_bool(
                app._parse_rns_config_bool(data.get(key), default=False),
            )
            changed = True

        if "instance_name" in data:
            name = data.get("instance_name")
            if name is None or str(name).strip() == "":
                reticulum_config.pop("instance_name", None)
            else:
                cleaned = str(name).strip()
                if len(cleaned) > 64 or any(c.isspace() for c in cleaned):
                    return http_bad_request(
                        "instance_name must be 1-64 characters without whitespace"
                    )
                reticulum_config["instance_name"] = cleaned
            changed = True

        if "shared_instance_type" in data:
            raw_type = data.get("shared_instance_type")
            if raw_type is None or str(raw_type).strip() == "":
                reticulum_config.pop("shared_instance_type", None)
            else:
                cleaned_type = str(raw_type).strip().lower()
                if cleaned_type not in ("tcp", "unix"):
                    return http_bad_request(
                        "shared_instance_type must be 'tcp' or 'unix'"
                    )
                reticulum_config["shared_instance_type"] = cleaned_type
            changed = True

        if "remote_management_allowed" in data:
            try:
                allowed = app._parse_rns_hash_list(
                    data.get("remote_management_allowed"),
                )
            except ValueError as e:
                return http_bad_request(str(e))
            if allowed:
                reticulum_config["remote_management_allowed"] = allowed
            else:
                reticulum_config.pop("remote_management_allowed", None)
            changed = True

        if not changed:
            return web.json_response(
                {"instance": app._build_reticulum_instance_settings()},
            )

        if not app._write_reticulum_config():
            return http_unexpected("Failed to write Reticulum config")

        try:
            reloaded = await app.reload_reticulum()
        except Exception as e:
            logger.debug(f"Failed to reload RNS after instance config update: {e}")
            reloaded = False

        if not reloaded:
            return http_unexpected(
                "Instance settings were saved, but RNS reload failed.",
                instance=app._build_reticulum_instance_settings(),
            )

        return web.json_response(
            {
                "message": "Reticulum instance settings updated and RNS restarted.",
                "instance": app._build_reticulum_instance_settings(),
            },
        )

    @routes.get("/api/v1/reticulum/management-identities")
    async def reticulum_management_identities_get(request):
        from meshchatx.src.backend.management_identities import (
            list_management_identities,
        )

        identities = list_management_identities(
            getattr(app, "reticulum_config_dir", None),
        )
        return web.json_response({"identities": identities})

    @routes.post("/api/v1/reticulum/management-identities")
    async def reticulum_management_identities_post(request):
        from meshchatx.src.backend.management_identities import (
            create_management_identity,
        )

        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            return http_bad_request("Invalid request body")
        name = (data or {}).get("name")
        force = bool((data or {}).get("force", False))
        try:
            identity = create_management_identity(
                getattr(app, "reticulum_config_dir", None),
                name or "",
                force=force,
            )
        except FileExistsError as e:
            return http_conflict(str(e))
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
        return web.json_response({"identity": identity})

    @routes.post("/api/v1/reticulum/reload")
    async def reticulum_reload(request):
        try:
            success = await app.reload_reticulum()
        except Exception as e:
            logger.debug(f"Failed to reload RNS on request: {e}")
            success = False
        if success:
            return web.json_response({"message": "Reticulum reloaded successfully"})
        return http_unexpected("Failed to reload Reticulum")

