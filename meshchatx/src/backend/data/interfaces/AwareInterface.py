# SPDX-License-Identifier: 0BSD

"""WiFi Aware (NAN) interface for Reticulum on Android only.

Loaded by RNS from the configured interfacepath as AwareInterface.py. The
controller session lives in the Java AwareSession bridge. This module turns
each established data-path socket into a spawned per-peer interface with the
same HDLC framing as TCPClientInterface, so wire behaviour is identical.

Config example:

    [[WiFi Aware]]
      type = AwareInterface
      enabled = yes
      mode = subscribe
      peers = 4

mode is publish (responder, waits for initiators) or subscribe (initiator,
connects to discovered publishers). peers caps concurrent data paths.
"""

import threading

import RNS
from RNS.Interfaces.Interface import Interface
from RNS.Interfaces.TCPInterface import HDLC


class AwareInterface(Interface):
    """Controller interface: owns the Aware session and spawns peer links."""

    BITRATE_GUESS = 10_000_000
    DEFAULT_IFAC_SIZE = 16
    AUTOCONFIGURE_MTU = True
    MAX_PEERS_LIMIT = 8

    @property
    def clients(self):
        return len(self.spawned_interfaces)

    def __init__(self, owner, configuration):
        super().__init__()

        c = Interface.get_config_obj(configuration)
        name = c["name"]
        mode = c["mode"] if "mode" in c else "subscribe"
        peers = int(c["peers"]) if "peers" in c else 4

        self.owner = owner
        self.name = name
        self.online = False
        self.OUT = False
        self.IN = True
        self.spawned_interfaces = []
        self.peers = {}
        self._spawning = set()
        self._lock = threading.Lock()
        self.detached = False
        self.initiator = False
        self.bitrate = self.BITRATE_GUESS
        self.max_peers = max(1, min(peers, self.MAX_PEERS_LIMIT))
        # RNS config machinery sets these post-construction. Provide defaults
        # so spawned peers can be created before or without full config.
        if not hasattr(self, "mode"):
            self.mode = Interface.MODE_FULL
        if not hasattr(self, "ifac_size"):
            self.ifac_size = None
            self.ifac_netname = None
            self.ifac_netkey = None

        try:
            from meshchatx.src.backend import android_locallink
        except Exception:
            android_locallink = None
        self._locallink = android_locallink
        if android_locallink is None or not android_locallink.is_available():
            raise SystemError("AwareInterface requires the Android local-link bridge")

        result = android_locallink.aware_start(mode)
        if not result.get("ok"):
            raise SystemError(f"Aware session start failed: {result.get('error')}")
        android_locallink.register_aware_listener(self._on_aware_event)
        self.online = True
        RNS.log(
            f"Aware session started in {mode} mode for {self}",
            RNS.LOG_VERBOSE,
        )

    # ------------------------------------------------------------------
    # Aware event fan-out
    # ------------------------------------------------------------------

    def _on_aware_event(self, event, peer_id, data):
        if self.detached:
            return
        if event == "link_up":
            self._spawn_peer(peer_id)
        elif event == "data":
            peer = self.peers.get(peer_id)
            if peer is not None:
                peer.feed_bytes(data or b"")
        elif event == "link_down":
            peer = self.peers.pop(peer_id, None)
            if peer is not None:
                peer.teardown()
        elif event == "session_lost":
            self.detach()

    def _spawn_peer(self, peer_id):
        with self._lock:
            if peer_id in self.peers or peer_id in self._spawning:
                return
            if len(self.spawned_interfaces) + len(self._spawning) >= self.max_peers:
                self._locallink.aware_close_peer(peer_id)
                RNS.log(
                    f"Aware peer cap reached on {self}, dropping link {peer_id}",
                    RNS.LOG_DEBUG,
                )
                return
            self._spawning.add(peer_id)
        try:
            self._spawn_peer_impl(peer_id)
        finally:
            with self._lock:
                self._spawning.discard(peer_id)

    def _spawn_peer_impl(self, peer_id):
        spawned = AwarePeerInterface(self.owner, self._locallink, peer_id)

        spawned.OUT = True
        spawned.IN = True
        spawned.ingress_control = self.ingress_control
        spawned.ic_max_held_announces = self.ic_max_held_announces
        spawned.ic_burst_hold = self.ic_burst_hold
        spawned.ic_burst_freq = self.ic_burst_freq
        spawned.ic_burst_freq_new = self.ic_burst_freq_new
        spawned.ic_new_time = self.ic_new_time
        spawned.ic_burst_penalty = self.ic_burst_penalty
        spawned.ic_held_release_interval = self.ic_held_release_interval
        spawned.egress_control = self.egress_control
        spawned.ec_pr_freq = self.ec_pr_freq
        spawned.ic_pr_burst_freq_new = self.ic_pr_burst_freq_new
        spawned.ic_pr_burst_freq = self.ic_pr_burst_freq
        for attr in (
            "announce_rate_target",
            "announce_rate_grace",
            "announce_rate_penalty",
        ):
            if hasattr(self, attr):
                setattr(spawned, attr, getattr(self, attr))
        spawned.mode = self.mode
        spawned.gravity = self.gravity
        spawned.bitrate = self.bitrate
        spawned.HW_MTU = self.HW_MTU
        spawned.parent_interface = self
        spawned.ifac_size = self.ifac_size
        spawned.ifac_netname = self.ifac_netname
        spawned.ifac_netkey = self.ifac_netkey
        if spawned.ifac_netname is not None or spawned.ifac_netkey is not None:
            ifac_origin = b""
            if spawned.ifac_netname is not None:
                ifac_origin += RNS.Identity.full_hash(
                    spawned.ifac_netname.encode("utf-8")
                )
            if spawned.ifac_netkey is not None:
                ifac_origin += RNS.Identity.full_hash(
                    spawned.ifac_netkey.encode("utf-8")
                )
            ifac_origin_hash = RNS.Identity.full_hash(ifac_origin)
            spawned.ifac_key = RNS.Cryptography.hkdf(
                length=64,
                derive_from=ifac_origin_hash,
                salt=RNS.Reticulum.IFAC_SALT,
                context=None,
            )
            spawned.ifac_identity = RNS.Identity.from_bytes(spawned.ifac_key)
            spawned.ifac_signature = spawned.ifac_identity.sign(
                RNS.Identity.full_hash(spawned.ifac_key)
            )
        spawned.optimise_mtu()
        spawned.online = True
        spawned.initiator = False

        with self._lock:
            self.peers[peer_id] = spawned
            self.spawned_interfaces.append(spawned)
        RNS.Transport.add_interface(spawned)
        RNS.log(f"Spawned new Aware peer interface: {spawned}", RNS.LOG_VERBOSE)

    # ------------------------------------------------------------------
    # Interface contract
    # ------------------------------------------------------------------

    def process_outgoing(self, data):
        # The controller never carries packets itself. Spawned peers do.
        pass

    def received_announce(self, size=0, from_spawned=False):
        pass

    def sent_announce(self, size=0, from_spawned=False):
        pass

    def received_path_request(self, size=0, from_spawned=False):
        pass

    def sent_path_request(self, size=0, from_spawned=False):
        pass

    def detach(self):
        self.detached = True
        self.online = False
        self.OUT = False
        self.IN = False
        if self._locallink is not None:
            try:
                self._locallink.unregister_aware_listener(self._on_aware_event)
            except Exception:
                pass
            try:
                self._locallink.aware_stop()
            except Exception:
                pass
        with self._lock:
            peers = list(self.peers.values())
            self.peers.clear()
        for peer in peers:
            peer.teardown()

    def __str__(self):
        return f"AwareInterface[{self.name}]"


