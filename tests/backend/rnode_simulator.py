# SPDX-License-Identifier: 0BSD

"""KISS-protocol RNode simulator over TCP for tests.

Listens on a local TCP port and speaks enough of the RNode device protocol
(KISS framing over the link) for RNS's RNodeInterface to detect, configure,
and exchange data with it, without any radio hardware.

Failure knobs let tests exercise the bad paths:

- fw_version below RNS's required minimum triggers the firmware panic path
- respond_to_detect=False leaves the interface stuck at device detect
- mirror_config=False makes validation see wrong radio parameters
- loopback=False keeps received data frames instead of echoing them
"""

from __future__ import annotations

import socket
import threading

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

CMD_DATA = 0x00
CMD_FREQUENCY = 0x01
CMD_BANDWIDTH = 0x02
CMD_TXPOWER = 0x03
CMD_SF = 0x04
CMD_CR = 0x05
CMD_RADIO_STATE = 0x06
CMD_DETECT = 0x08
CMD_LEAVE = 0x0A
CMD_ST_ALOCK = 0x0B
CMD_LT_ALOCK = 0x0C
CMD_READY = 0x0F
CMD_PLATFORM = 0x48
CMD_MCU = 0x49
CMD_FW_VERSION = 0x50
CMD_RESET = 0x55
CMD_ERROR = 0x90

DETECT_REQ = 0x73
DETECT_RESP = 0x46

RADIO_STATE_ON = 0x01
PLATFORM_ESP32 = 0x80
MCU_ESP32 = 0x30

ERROR_INITRADIO = 0x01


def kiss_escape(data: bytes) -> bytes:
    data = data.replace(bytes([FESC]), bytes([FESC, TFESC]))
    return data.replace(bytes([FEND]), bytes([FESC, TFEND]))


def kiss_frame(command: int, payload: bytes = b"") -> bytes:
    return bytes([FEND, command]) + kiss_escape(payload) + bytes([FEND])


class _KissParser:
    """Stateful KISS deframer. Keeps a partial frame across recv() chunks."""

    def __init__(self):
        self.in_frame = False
        self.escaped = False
        self.buf = bytearray()

    def feed(self, stream: bytes):
        frames = []
        for byte in stream:
            if byte == FEND:
                if self.in_frame and self.buf:
                    frames.append((self.buf[0], bytes(self.buf[1:])))
                self.in_frame = True
                self.escaped = False
                self.buf = bytearray()
                continue
            if not self.in_frame:
                continue
            if byte == FESC and not self.escaped:
                self.escaped = True
                continue
            if self.escaped:
                if byte == TFEND:
                    byte = FEND
                elif byte == TFESC:
                    byte = FESC
                self.escaped = False
            self.buf.append(byte)
        return frames


