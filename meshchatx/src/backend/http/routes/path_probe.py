# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe."""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import datetime

import RNS
from aiohttp import web

from meshchatx.src.backend import reticulum_pathfinding
from meshchatx.src.backend.async_utils import AsyncUtils
from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_not_found,
    http_payload_too_large,
    http_unavailable,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)
from meshchatx.src.backend.meshchat_utils import normalize_hex_identifier
from meshchatx.src.backend.path_utils import path_response_window

# Same ceiling as RNProbeHandler.MAX_TIMEOUT_S
PATH_PROBE_MIN_TIMEOUT_S = 1
PATH_PROBE_MAX_TIMEOUT_S = 600
PATH_WAIT_REQUIRES_POST_MESSAGE = (
    "Waiting for a path requires POST. GET /path is a snapshot only."
)


def parse_path_probe_timeout(raw, *, default=None):
    if raw is None or raw == "":
        raw = default
    if raw is None or raw == "":
        return None, None
    try:
        timeout_seconds = int(raw)
    except (TypeError, ValueError):
        return None, "Timeout must be an integer."
    if (
        timeout_seconds < PATH_PROBE_MIN_TIMEOUT_S
        or timeout_seconds > PATH_PROBE_MAX_TIMEOUT_S
    ):
        return None, (
            f"Timeout must be between {PATH_PROBE_MIN_TIMEOUT_S} and "
            f"{PATH_PROBE_MAX_TIMEOUT_S} seconds."
        )
    return timeout_seconds, None


async def read_path_probe_timeout_raw(request, default=None):
    query = getattr(request, "query", None) or {}
    if "timeout" in query:
        return query.get("timeout")
    method = str(getattr(request, "method", "GET") or "GET").upper()
    if method == "POST":
        try:
            body = await read_json_limited(request)
        except Exception:
            body = None
        if isinstance(body, dict) and body.get("timeout") is not None:
            return body.get("timeout")
    return default


def lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex: str) -> bytes:
    """Return lxmf.delivery bytes for transport path and ping operations.

    The UI may pass an identity hash or an lxmf.delivery hash. Reticulum
    path tables are keyed by destination hash, not identity hash.
    """
    fallback = bytes.fromhex(destination_hash_hex)
    with contextlib.suppress(Exception):
        resolved_hex = app.get_lxmf_destination_hash_for_identity_hash(
            destination_hash_hex,
        )
        if isinstance(resolved_hex, str):
            stripped = resolved_hex.strip()
            if len(stripped) == 32:
                return bytes.fromhex(stripped)
    return fallback


def lxmf_delivery_hash_hex_for_path(app, destination_hash_hex: str) -> str:
    return lxmf_delivery_hash_bytes_for_path(app, destination_hash_hex).hex()


def local_destination_hashes(app):
    hashes: set[str] = set()
    with contextlib.suppress(Exception):
        if app.current_context and app.current_context.identity:
            hashes.add(app.current_context.identity.hash.hex())
    with contextlib.suppress(Exception):
        if app.local_lxmf_destination is not None:
            hashes.add(app.local_lxmf_destination.hash.hex())
    with contextlib.suppress(Exception):
        if app.current_context and app.current_context.message_router:
            pdest = app.current_context.message_router.propagation_destination
            if pdest is not None and getattr(pdest, "hash", None):
                hashes.add(pdest.hash.hex())
    return hashes