class AwarePeerInterface(Interface):
    """Spawned per-peer interface wrapping one Aware data-path socket."""

    AUTOCONFIGURE_MTU = True

    def __init__(self, owner, locallink, peer_id):
        super().__init__()
        self.owner = owner
        self._locallink = locallink
        self.peer_id = peer_id
        self.name = f"aware-peer-{peer_id}"
        self.online = False
        self.OUT = True
        self.IN = True
        self.initiator = False
        self.writing = False
        self.parent_interface = None
        self._rx_lock = threading.Lock()
        self._rx_in_frame = False
        self._rx_escape = False
        self._rx_buf = bytearray()

    def process_outgoing(self, data):
        if not self.online or self.detached:
            return
        try:
            framed = bytes([HDLC.FLAG]) + HDLC.escape(data) + bytes([HDLC.FLAG])
            if not self._locallink.aware_send(self.peer_id, framed):
                RNS.log(
                    f"Aware send failed on {self}, tearing down",
                    RNS.LOG_ERROR,
                )
                self.teardown()
                return
            self.txb += len(framed)
            if self.parent_interface is not None:
                self.parent_interface.txb += len(framed)
        except Exception as e:
            RNS.log(
                f"Exception occurred while transmitting via {self}, "
                f"tearing down interface. The contained exception was: {e}",
                RNS.LOG_ERROR,
            )
            self.teardown()

    def feed_bytes(self, data):
        """HDLC deframe raw socket bytes, dispatch frames to owner.inbound."""
        if not self.online or self.detached or not data:
            return
        frames = []
        with self._rx_lock:
            for byte in data:
                if self._rx_in_frame:
                    if byte == HDLC.FLAG:
                        frames.append(bytes(self._rx_buf))
                        self._rx_buf = bytearray()
                        self._rx_escape = False
                        # FLAG both ends a frame and starts the next one.
                    elif self._rx_escape:
                        self._rx_buf.append(byte ^ HDLC.ESC_MASK)
                        self._rx_escape = False
                    elif byte == HDLC.ESC:
                        self._rx_escape = True
                    else:
                        self._rx_buf.append(byte)
                elif byte == HDLC.FLAG:
                    self._rx_in_frame = True
                    self._rx_escape = False
                    self._rx_buf = bytearray()
            if len(self._rx_buf) > self.HW_MTU * 4 + 64:
                self._rx_buf = bytearray()
                self._rx_in_frame = False
        for frame in frames:
            if self.check_frame_len(len(frame)):
                self.rxb += len(frame)
                if self.parent_interface is not None:
                    self.parent_interface.rxb += len(frame)
                self.owner.inbound(frame, self)
            else:
                RNS.log(
                    f"Invalid HDLC frame of {RNS.prettysize(len(frame))} "
                    f"received on {self}, dropping frame",
                    RNS.LOG_DEBUG,
                )

    def check_frame_len(self, frame_len):
        if frame_len <= RNS.Reticulum.HEADER_MINSIZE:
            return False
        if frame_len > self.HW_MTU + (self.ifac_size or 0):
            return False
        return True

    def process_incoming(self, data):
        if not data:
            return
        if self.online and not self.detached:
            self.rxb += len(data)
            if self.parent_interface is not None:
                self.parent_interface.rxb += len(data)
            self.owner.inbound(data, self)

    def teardown(self):
        if self.detached:
            return
        RNS.log(f"The interface {self} is being torn down.", RNS.LOG_VERBOSE)
        self.detached = True
        self.online = False
        self.OUT = False
        self.IN = False
        try:
            self._locallink.aware_close_peer(self.peer_id)
        except Exception:
            pass
        if self.parent_interface is not None:
            while self in self.parent_interface.spawned_interfaces:
                self.parent_interface.spawned_interfaces.remove(self)
            self.parent_interface.peers.pop(self.peer_id, None)
        if not self.initiator:
            RNS.Transport.remove_interface(self)

    def __str__(self):
        return f"AwarePeerInterface[{self.name}]"


interface_class = AwareInterface
