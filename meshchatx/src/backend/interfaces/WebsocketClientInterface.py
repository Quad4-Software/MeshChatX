# SPDX-License-Identifier: 0BSD

"""RNS Interface that tunnels packets over a client WebSocket connection."""

from __future__ import annotations

import contextlib
import threading
import time

import RNS
from RNS.Interfaces.Interface import Interface
from websockets.sync.client import connect
from websockets.sync.connection import Connection


class WebsocketClientInterface(Interface):
    """Outbound (or accepted-child) WebSocket transport for RNS packets."""

    DEFAULT_IFAC_SIZE = 16
    RECONNECT_WAIT_S = 5

    def __str__(self) -> str:
        return f"WebsocketClientInterface[{self.name}/{self.target_url}]"

    def __init__(
        self,
        owner,
        configuration,
        websocket: Connection | None = None,
    ) -> None:
        super().__init__()
        self.owner = owner
        self.parent_interface = None
        self.IN = True
        self.OUT = False
        self.HW_MTU = 262144
        self.bitrate = 1_000_000_000
        self.mode = RNS.Interfaces.Interface.Interface.MODE_FULL

        conf = Interface.get_config_obj(configuration)
        self.name = conf.get("name")
        self.target_url = conf.get("target_url", None)
        if self.target_url is None:
            raise SystemError(f"target_url is required for interface '{self.name}'")

        self.websocket = websocket
        if self.websocket is None:
            worker = threading.Thread(target=self._maintain_connection, daemon=True)
            worker.start()

    def _drop_socket(self) -> None:
        sock = self.websocket
        self.websocket = None
        if sock is None:
            return
        with contextlib.suppress(Exception):
            sock.close()

    def _close_websocket(self) -> None:
        """Release the current websocket FD without raising."""
        self._drop_socket()

    def process_incoming(self, data) -> None:
        if not self.online or self.detached:
            return
        self.rxb += len(data)
        if self.parent_interface is not None:
            self.parent_interface.rxb += len(data)
        self.owner.inbound(data, self)

    def process_outgoing(self, data) -> None:
        if not self.online or self.detached:
            return
        try:
            self.websocket.send(data)
        except Exception as exc:
            RNS.log(f"Exception occurred while transmitting via {self!s}", RNS.LOG_ERROR)
            RNS.log(f"The contained exception was: {exc!s}", RNS.LOG_ERROR)
            return
        self.txb += len(data)
        if self.parent_interface is not None:
            self.parent_interface.txb += len(data)

    def _maintain_connection(self) -> None:
        while not self.detached:
            try:
                self._drop_socket()
                RNS.log(f"Connecting to Websocket for {self!s}...", RNS.LOG_DEBUG)
                self.websocket = connect(
                    f"{self.target_url}",
                    max_size=None,
                    compression=None,
                )
                RNS.log(f"Connected to Websocket for {self!s}", RNS.LOG_DEBUG)
                self._consume_messages()
            except Exception as exc:
                RNS.log(f"{self} failed with error: {exc}", RNS.LOG_ERROR)
            finally:
                self._drop_socket()
                self.online = False

            if self.detached:
                return
            RNS.log(f"Websocket disconnected for {self!s}...", RNS.LOG_DEBUG)
            time.sleep(self.RECONNECT_WAIT_S)

    def connect(self) -> None:
        """Public entry used by tests and callers that start the client loop."""
        self._maintain_connection()

    def read_loop(self) -> None:
        """Public entry for server-spawned children that already have a socket."""
        self._consume_messages()

    def _consume_messages(self) -> None:
        self.online = True
        sock = self.websocket
        if sock is None:
            self.online = False
            return
        try:
            for message in sock:
                self.process_incoming(message)
        except Exception as exc:
            RNS.log(f"{self} read loop error: {exc}", RNS.LOG_ERROR)
        self.online = False

    def detach(self) -> None:
        self.online = False
        self._drop_socket()
        self.detached = True


# RNS external interface entry point
interface_class = WebsocketClientInterface

# Back-compat alias for code that still references the old constant name
WebsocketClientInterface.RECONNECT_DELAY_SECONDS = (
    WebsocketClientInterface.RECONNECT_WAIT_S
)
