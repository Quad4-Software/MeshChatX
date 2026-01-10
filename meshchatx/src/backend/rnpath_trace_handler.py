import asyncio
import time
import traceback

import RNS


class RNPathTraceHandler:
    def __init__(self, reticulum_instance, identity):
        self.reticulum = reticulum_instance
        self.identity = identity

    async def trace_path(self, destination_hash_str):
        try:
            try:
                destination_hash = bytes.fromhex(destination_hash_str)
            except Exception:
                return {"error": "Invalid destination hash"}

            # Request path if we don't have it
            if not RNS.Transport.has_path(destination_hash):
                RNS.Transport.request_path(destination_hash)
                timeout = 10
                start_time = time.time()
                while (
                    not RNS.Transport.has_path(destination_hash)
                    and time.time() - start_time < timeout
                ):
                    await asyncio.sleep(0.2)

            if not RNS.Transport.has_path(destination_hash):
                return {"error": "Path not found after timeout"}

            hops = RNS.Transport.hops_to(destination_hash)

            next_hop_bytes = None
            next_hop_interface = None
            if self.reticulum:
                try:
                    next_hop_bytes = self.reticulum.get_next_hop(destination_hash)
                    next_hop_interface = self.reticulum.get_next_hop_if_name(
                        destination_hash,
                    )
                except Exception as e:
                    print(f"Error calling reticulum methods: {e}")

            path = []
            # Me
            local_hash = "unknown"
            if self.identity and hasattr(self.identity, "hash"):
                local_hash = self.identity.hash.hex()
            elif (
                self.reticulum
                and hasattr(self.reticulum, "identity")
                and self.reticulum.identity
            ):
                local_hash = self.reticulum.identity.hash.hex()

            path.append({"type": "local", "hash": local_hash, "name": "Local Node"})

            if hops == 1:
                # Direct
                path.append(
                    {
                        "type": "destination",
                        "hash": destination_hash_str,
                        "hops": 1,
                        "interface": next_hop_interface,
                    },
                )
            elif hops > 1:
                # Next hop
                path.append(
                    {
                        "type": "hop",
                        "hash": next_hop_bytes.hex() if next_hop_bytes else None,
                        "name": "Next Hop",
                        "interface": next_hop_interface,
                        "hop_number": 1,
                    },
                )

                # Intermediate unknown hops
                if hops > 2:
                    path.append({"type": "unknown", "count": hops - 2})

                # Destination
                path.append(
                    {"type": "destination", "hash": destination_hash_str, "hops": hops},
                )

            return {
                "destination": destination_hash_str,
                "hops": hops,
                "path": path,
                "interface": next_hop_interface,
                "next_hop": next_hop_bytes.hex() if next_hop_bytes else None,
            }
        except Exception as e:
            return {"error": f"Trace failed: {e}\n{traceback.format_exc()}"}
