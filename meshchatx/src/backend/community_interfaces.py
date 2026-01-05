import asyncio
import time
from typing import Any


class CommunityInterfacesManager:
    def __init__(self):
        self.interfaces = [
            {
                "name": "noDNS1",
                "type": "TCPClientInterface",
                "target_host": "202.61.243.41",
                "target_port": 4965,
                "description": "Public TCP Relay",
            },
            {
                "name": "noDNS2",
                "type": "TCPClientInterface",
                "target_host": "193.26.158.230",
                "target_port": 4965,
                "description": "Public TCP Relay",
            },
            {
                "name": "0rbit-Net",
                "type": "TCPClientInterface",
                "target_host": "93.95.227.8",
                "target_port": 49952,
                "description": "Public TCP Relay",
            },
            {
                "name": "Quad4 TCP Node 1",
                "type": "TCPClientInterface",
                "target_host": "rns.quad4.io",
                "target_port": 4242,
                "description": "Public TCP Relay",
            },
            {
                "name": "Quad4 TCP Node 2",
                "type": "TCPClientInterface",
                "target_host": "rns2.quad4.io",
                "target_port": 4242,
                "description": "Public TCP Relay",
            },
            {
                "name": "RNS Testnet Amsterdam",
                "type": "TCPClientInterface",
                "target_host": "amsterdam.connect.reticulum.network",
                "target_port": 4965,
                "description": "Reticulum Testnet Hub",
            },
            {
                "name": "RNS Testnet BetweenTheBorders",
                "type": "TCPClientInterface",
                "target_host": "reticulum.betweentheborders.com",
                "target_port": 4242,
                "description": "Reticulum Testnet Hub",
            },
        ]
        self.status_cache = {}
        self.last_check = 0
        self.check_interval = 600  # Check every 10 minutes

    async def check_health(self, host: str, port: int) -> bool:
        try:
            # Simple TCP connect check as a proxy for "working"
            # In a real RNS environment, we might want to use RNS.Transport.probe()
            # but that requires Reticulum to be running with a configured interface to that target.
            # For "suggested" interfaces, we just check if they are reachable.
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=3.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def update_statuses(self):
        tasks = [
            self.check_health(iface["target_host"], iface["target_port"])
            for iface in self.interfaces
        ]

        results = await asyncio.gather(*tasks)

        for iface, is_online in zip(self.interfaces, results):
            self.status_cache[iface["name"]] = {
                "online": is_online,
                "last_check": time.time(),
            }
        self.last_check = time.time()

    async def get_interfaces(self) -> list[dict[str, Any]]:
        # If cache is old or empty, update it
        if time.time() - self.last_check > self.check_interval or not self.status_cache:
            # We don't want to block the request, so we could do this in background
            # but for now let's just do it.
            await self.update_statuses()

        results = []
        for iface in self.interfaces:
            status = self.status_cache.get(
                iface["name"],
                {"online": False, "last_check": 0},
            )
            results.append(
                {
                    **iface,
                    "online": status["online"],
                    "last_check": status["last_check"],
                },
            )

        # Sort so online ones are first
        results.sort(key=lambda x: x["online"], reverse=True)
        return results