def register_path_probe_routes(routes, app):

    def maybe_resend_failed_for_current(destination_hash_str):
        ctx = app.current_context
        if (
            ctx is not None
            and ctx.running
            and ctx.config.auto_resend_failed_messages_when_announce_received.get()
        ):
            lookup_hash = lxmf_delivery_hash_hex_for_path(app, destination_hash_str)
            AsyncUtils.run_async(
                app.resend_failed_messages_for_destination(
                    lookup_hash,
                    context=ctx,
                ),
            )

    def local_path_response(destination_hash_hex):
        return web.json_response(
            {
                "path": {
                    "hops": 0,
                    "next_hop": destination_hash_hex,
                    "next_hop_interface": "Local",
                },
                "path_stale": False,
                "path_unresponsive": False,
            },
        )

    def destination_path_snapshot(destination_hash):
        if not RNS.Transport.has_path(destination_hash):
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )

        hops = RNS.Transport.hops_to(destination_hash)
        if not isinstance(hops, int):
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )
        next_hop_bytes = None
        if hasattr(app, "reticulum") and app.reticulum:
            next_hop_bytes = app.reticulum.get_next_hop(destination_hash)
        if next_hop_bytes is not None and not isinstance(
            next_hop_bytes,
            (bytes, bytearray),
        ):
            next_hop_bytes = None

        if next_hop_bytes is None:
            pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
            return web.json_response(
                {
                    "path": None,
                    **pm,
                },
            )

        next_hop = next_hop_bytes.hex()
        next_hop_interface = (
            app.reticulum.get_next_hop_if_name(destination_hash)
            if hasattr(app, "reticulum") and app.reticulum
            else None
        )

        pm = reticulum_pathfinding.path_metadata_for_api(destination_hash)
        return web.json_response(
            {
                "path": {
                    "hops": hops,
                    "next_hop": next_hop,
                    "next_hop_interface": next_hop_interface,
                },
                **pm,
            },
        )

    @routes.get(API_V1_PREFIX + "/destination/{destination_hash}/path")
    async def destination_path(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(app, destination_hash)
        except ValueError:
            return http_bad_request("invalid destination hash")
        destination_hash_hex = destination_hash.hex()

        request_query_param = request.query.get("request", "false")
        if request_query_param in ("true", "1"):
            return http_bad_request(PATH_WAIT_REQUIRES_POST_MESSAGE)

        if destination_hash_hex in local_destination_hashes(app):
            return local_path_response(destination_hash_hex)

        return destination_path_snapshot(destination_hash)

    @routes.post(API_V1_PREFIX + "/destination/{destination_hash}/path")
    async def destination_path_wait(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash_bytes = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return http_bad_request("invalid destination hash")
        destination_hash_hex = destination_hash_bytes.hex()

        timeout_raw = await read_path_probe_timeout_raw(request)
        timeout_seconds, timeout_error = parse_path_probe_timeout(timeout_raw)
        if timeout_error:
            return http_bad_request(timeout_error)
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
    @routes.post(API_V1_PREFIX + "/destination/{destination_hash}/drop-path")
    async def destination_drop_path(request):
        # get path params
        destination_hash = request.match_info.get("destination_hash", "")

        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return http_bad_request("invalid destination hash")

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
    @routes.post(API_V1_PREFIX + "/destination/{destination_hash}/request-path")
    async def destination_request_path_fire(request):
        destination_hash = request.match_info.get("destination_hash", "")
        try:
            destination_hash_bytes = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash,
            )
        except ValueError:
            return http_bad_request("invalid destination hash")
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
    @routes.get(API_V1_PREFIX + "/destination/{destination_hash}/signal-metrics")
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

    # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
    # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
    # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374
    @routes.post(API_V1_PREFIX + "/ping/{destination_hash}/lxmf.delivery")
    async def ping_lxmf_delivery(request):
        # get path params
        destination_hash_str = request.match_info.get("destination_hash", "")

        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash_str,
            )
        except ValueError:
            return http_bad_request("Ping failed. Invalid destination hash.")
        destination_hash_str = destination_hash.hex()

        timeout_raw = await read_path_probe_timeout_raw(request)
        timeout_seconds, timeout_error = parse_path_probe_timeout(timeout_raw)
        if timeout_error:
            return http_bad_request(f"Ping failed. {timeout_error}")
        if timeout_seconds is None:
            reticulum = app.reticulum if hasattr(app, "reticulum") else None
            timeout_seconds = round(path_response_window(destination_hash, reticulum))

        # Split the budget so path discovery cannot consume the whole timeout.
        path_budget_seconds = max(1, timeout_seconds // 2)
        delivery_budget_seconds = max(1, timeout_seconds - path_budget_seconds)
        path_deadline = time.time() + path_budget_seconds

        # request path if we don't have it
        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        # wait until we have a path, or give up after the path budget
        while (
            not RNS.Transport.has_path(destination_hash) and time.time() < path_deadline
        ):
            await asyncio.sleep(0.1)

        if not RNS.Transport.has_path(destination_hash):
            return http_unavailable("Ping failed. Could not find path to destination.")

        # find destination identity (pass string hash, not bytes)
        destination_identity = app.recall_identity(destination_hash_str)
        if destination_identity is None:
            return http_unavailable(
                "Ping failed. Could not recall destination identity."
            )

        # create outbound destination
        request_destination = RNS.Destination(
            destination_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        # send empty packet to destination
        packet = RNS.Packet(request_destination, b"")
        receipt = packet.send()

        delivery_deadline = time.time() + delivery_budget_seconds
        # wait until delivered, or give up after the delivery budget
        while (
            receipt.status != RNS.PacketReceipt.DELIVERED
            and time.time() < delivery_deadline
        ):
            await asyncio.sleep(0.1)

        # ping failed if not delivered
        if receipt.status != RNS.PacketReceipt.DELIVERED:
            return http_unavailable(
                f"Ping failed. Timed out after {timeout_seconds} seconds."
            )

        # get number of hops to destination and back from destination
        hops_there = RNS.Transport.hops_to(destination_hash)
        hops_back = receipt.proof_packet.hops

        # get rssi
        rssi = receipt.proof_packet.rssi
        if rssi is None and hasattr(app, "reticulum") and app.reticulum:
            rssi = app.reticulum.get_packet_rssi(receipt.proof_packet.packet_hash)

        # get snr
        snr = receipt.proof_packet.snr
        if snr is None and hasattr(app, "reticulum") and app.reticulum:
            snr = app.reticulum.get_packet_snr(receipt.proof_packet.packet_hash)

        # get signal quality
        quality = receipt.proof_packet.q
        if quality is None and hasattr(app, "reticulum") and app.reticulum:
            quality = app.reticulum.get_packet_q(receipt.proof_packet.packet_hash)

        # get and format round trip time
        rtt = receipt.get_rtt()
        rtt_milliseconds = round(rtt * 1000, 3)
        rtt_duration_string = f"{rtt_milliseconds} ms"

        maybe_resend_failed_for_current(destination_hash_str)

        return web.json_response(
            {
                "message": f"Valid reply from {receipt.destination.hash.hex()}\nDuration: {rtt_duration_string}\nHops There: {hops_there}\nHops Back: {hops_back}",
                "ping_result": {
                    "rtt": rtt,
                    "hops_there": hops_there,
                    "hops_back": hops_back,
                    "rssi": rssi,
                    "snr": snr,
                    "quality": quality,
                    "receiving_interface": str(
                        receipt.proof_packet.receiving_interface,
                    ),
                },
            },
        )

    # get path table
    @routes.get(API_V1_PREFIX + "/path-table")
    @routes.post(API_V1_PREFIX + "/path-table")
    async def path_table(request):
        limit = request.query.get("limit", None)
        offset = request.query.get("offset", None)
        destination_hashes = None
        if request.method == "POST":
            try:
                body = await read_json_limited(request)
                destination_hashes = body.get("destination_hashes")
                if destination_hashes and not isinstance(destination_hashes, list):
                    destination_hashes = None
            except PayloadTooLargeError:
                return http_payload_too_large()
            except Exception:
                pass

        all_paths = []
        if hasattr(app, "reticulum") and app.reticulum:
            try:
                all_paths = app.reticulum.get_path_table()
            except Exception:
                pass

        if destination_hashes:
            hash_set = {h.lower() for h in destination_hashes if isinstance(h, str)}
            all_paths = [p for p in all_paths if p["hash"].hex().lower() in hash_set]

        total_count = len(all_paths)

        # apply pagination if requested
        if limit is not None or offset is not None:
            try:
                start = int(offset) if offset else 0
                end = (start + int(limit)) if limit else total_count
                paginated_paths = all_paths[start:end]
            except (ValueError, TypeError):
                paginated_paths = all_paths
        else:
            paginated_paths = all_paths

        path_table = []
        for path in paginated_paths:
            path["hash"] = path["hash"].hex()
            path["via"] = path["via"].hex()
            path_table.append(path)

        return web.json_response(
            {
                "path_table": path_table,
                "total_count": total_count,
            },
        )

    # derive lxmf delivery address from an identity hash

    @routes.get(API_V1_PREFIX + "/identity/{identity_hash}/lxmf-address")
    async def identity_lxmf_address(request):
        raw = request.match_info.get("identity_hash", "")
        norm = normalize_hex_identifier(raw)
        # Identity hashes are 16 bytes (32 hex); 32-byte (64 hex) forms are
        # tolerated to match parse_identity_hash.
        if len(norm) not in (32, 64):
            return http_bad_request("invalid identity hash")

        lxmf_hex = await asyncio.to_thread(
            app.get_lxmf_destination_hash_for_identity_hash,
            norm,
        )
        if not lxmf_hex:
            return http_not_found("no LXMF address could be derived for this identity")

        has_path = False
        try:
            has_path = RNS.Transport.has_path(bytes.fromhex(lxmf_hex))
        except Exception:
            pass

        return web.json_response(
            {
                "identity_hash": norm,
                "lxmf_destination_hash": lxmf_hex,
                "has_path": has_path,
            },
        )

    # send lxmf message
