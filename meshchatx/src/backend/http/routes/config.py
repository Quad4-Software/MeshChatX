# SPDX-License-Identifier: 0BSD
"""HTTP routes: config."""

from __future__ import annotations

from aiohttp import web

from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_payload_too_large,
    http_unexpected,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_config_routes(routes, app):

    # get config
    @routes.get(API_V1_PREFIX + "/config")
    async def config_get(request):
        return web.json_response(
            {
                "config": app.get_config_dict(),
            },
        )

    # update config

    # update config
    @routes.patch(API_V1_PREFIX + "/config")
    async def config_update(request):
        # get request body as json
        try:
            data = await read_json_limited(request)
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
        except PayloadTooLargeError:
            return http_payload_too_large()
        except ValueError as e:
            return http_bad_request(str(e))
        except Exception:
            import traceback

            print("config_update failed:\n" + traceback.format_exc())
            return http_unexpected("config_update_failed")

    # get or update reticulum discovery configuration
