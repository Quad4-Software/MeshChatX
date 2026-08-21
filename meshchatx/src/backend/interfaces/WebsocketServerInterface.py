# SPDX-License-Identifier: 0BSD AND MIT

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
    DEFAULT_IFAC_SIZE = 16

    RESTART_DELAY_SECONDS = 5

    def __str__(self):
        return (
            f"WebsocketServerInterface[{self.name}/{self.listen_ip}:{self.listen_port}]"
        )

    def __init__(self, owner, configuration):
        super().__init__()

        self.owner = owner

        self.IN = True
        self.OUT = False
        self.HW_MTU = 262144  # 256KiB
        self.bitrate = 1_000_000_000  # 1Gbps
        self.mode = RNS.Interfaces.Interface.Interface.MODE_FULL

        self.server: Server | None = None
        self.spawned_interfaces: list[WebsocketClientInterface] = []

        # parse config
        ifconf = Interface.get_config_obj(configuration)
        self.name = ifconf.get("name")
        listen_ip = ifconf.get("listen_ip", None)
        listen_port = ifconf.get("listen_port", None)

        # ensure listen ip is provided
        if listen_ip is None:
            msg = f"listen_ip is required for interface '{self.name}'"
            raise SystemError(msg)

        # ensure listen port is provided
        if listen_port is None:
            msg = f"listen_port is required for interface '{self.name}'"
            raise SystemError(msg)

        self.listen_ip = str(listen_ip)
        self.listen_port = int(str(listen_port).strip())

        # run websocket server
        thread = threading.Thread(target=self.serve)
        thread.daemon = True
        thread.start()

    @property
    def clients(self):
        return len(self.spawned_interfaces)

    def received_announce(self, from_spawned=False):
        if from_spawned:
            self.ia_freq_deque.append(time.time())

    # TODO docs
    def sent_announce(self, from_spawned=False):
        if from_spawned:
            self.oa_freq_deque.append(time.time())

    # do nothing as the spawned child interface will take care of rx/tx
    def process_incoming(self, data):
        pass

    # do nothing as the spawned child interface will take care of rx/tx
    def process_outgoing(self, data):
        pass

    def serve(self):
        # handle new websocket client connections
        def on_websocket_client_connected(websocket: ServerConnection):
            # create new child interface
            RNS.log("Accepting incoming WebSocket connection", RNS.LOG_VERBOSE)
            spawned_interface = WebsocketClientInterface(
                self.owner,
                {
                    "name": f"Client on {self.name}",
                    "target_url": (
                        f"ws://{websocket.remote_address[0]}:"
                        f"{websocket.remote_address[1]}"
                    ),
                    "target_host": websocket.remote_address[0],
                    "target_port": str(websocket.remote_address[1]),
                },
                websocket=websocket,
            )

            # configure child interface
            spawned_interface.IN = self.IN
            spawned_interface.OUT = self.OUT
            spawned_interface.HW_MTU = self.HW_MTU
            spawned_interface.bitrate = self.bitrate
            spawned_interface.mode = self.mode
            spawned_interface.parent_interface = self
            spawned_interface.online = True

            spawned_interface.announce_rate_target = None
            spawned_interface.announce_rate_grace = None
            spawned_interface.announce_rate_penalty = None

            # activate child interface
            RNS.log(
                f"Spawned new WebsocketClientInterface: {spawned_interface}",
                RNS.LOG_VERBOSE,
            )
            RNS.Transport.interfaces.append(spawned_interface)

            # associate child interface with this interface
            while spawned_interface in self.spawned_interfaces:
                self.spawned_interfaces.remove(spawned_interface)
            self.spawned_interfaces.append(spawned_interface)

            # run read loop
            try:
                spawned_interface.read_loop()
            finally:
                # Drop Transport + child bookkeeping and close the socket so
                # reconnect storms cannot pin FDs in RNS.Transport.interfaces.
                with contextlib.suppress(ValueError):
                    self.spawned_interfaces.remove(spawned_interface)
                with contextlib.suppress(ValueError):
                    RNS.Transport.interfaces.remove(spawned_interface)
                spawned_interface.detach()

        # run websocket server
        while not self.detached:
            try:
                RNS.log(f"Starting Websocket server for {self!s}...", RNS.LOG_DEBUG)
                with serve(
                    on_websocket_client_connected,
                    self.listen_ip,
                    self.listen_port,
                    compression=None,
                ) as server:
                    self.online = True
                    self.server = server
                    server.serve_forever()
            except Exception as e:
                RNS.log(f"{self} failed with error: {e}", RNS.LOG_ERROR)
            finally:
                self.online = False
                self.server = None

            if self.detached:
                return

            RNS.log(f"Websocket server stopped for {self!s}...", RNS.LOG_DEBUG)
            time.sleep(self.RESTART_DELAY_SECONDS)

    def detach(self):
        # mark as offline
        self.online = False

        # stop websocket server
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

        # mark as detached
        self.detached = True


# set interface class RNS should use when importing this external interface
interface_class = WebsocketServerInterface
