# SPDX-License-Identifier: 0BSD

"""Connection and link lifecycle mixin for RRCHub."""

import contextlib
import threading
import time

import RNS

from meshchatx.src.backend.path_utils import (
    path_response_window,
    slowest_online_bitrate,
)
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager.constants import (
    SLOW_CHANNEL_BPS,
    _slow_connect_gate,
)
from meshchatx.src.backend.rrc.server import _LoopbackEndpoint


class RRCHubConnectionMixin:
    """Network connection, loopback, hello loop, and raw send for RRCHub."""

    def connect(self):
        with self._lock:
            if self.status in (self.STATUS_CONNECTING, self.STATUS_CONNECTED):
                return
            self._manual_disconnect = False
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            if self._reconnect_attempts > 0:
                text = "Reconnecting (attempt " + str(self._reconnect_attempts) + ")"
            else:
                text = "Connecting"
            self._set_status(self.STATUS_CONNECTING, text)

        t = threading.Thread(target=self._connect_worker, daemon=True)
        t.start()

    def _connect_loopback(self, server):
        self._stop_hello.clear()
        link = _LoopbackEndpoint(self, server)
        server._attach_loopback(link, self.manager.identity)
        with self._lock:
            self.link = link
        self._set_status(self.STATUS_CONNECTING, "Connected locally, sending HELLO")
        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _connect_worker(self):
        try:
            server = self.manager.find_local_server(self.hub_hash)
            if server is not None:
                self._connect_loopback(server)
                return

            timeout_s = 20.0
            bitrate = slowest_online_bitrate()
            gate = (
                _slow_connect_gate
                if bitrate is not None and bitrate < SLOW_CHANNEL_BPS
                else None
            )
            if gate is not None:
                gate.acquire()
            try:
                path_wait = timeout_s
                if not RNS.Transport.has_path(self.hub_hash):
                    RNS.Transport.request_path(self.hub_hash)
                    try:
                        path_wait = path_response_window(self.hub_hash)
                    except Exception:
                        path_wait = float(RNS.Transport.PATH_REQUEST_TIMEOUT)
                    deadline = time.monotonic() + path_wait
                    while time.monotonic() < deadline:
                        if RNS.Transport.has_path(self.hub_hash):
                            break
                        time.sleep(0.1)

                hub_identity = None
                deadline = time.monotonic() + path_wait
                while time.monotonic() < deadline:
                    hub_identity = RNS.Identity.recall(self.hub_hash)
                    if hub_identity is not None:
                        break
                    time.sleep(0.2)
            finally:
                if gate is not None:
                    gate.release()

            if hub_identity is None:
                self._set_status(self.STATUS_FAILED, "Hub identity unknown")
                self._maybe_schedule_reconnect_after_failed_connect()
                return

            app_name, aspects = RNS.Destination.app_and_aspects_from_name(
                self.dest_name,
            )
            hub_dest = RNS.Destination(
                hub_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                app_name,
                *aspects,
            )

            if hub_dest.hash != self.hub_hash:
                self._set_status(
                    self.STATUS_FAILED,
                    "Hash/destination name mismatch",
                )
                self._maybe_schedule_reconnect_after_failed_connect()
                return

            self._stop_hello.clear()
            link = RNS.Link(
                hub_dest,
                established_callback=self._on_established,
                closed_callback=self._on_closed,
            )
            link.set_packet_callback(lambda data, pkt: self._on_packet(data))
            with self._lock:
                self.link = link
        except Exception as e:
            self._set_status(self.STATUS_FAILED, "Connect error: " + str(e))
            self._maybe_schedule_reconnect_after_failed_connect()

    def _maybe_schedule_reconnect_after_failed_connect(self):
        with self._lock:
            if self._manual_disconnect or not self.auto_reconnect:
                return
            if self.link is not None:
                return
        self._schedule_reconnect()

    def _on_established(self, link):
        with contextlib.suppress(Exception):
            link.set_resource_strategy(RNS.Link.ACCEPT_APP)
            link.set_resource_callback(self._resource_advertised)
            link.set_resource_started_callback(self._resource_advertised)
            link.set_resource_concluded_callback(self._resource_concluded)

        try:
            link.identify(self.manager.identity)
        except Exception as e:
            self._log("identify failed: " + str(e), RNS.LOG_ERROR)
            with contextlib.suppress(Exception):
                link.teardown()
            return

        self._set_status(self.STATUS_CONNECTING, "Identified, sending HELLO")

        self._hello_thread = threading.Thread(target=self._hello_loop, daemon=True)
        self._hello_thread.start()

    def _hello_loop(self):
        attempts = 0
        while not self._stop_hello.is_set() and not self.welcomed and attempts < 5:
            with self._lock:
                cur_link = self.link
            if cur_link is None or cur_link.status != RNS.Link.ACTIVE:
                if self.status == self.STATUS_CONNECTING:
                    self._on_closed(cur_link)
                return
            try:
                self._send_hello(cur_link)
            except Exception as e:
                self._log("HELLO send failed: " + str(e), RNS.LOG_ERROR)
            attempts += 1
            self._stop_hello.wait(timeout=3.0)
        if not self.welcomed and not self._stop_hello.is_set():
            self._fail_welcome_timeout()

    def _fail_welcome_timeout(self):
        self._set_status(self.STATUS_FAILED, "WELCOME timeout")
        with self._lock:
            link = self.link
        if link is not None:
            with contextlib.suppress(Exception):
                link.teardown()
        with self._lock:
            if self.link is link:
                self.link = None
        if self.status == self.STATUS_FAILED:
            self._maybe_schedule_reconnect_after_failed_connect()

    def _send_hello(self, link):
        body = {
            proto.B_HELLO_NAME: proto.HELLO_CLIENT_NAME,
            proto.B_HELLO_VER: proto.HELLO_CLIENT_VERSION,
            proto.B_HELLO_CAPS: {
                proto.CAP_RESOURCE_ENVELOPE: True,
                proto.CAP_ACTION: True,
            },
        }
        env = proto.make_envelope(
            proto.T_HELLO,
            src=self.manager.identity.hash,
            body=body,
        )
        nick = self.get_effective_nick()
        if nick:
            env[proto.K_NICK] = nick
        payload = proto.encode(env)
        self._raw_send(link, payload)

    def _on_closed(self, link):
        self._stop_hello.set()
        with self._lock:
            was_welcomed = self.welcomed
            rooms = list(self.rooms)
            manual = self._manual_disconnect
            self.link = None
            self.welcomed = False
            self.motd = None
            self.members.clear()
            self._resource_expectations.clear()
            self._pending_joins.clear()
            self._pending_parts.clear()
            self._silent_joins.clear()
            self._silent_who_rooms.clear()
            should_reconnect = self.auto_reconnect and not self._manual_disconnect
        if was_welcomed and rooms:
            text = "Disconnected from hub" if manual else "Connection lost"
            self._record_connection_event(text, rooms=rooms)
        self._set_status(self.STATUS_DISCONNECTED, "Disconnected")
        if should_reconnect:
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        with self._lock:
            self._reconnect_attempts += 1
            backoff = min(60.0, max(1.0, 2.0 ** min(self._reconnect_attempts, 6)))
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()

            self._reconnect_timer = threading.Timer(backoff, self._fire_reconnect)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()
            self._set_status(
                self.STATUS_DISCONNECTED,
                "Reconnect in " + str(int(backoff)) + "s",
            )

    def _fire_reconnect(self):
        with self._lock:
            self._reconnect_timer = None
            if self._manual_disconnect or not self.auto_reconnect:
                return
        self.connect()

    def disconnect(self):
        self._stop_hello.set()
        with self._lock:
            self._manual_disconnect = True
            self._reconnect_attempts = 0
            if self._reconnect_timer is not None:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None
            link = self.link
            self.link = None
        if link is not None:
            with contextlib.suppress(Exception):
                link.teardown()
        self._set_status(self.STATUS_DISCONNECTED, "Disconnected")

    def _packet_would_fit(self, link, payload):
        try:
            pkt = RNS.Packet(link, payload)
            pkt.pack()
            return True
        except Exception:
            return False

    def _raw_send(self, link, payload):
        if isinstance(link, _LoopbackEndpoint):
            link.from_client(payload)
        else:
            RNS.Packet(link, payload).send()

    def _send_env(self, env):
        with self._lock:
            link = self.link
        if link is None or link.status != RNS.Link.ACTIVE:
            msg = "not connected"
            raise RuntimeError(msg)
        payload = proto.encode(env)
        if isinstance(link, _LoopbackEndpoint):
            link.from_client(payload)
            return
        if not self._packet_would_fit(link, payload):
            msg = "message exceeds link MTU"
            raise RuntimeError(msg)
        RNS.Packet(link, payload).send()

    def _send_env_then_maybe_record(self, env, local_msg):
        """Send on the wire, then record local history if send succeeded.

        Mesh send is async, so the local echo still lands before a remote
        reply. Loopback delivery is synchronous, so the echo is recorded
        first or the hub notice would appear above the typed command.
        """
        with self._lock:
            link = self.link
            loopback = isinstance(link, _LoopbackEndpoint)
        if link is None or link.status != RNS.Link.ACTIVE:
            msg = "not connected"
            raise RuntimeError(msg)
        if local_msg is not None and loopback:
            self._record_message(local_msg, local=True)
        self._send_env(env)
        if local_msg is not None and not loopback:
            self._record_message(local_msg, local=True)
