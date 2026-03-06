from typing import Any


class CommunityInterfacesManager:
    """
    Suggested community interfaces for the interface wizard.
    No outbound connectivity checks are performed; listing these does not contact the internet.
    """

    def __init__(self):
        self.interfaces = [
            {
                "name": "Quad4",
                "type": "TCPClientInterface",
                "target_host": "62.151.179.77",
                "target_port": 45657,
                "description": "Quad4 Official Node",
            },
        ]

    async def get_interfaces(self) -> list[dict[str, Any]]:
        return [{**iface, "online": None, "last_check": 0} for iface in self.interfaces]
