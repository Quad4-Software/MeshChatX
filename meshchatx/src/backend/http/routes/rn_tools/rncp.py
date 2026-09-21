# SPDX-License-Identifier: 0BSD
"""HTTP routes: rn_tools rncp."""

from __future__ import annotations

from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.routes.rn_tools._helpers import make_rn_tools_helpers

# ruff: noqa: F405
from meshchatx.src.backend.http.routes.rn_tools._names import *  # noqa: F403
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_rn_tools_rncp_routes(routes, app):
    (
        _rnsh_require_manager,
        _rnx_require_manager,
    ) = make_rn_tools_helpers(app)

    @routes.post("/api/v1/rncp/send")
    async def rncp_send(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash_str = data.get("destination_hash", "")
        file_path = data.get("file_path", "")
        timeout_raw = data.get("timeout")
        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            timeout = None
        no_compress = bool(data.get("no_compress", False))

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return http_bad_request(f"Invalid destination hash: {e}")

        transfer_id = None

        def on_transfer_started(tid):
            nonlocal transfer_id
            transfer_id = tid

        def on_progress(progress):
            if transfer_id:
                AsyncUtils.run_async(
                    app._broadcast_websocket_message(
                        {
                            "type": "rncp.transfer.progress",
                            "transfer_id": transfer_id,
                            "progress": progress,
                        },
                    ),
                )

        try:
            result = await app.rncp_handler.send_file(
                destination_hash=destination_hash,
                file_path=file_path,
                timeout=timeout,
                on_progress=on_progress,
                no_compress=no_compress,
                on_transfer_started=on_transfer_started,
            )
            AsyncUtils.run_async(
                app._broadcast_websocket_message(
                    {
                        "type": "rncp.send.completed",
                        "transfer_id": result["transfer_id"],
                        "file_path": result.get("file_path"),
                        "status": "completed",
                    },
                ),
            )
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rncp/fetch")
    async def rncp_fetch(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        destination_hash_str = data.get("destination_hash", "")
        file_path = data.get("file_path", "")
        timeout_raw = data.get("timeout")
        try:
            timeout = float(timeout_raw) if timeout_raw not in (None, "") else None
        except (TypeError, ValueError):
            timeout = None
        save_path = data.get("save_path")
        allow_overwrite = bool(data.get("allow_overwrite", False))

        try:
            destination_hash = bytes.fromhex(destination_hash_str)
        except Exception as e:
            return http_bad_request(f"Invalid destination hash: {e}")

        transfer_id = None

        def on_transfer_started(tid):
            nonlocal transfer_id
            transfer_id = tid

        def on_progress(progress):
            if transfer_id:
                AsyncUtils.run_async(
                    app._broadcast_websocket_message(
                        {
                            "type": "rncp.transfer.progress",
                            "transfer_id": transfer_id,
                            "progress": progress,
                        },
                    ),
                )

        try:
            result = await app.rncp_handler.fetch_file(
                destination_hash=destination_hash,
                file_path=file_path,
                timeout=timeout,
                on_progress=on_progress,
                save_path=save_path,
                allow_overwrite=allow_overwrite,
                on_transfer_started=on_transfer_started,
            )
            AsyncUtils.run_async(
                app._broadcast_websocket_message(
                    {
                        "type": "rncp.fetch.completed",
                        "file_path": result.get("file_path"),
                        "status": "completed",
                    },
                ),
            )
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.get("/api/v1/rncp/transfer/{transfer_id}")
    async def rncp_transfer_status(request):
        transfer_id = request.match_info.get("transfer_id", "")
        status = app.rncp_handler.get_transfer_status(transfer_id)
        if status:
            return web.json_response(status)
        return http_not_found("Transfer not found")

    @routes.post("/api/v1/rncp/listen")
    async def rncp_listen(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        allowed_hashes = data.get("allowed_hashes", [])
        fetch_allowed = bool(data.get("fetch_allowed", False))
        fetch_jail = data.get("fetch_jail")
        allow_overwrite = bool(data.get("allow_overwrite", False))

        try:
            destination_hash = app.rncp_handler.setup_receive_destination(
                allowed_hashes=allowed_hashes,
                fetch_allowed=fetch_allowed,
                fetch_jail=fetch_jail,
                allow_overwrite=allow_overwrite,
            )
            return web.json_response(
                {
                    "destination_hash": destination_hash,
                    "message": "RNCP listener started",
                },
            )
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.get("/api/v1/rncp/status")
    async def rncp_status(_request):
        return web.json_response(app.rncp_handler.get_listener_status())

    @routes.post("/api/v1/rncp/stop")
    async def rncp_stop(_request):
        try:
            app.rncp_handler.teardown_receive_destination()
            return web.json_response({"message": "RNCP listener stopped"})
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)

    @routes.post("/api/v1/rncp/cancel")
    async def rncp_cancel(request):
        data = {}
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        except Exception:
            pass
        transfer_id = None
        if isinstance(data, dict):
            raw = data.get("transfer_id")
            if isinstance(raw, str) and raw.strip():
                transfer_id = raw.strip()
        try:
            result = app.rncp_handler.cancel_transfer(transfer_id)
            return web.json_response(result)
        except Exception as e:
            return http_error_from_exception(e, key="message", fallback_status=500)
