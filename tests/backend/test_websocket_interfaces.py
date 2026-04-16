# SPDX-License-Identifier: 0BSD

import socket
import unittest
from unittest.mock import MagicMock, patch

from meshchatx.src.backend.interfaces.WebsocketClientInterface import (
    WebsocketClientInterface,
)
from meshchatx.src.backend.interfaces.WebsocketServerInterface import (
    WebsocketServerInterface,
)


class TestWebsocketInterfaces(unittest.TestCase):
    def setUp(self):
        self.owner = MagicMock()
        # Find a free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        self.port = s.getsockname()[1]
        s.close()

    @patch("RNS.Interfaces.Interface.Interface.get_config_obj")
    def test_server_initialization(self, mock_get_config):
        config = {
            "name": "test_ws_server",
            "listen_ip": "127.0.0.1",
            "listen_port": str(self.port),
        }
        mock_get_config.return_value = config

        server = WebsocketServerInterface(self.owner, config)
        self.assertEqual(server.name, "test_ws_server")
        self.assertEqual(server.listen_ip, "127.0.0.1")
        self.assertEqual(server.listen_port, self.port)

        # Cleanup
        if server.server:
            server.server.shutdown()

    @patch("RNS.Interfaces.Interface.Interface.get_config_obj")
    def test_client_initialization(self, mock_get_config):
        config = {"name": "test_ws_client", "target_url": f"ws://127.0.0.1:{self.port}"}
        mock_get_config.return_value = config

        # We don't want it to actually try connecting in this basic test
        with patch(
            "meshchatx.src.backend.interfaces.WebsocketClientInterface.threading.Thread",
        ):
            client = WebsocketClientInterface(self.owner, config)
            self.assertEqual(client.name, "test_ws_client")
            self.assertEqual(client.target_url, f"ws://127.0.0.1:{self.port}")


if __name__ == "__main__":
    unittest.main()
