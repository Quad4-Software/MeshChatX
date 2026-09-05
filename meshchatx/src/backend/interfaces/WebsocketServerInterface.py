# SPDX-License-Identifier: 0BSD

"""RNS Interface that accepts WebSocket clients and spawns child transports."""

from __future__ import annotations

import contextlib
import threading
import time

import RNS
from RNS.Interfaces.Interface import Interface
from websockets.sync.server import Server, ServerConnection, serve

from meshchatx.src.backend.interfaces.WebsocketClientInterface import (
    WebsocketClientInterface,
)


class WebsocketServerInterface(Interface):
    """Listen for WebSocket peers and attach each as a child RNS interface."""

    DEFAULT_IFAC_SIZE = 16
    RESTART_WAIT_S = 5

    def __str__(self) -> str:
        return (
            f"WebsocketServerInterface[{self.name}/{self.listen_ip}:{self.listen_port}]"
        )

    def __init__(self, owner, configuration) -> None:
        super().__init__()
        self.owner = owner
        self.IN = True
        self.OUT = False
        self.HW_MTU = 262144
        self.bitrate = 1_000_000_000
        self.mode = RNS.Interfaces.Interface.Interface.MODE_FULL
        self.server: Server | None = None
        self.spawned_interfaces: list[WebsocketClientInterface] = []

        conf = Interface.get_config_obj(configuration)
        self.name = conf.get("name")
        listen_ip = conf.get("listen_ip", None)
        listen_port = conf.get("listen_port", None)
        if listen_ip is None:
            raise SystemError(f"listen_ip is required for interface '{self.name}'")
        if listen_port is None:
            raise SystemError(f"listen_port is required for interface '{self.name}'")

        self.listen_ip = str(listen_ip)
        self.listen_port = int(str(listen_port).strip())
        threading.Thread(target=self._serve_loop, daemon=True).start()

    @property
    def clients(self) -> int:
        return len(self.spawned_interfaces)

    def received_announce(self, from_spawned: bool = False) -> None:
        if from_spawned:
            self.ia_freq_deque.append(time.time())

    def sent_announce(self, from_spawned: bool = False) -> None:
        if from_spawned:
            self.oa_freq_deque.append(time.time())

    def process_incoming(self, data) -> None:
        return

    def process_outgoing(self, data) -> None:
        return

    def _on_client(self, websocket: ServerConnection) -> None:
        RNS.log("Accepting incoming WebSocket connection", RNS.LOG_VERBOSE)
        remote = websocket.remote_address
        child = WebsocketClientInterface(
            self.owner,
            {
                "name": f"Client on {self.name}",
                "target_url": f"ws://{remote[0]}:{remote[1]}",
                "target_host": remote[0],
                "target_port": str(remote[1]),
            },
            websocket=websocket,
        )
        child.IN = self.IN
        child.OUT = self.OUT
        child.HW_MTU = self.HW_MTU
        child.bitrate = self.bitrate
        child.mode = self.mode
        child.parent_interface = self
        child.online = True
        child.announce_rate_target = None
        child.announce_rate_grace = None
        child.announce_rate_penalty = None

        RNS.log(f"Spawned new WebsocketClientInterface: {child}", RNS.LOG_VERBOSE)
        RNS.Transport.interfaces.append(child)
        while child in self.spawned_interfaces:
            self.spawned_interfaces.remove(child)
        self.spawned_interfaces.append(child)

        try:
            child.read_loop()
        finally:
            with contextlib.suppress(ValueError):
                self.spawned_interfaces.remove(child)
            with contextlib.suppress(ValueError):
                RNS.Transport.interfaces.remove(child)
            child.detach()

    def _serve_loop(self) -> None:
        while not self.detached:
            try:
                RNS.log(f"Starting Websocket server for {self!s}...", RNS.LOG_DEBUG)
                with serve(
                    self._on_client,
                    self.listen_ip,
                    self.listen_port,
                    compression=None,
                ) as server:
                    self.online = True
                    self.server = server
                    server.serve_forever()
            except Exception as exc:
                RNS.log(f"{self} failed with error: {exc}", RNS.LOG_ERROR)
            finally:
                self.online = False
                self.server = None

            if self.detached:
                return
            RNS.log(f"Websocket server stopped for {self!s}...", RNS.LOG_DEBUG)
            time.sleep(self.RESTART_WAIT_S)

    def serve(self) -> None:
        """Public entry for tests that start the accept loop explicitly."""
        self._serve_loop()

    def detach(self) -> None:
        self.online = False
        if self.server is not None:
            with contextlib.suppress(Exception):
                self.server.shutdown()
            self.server = None
        for child in list(self.spawned_interfaces):
            with contextlib.suppress(Exception):
                child.detach()
            with contextlib.suppress(ValueError):
                RNS.Transport.interfaces.remove(child)
        self.spawned_interfaces.clear()
        self.detached = True


interface_class = WebsocketServerInterface

WebsocketServerInterface.RESTART_DELAY_SECONDS = WebsocketServerInterface.RESTART_WAIT_S
