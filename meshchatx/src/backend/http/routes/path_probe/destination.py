# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe destination."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.path_probe._names import *  # noqa: F403, F405


def register_path_probe_destination_routes(routes, app):

    @routes.get("/api/v1/destination/{destination_hash}/path")
    async def destination_path(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(app, destination_hash)
        except ValueError:
            return web.json_response(
                {"message": "invalid destination hash"},
                status=400,
            )
        destination_hash_hex = destination_hash.hex()

        request_query_param = request.query.get("request", "false")
        if request_query_param in ("true", "1"):
            return web.json_response(
                {"message": PATH_WAIT_REQUIRES_POST_MESSAGE},
                status=400,
            )

        if destination_hash_hex in local_destination_hashes(app):
            return local_path_response(destination_hash_hex)

        return destination_path_snapshot(destination_hash)

    @routes.post("/api/v1/destination/{destination_hash}/path")
    async def destination_path_wait(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash_bytes = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return web.json_response(
                {"message": "invalid destination hash"},
                status=400,
            )
        destination_hash_hex = destination_hash_bytes.hex()

        timeout_raw = await read_path_probe_timeout_raw(request)
        timeout_seconds, timeout_error = parse_path_probe_timeout(timeout_raw)
        if timeout_error:
            return web.json_response({"message": timeout_error}, status=400)
        if timeout_seconds is None:
            reticulum = app.reticulum if hasattr(app, "reticulum") else None
            timeout_seconds = path_response_window(
                destination_hash_bytes,
                reticulum,
            )

        if destination_hash_hex in local_destination_hashes(app):
            return local_path_response(destination_hash_hex)

        timeout_after_seconds = time.time() + timeout_seconds
        reticulum = app.reticulum if hasattr(app, "reticulum") else None
        reticulum_pathfinding.prepare_fresh_path_request(
            reticulum,
            destination_hash_bytes,
        )

        while (
            not RNS.Transport.has_path(destination_hash_bytes)
            and time.time() < timeout_after_seconds
        ):
            await asyncio.sleep(0.1)

        if RNS.Transport.has_path(destination_hash_bytes):
            maybe_resend_failed_for_current(destination_hash)

        return destination_path_snapshot(destination_hash_bytes)

    # drop path to destination

    # drop path to destination
    @routes.post("/api/v1/destination/{destination_hash}/drop-path")
    async def destination_drop_path(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return web.json_response(
                {"message": "invalid destination hash"},
                status=400,
            )

        # drop path
        if hasattr(app, "reticulum") and app.reticulum:
            app.reticulum.drop_path(destination_hash)

        return web.json_response(
            {
                "message": "Path has been dropped",
            },
        )

    # proactively ask Reticulum to resolve or refresh path (non-blocking HTTP, and discovery runs in background)

    # proactively ask Reticulum to resolve or refresh path (non-blocking HTTP, and discovery runs in background)
    @routes.post("/api/v1/destination/{destination_hash}/request-path")
    async def destination_request_path_fire(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash_bytes = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return web.json_response(
                {
                    "message": "invalid destination hash",
                },
                status=400,
            )
        reticulum = app.reticulum if hasattr(app, "reticulum") else None
        reticulum_pathfinding.prepare_fresh_path_request(
            reticulum,
            destination_hash_bytes,
        )

        if RNS.Transport.has_path(destination_hash_bytes):
            maybe_resend_failed_for_current(destination_hash)

        return web.json_response(
            {
                "message": "ok",
            },
        )

    # get signal metrics for a destination by checking the latest announce or lxmf message received from them

    # get signal metrics for a destination by checking the latest announce or lxmf message received from them
    @routes.get("/api/v1/destination/{destination_hash}/signal-metrics")
    async def destination_signal_metrics(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        # signal metrics to return
        snr = None
        rssi = None
        quality = None
        updated_at = None

        # get latest announce from database for the provided destination hash
        latest_announce = app.database.announces.get_announce_by_hash(
            destination_hash,
        )

        # get latest lxmf message from database sent to us from the provided destination hash
        local_hash = app.local_lxmf_destination.hexhash
        messages = app.message_handler.get_conversation_messages(
            local_hash,
            destination_hash,
            limit=1,
        )
        # Filter for incoming messages only
        latest_lxmf_message = next(
            (m for m in messages if m["source_hash"] == destination_hash),
            None,
        )

        # determine when latest announce was received
        latest_announce_at = None
        if latest_announce is not None:
            latest_announce_at = datetime.fromisoformat(
                latest_announce["updated_at"],
            )
            if latest_announce_at.tzinfo is not None:
                latest_announce_at = latest_announce_at.replace(tzinfo=None)

        # determine when latest lxmf message was received
        latest_lxmf_message_at = None
        if latest_lxmf_message is not None:
            latest_lxmf_message_at = datetime.fromisoformat(
                latest_lxmf_message["created_at"],
            )
            if latest_lxmf_message_at.tzinfo is not None:
                latest_lxmf_message_at = latest_lxmf_message_at.replace(tzinfo=None)

        # get signal metrics from latest announce
        if latest_announce is not None:
            snr = latest_announce["snr"]
            rssi = latest_announce["rssi"]
            quality = latest_announce["quality"]
            # using updated_at from announce because this is when the latest announce was received
            updated_at = latest_announce["updated_at"]

        # get signal metrics from latest lxmf message if it's more recent than the announce
        if latest_lxmf_message is not None and (
            latest_announce_at is None or latest_lxmf_message_at > latest_announce_at
        ):
            snr = latest_lxmf_message["snr"]
            rssi = latest_lxmf_message["rssi"]
            quality = latest_lxmf_message["quality"]
            # using created_at from lxmf message because this is when the message was received
            updated_at = latest_lxmf_message["created_at"]

        return web.json_response(
            {
                "signal_metrics": {
                    "snr": snr,
                    "rssi": rssi,
                    "quality": quality,
                    "updated_at": updated_at,
                },
            },
        )

    # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
    # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
    # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374