class RNodeSimulator:
    """A TCP RNode device speaking KISS.

    Echoes radio configuration commands back so the interface's
    validateRadioState() succeeds, answers detect/firmware/platform/MCU
    probes, and collects CMD_DATA payloads. Use inject_data() to deliver an
    inbound frame to the connected interface.
    """

    def __init__(
        self,
        *,
        fw_version=(1, 60),
        platform=PLATFORM_ESP32,
        mcu=MCU_ESP32,
        respond_to_detect=True,
        mirror_config=True,
        loopback=False,
    ):
        self.fw_version = fw_version
        self.platform = platform
        self.mcu = mcu
        self.respond_to_detect = respond_to_detect
        self.mirror_config = mirror_config
        self.loopback = loopback

        self.received_data: list[bytes] = []
        self.radio_state = 0
        self.config: dict[str, object] = {}
        self.connections = 0

        self._sock: socket.socket | None = None
        self._client: socket.socket | None = None
        self._client_lock = threading.Lock()
        self._running = False
        self._bind_port = 0
        self._threads: list[threading.Thread] = []

    @property
    def port(self) -> int:
        return self._bind_port

    def start(self) -> RNodeSimulator:
        """Start listening. Re-binds the previous port after stop/start."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", self._bind_port))
        self._bind_port = self._sock.getsockname()[1]
        self._sock.listen(2)
        self._sock.settimeout(0.5)
        self._running = True
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        self._threads.append(t)
        return self

    def stop(self):
        self._running = False
        with self._client_lock:
            if self._client is not None:
                try:
                    self._client.close()
                except OSError:
                    pass
                self._client = None
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        for t in self._threads:
            t.join(timeout=2.0)

    def inject_data(self, payload: bytes) -> bool:
        """Send an inbound CMD_DATA frame to the connected interface."""
        with self._client_lock:
            if self._client is None:
                return False
            try:
                self._client.sendall(kiss_frame(CMD_DATA, payload))
                return True
            except OSError:
                return False

    def _accept_loop(self):
        while self._running:
            try:
                client, _addr = self._sock.accept()
            except (TimeoutError, OSError):
                continue
            client.settimeout(0.5)
            with self._client_lock:
                if self._client is not None:
                    try:
                        self._client.close()
                    except OSError:
                        pass
                self._client = client
            self.connections += 1
            t = threading.Thread(target=self._serve, args=(client,), daemon=True)
            t.start()
            self._threads.append(t)

    def _send(self, client: socket.socket, command: int, payload: bytes = b""):
        try:
            client.sendall(kiss_frame(command, payload))
        except OSError:
            pass

    def _serve(self, client: socket.socket):
        parser = _KissParser()
        while self._running:
            try:
                chunk = client.recv(4096)
            except TimeoutError:
                continue
            except OSError:
                break
            if not chunk:
                break
            for command, payload in parser.feed(chunk):
                self._handle(client, command, payload)
        with self._client_lock:
            if self._client is client:
                self._client = None
        try:
            client.close()
        except OSError:
            pass

    def _handle(self, client: socket.socket, command: int, payload: bytes):
        if command == CMD_DETECT:
            if payload and payload[0] == DETECT_REQ and self.respond_to_detect:
                self._send(client, CMD_DETECT, bytes([DETECT_RESP]))
        elif command == CMD_FW_VERSION:
            self._send(
                client, CMD_FW_VERSION, bytes([self.fw_version[0], self.fw_version[1]])
            )
        elif command == CMD_PLATFORM:
            self._send(client, CMD_PLATFORM, bytes([self.platform]))
        elif command == CMD_MCU:
            self._send(client, CMD_MCU, bytes([self.mcu]))
        elif command == CMD_FREQUENCY and len(payload) == 4:
            self.config["frequency"] = int.from_bytes(payload, "big")
            if self.mirror_config:
                self._send(client, CMD_FREQUENCY, payload)
        elif command == CMD_BANDWIDTH and len(payload) == 4:
            self.config["bandwidth"] = int.from_bytes(payload, "big")
            if self.mirror_config:
                self._send(client, CMD_BANDWIDTH, payload)
        elif command == CMD_TXPOWER and payload:
            self.config["txpower"] = payload[0]
            if self.mirror_config:
                self._send(client, CMD_TXPOWER, payload)
        elif command == CMD_SF and payload:
            self.config["spreadingfactor"] = payload[0]
            if self.mirror_config:
                self._send(client, CMD_SF, payload)
        elif command == CMD_CR and payload:
            self.config["codingrate"] = payload[0]
            if self.mirror_config:
                self._send(client, CMD_CR, payload)
        elif command == CMD_RADIO_STATE and payload:
            self.radio_state = payload[0]
            if self.mirror_config:
                self._send(client, CMD_RADIO_STATE, payload)
            if self.radio_state == RADIO_STATE_ON:
                # Signal ready so flow-controlled sends can proceed.
                self._send(client, CMD_READY, b"")
        elif command == CMD_ST_ALOCK and len(payload) == 2:
            if self.mirror_config:
                self._send(client, CMD_ST_ALOCK, payload)
        elif command == CMD_LT_ALOCK and len(payload) == 2:
            if self.mirror_config:
                self._send(client, CMD_LT_ALOCK, payload)
        elif command == CMD_DATA:
            self.received_data.append(payload)
            if self.loopback:
                self._send(client, CMD_DATA, payload)
        elif command == CMD_LEAVE:
            try:
                client.close()
            except OSError:
                pass
        elif command == CMD_RESET:
            pass
