import asyncio
import os
import time

import RNS


class RNProbeHandler:
    DEFAULT_PROBE_SIZE = 16
    DEFAULT_TIMEOUT = 12

    def __init__(self, reticulum_instance, identity):
        self.reticulum = reticulum_instance
        self.identity = identity

    async def probe_destination(
        self,
        destination_hash: bytes,
        full_name: str,
        size: int = DEFAULT_PROBE_SIZE,
        timeout: float | None = None,
        wait: float = 0,
        probes: int = 1,
    ):
        try:
            app_name, aspects = RNS.Destination.app_and_aspects_from_name(full_name)
        except Exception as e:
            msg = f"Invalid destination name: {e}"
            raise ValueError(msg)

        if not RNS.Transport.has_path(destination_hash):
            RNS.Transport.request_path(destination_hash)

        timeout_after = time.time() + (timeout or self.DEFAULT_TIMEOUT + self.reticulum.get_first_hop_timeout(destination_hash))
        while not RNS.Transport.has_path(destination_hash) and time.time() < timeout_after:
            await asyncio.sleep(0.1)

        if not RNS.Transport.has_path(destination_hash):
            msg = "Path request timed out"
            raise TimeoutError(msg)

        server_identity = RNS.Identity.recall(destination_hash)
        request_destination = RNS.Destination(
            server_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            app_name,
            *aspects,
        )

        results = []
        sent = 0

        while probes > 0:
            if sent > 0:
                await asyncio.sleep(wait)

            try:
                probe = RNS.Packet(request_destination, os.urandom(size))
                probe.pack()
            except OSError:
                msg = f"Probe packet size of {len(probe.raw)} bytes exceeds MTU of {RNS.Reticulum.MTU} bytes"
                raise ValueError(msg)

            receipt = probe.send()
            sent += 1

            next_hop = self.reticulum.get_next_hop(destination_hash)
            via_str = f" via {RNS.prettyhexrep(next_hop)}" if next_hop else ""
            if_name = self.reticulum.get_next_hop_if_name(destination_hash)
            if_str = f" on {if_name}" if if_name and if_name != "None" else ""

            timeout_after = time.time() + (timeout or self.DEFAULT_TIMEOUT + self.reticulum.get_first_hop_timeout(destination_hash))
            while receipt.status == RNS.PacketReceipt.SENT and time.time() < timeout_after:
                await asyncio.sleep(0.1)

            result: dict = {
                "probe_number": sent,
                "size": size,
                "destination": RNS.prettyhexrep(destination_hash),
                "via": via_str,
                "interface": if_str,
                "status": "timeout",
            }

            if time.time() > timeout_after:
                result["status"] = "timeout"
            elif receipt.status == RNS.PacketReceipt.DELIVERED:
                hops = RNS.Transport.hops_to(destination_hash)
                rtt = receipt.get_rtt()

                if rtt >= 1:
                    rtt_str = f"{round(rtt, 3)} seconds"
                else:
                    rtt_str = f"{round(rtt * 1000, 3)} milliseconds"

                reception_stats = {}
                if self.reticulum.is_connected_to_shared_instance:
                    reception_rssi = self.reticulum.get_packet_rssi(receipt.proof_packet.packet_hash)
                    reception_snr = self.reticulum.get_packet_snr(receipt.proof_packet.packet_hash)
                    reception_q = self.reticulum.get_packet_q(receipt.proof_packet.packet_hash)

                    if reception_rssi is not None:
                        reception_stats["rssi"] = reception_rssi
                    if reception_snr is not None:
                        reception_stats["snr"] = reception_snr
                    if reception_q is not None:
                        reception_stats["quality"] = reception_q
                elif receipt.proof_packet:
                    if receipt.proof_packet.rssi is not None:
                        reception_stats["rssi"] = receipt.proof_packet.rssi
                    if receipt.proof_packet.snr is not None:
                        reception_stats["snr"] = receipt.proof_packet.snr

                result.update(
                    {
                        "status": "delivered",
                        "hops": hops,
                        "rtt": rtt,
                        "rtt_string": rtt_str,
                        "reception_stats": reception_stats,
                    },
                )
            else:
                result["status"] = "failed"

            results.append(result)
            probes -= 1

        return {
            "results": results,
            "sent": sent,
            "delivered": sum(1 for r in results if r["status"] == "delivered"),
            "timeouts": sum(1 for r in results if r["status"] == "timeout"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }

