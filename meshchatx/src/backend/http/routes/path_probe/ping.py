# SPDX-License-Identifier: 0BSD
"""HTTP routes: path_probe ping."""

from __future__ import annotations

# ruff: noqa: F405

from meshchatx.src.backend.http.routes.path_probe._names import *  # noqa: F403, F405


def register_path_probe_ping_routes(routes, app):

    # pings an lxmf.delivery destination by sending empty data and waiting for the recipient to send a proof back
    # the lxmf router proves all received packets, then drops them if they can't be decoded as lxmf messages
    # this allows us to ping/probe any active lxmf.delivery destination and get rtt/snr/rssi data on demand
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L234
    # https://github.com/markqvist/LXMF/blob/9ff76c0473e9d4107e079f266dd08144bb74c7c8/LXMF/LXMRouter.py#L1374
    @routes.post("/api/v1/ping/{destination_hash}/lxmf.delivery")
    async def ping_lxmf_delivery(request):
        # get path params
        destination_hash_str = request.match_info.get("destination_hash", "")

        try:
            destination_hash = lxmf_delivery_hash_bytes_for_path(
                app,
                destination_hash_str,
            )
        except ValueError:
            return web.json_response(
                {"message": "Ping failed. Invalid destination hash."},
                status=400,
            )
        destination_hash_str = destination_hash.hex()

        timeout_raw = await read_path_probe_timeout_raw(request)
        timeout_seconds, timeout_error = parse_path_probe_timeout(timeout_raw)
        if timeout_error:
            return web.json_response(
                {"message": f"Ping failed. {timeout_error}"},
                status=400,
            )
        if timeout_seconds is None:
            reticulum = app.reticulum if hasattr(app, "reticulum") else None
            timeout_seconds = int(
                round(path_response_window(destination_hash, reticulum)),
            )

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
            return web.json_response(
                {
                    "message": "Ping failed. Could not find path to destination.",
                },
                status=503,
            )

        # find destination identity (pass string hash, not bytes)
        destination_identity = app.recall_identity(destination_hash_str)
        if destination_identity is None:
            return web.json_response(
                {
                    "message": "Ping failed. Could not recall destination identity.",
                },
                status=503,
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
            return web.json_response(
                {
                    "message": f"Ping failed. Timed out after {timeout_seconds} seconds.",
                },
                status=503,
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
