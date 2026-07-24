import asyncio
import os
import socket
import ssl
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Empty, Queue
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

import httpx
import RNS
from RNS.Interfaces.Interface import Interface


class HDLC:
    """Pipe-compatible simplified HDLC framing for HTTP bodies.

    Same FLAG/ESC scheme as RNS PipeInterface so multiple packets can
    share one HTTP request or response without losing boundaries.
    """

    FLAG = 0x7E
    ESC = 0x7D
    ESC_MASK = 0x20

    @staticmethod
    def escape(data):
        data = data.replace(
            bytes([HDLC.ESC]),
            bytes([HDLC.ESC, HDLC.ESC ^ HDLC.ESC_MASK]),
        )
        data = data.replace(
            bytes([HDLC.FLAG]),
            bytes([HDLC.ESC, HDLC.FLAG ^ HDLC.ESC_MASK]),
        )
        return data

    @staticmethod
    def frame(packet):
        return bytes([HDLC.FLAG]) + HDLC.escape(packet) + bytes([HDLC.FLAG])

    @staticmethod
    def deframe(buffer, max_frame_len):
        """Return (packets, remainder) from an HDLC byte buffer."""
        packets = []
        in_frame = False
        escape = False
        data_buffer = bytearray()
        i = 0
        last_complete = 0

        while i < len(buffer):
            byte = buffer[i]
            i += 1

            if in_frame and byte == HDLC.FLAG:
                packets.append(bytes(data_buffer))
                in_frame = False
                escape = False
                data_buffer = bytearray()
                last_complete = i
            elif byte == HDLC.FLAG:
                in_frame = True
                escape = False
                data_buffer = bytearray()
            elif in_frame and len(data_buffer) < max_frame_len:
                if byte == HDLC.ESC:
                    escape = True
                else:
                    if escape:
                        if byte == HDLC.FLAG ^ HDLC.ESC_MASK:
                            byte = HDLC.FLAG
                        elif byte == HDLC.ESC ^ HDLC.ESC_MASK:
                            byte = HDLC.ESC
                        escape = False
                    data_buffer.append(byte)

        remainder = buffer[last_complete:] if in_frame else b""
        return packets, remainder


class _H3Session:
    """Persistent HTTP/3 client over one QUIC connection."""

    def __init__(self, server_url, user_agent, verify=True, ca_certs=None):
        from aioquic.asyncio import connect
        from aioquic.asyncio.protocol import QuicConnectionProtocol
        from aioquic.h3.connection import H3_ALPN, H3Connection
        from aioquic.h3.events import DataReceived, HeadersReceived
        from aioquic.quic.configuration import QuicConfiguration
        from aioquic.quic.events import QuicEvent

        parsed = urlparse(server_url)
        if parsed.scheme != "https":
            raise ValueError("HTTP/3 requires an https:// server_url")

        self._host = parsed.hostname
        self._port = parsed.port or 443
        self._path = parsed.path or "/"
        if parsed.query:
            self._path += "?" + parsed.query
        self._authority = parsed.netloc
        self._user_agent = user_agent
        self._closed = False
        self._request_count = 0

        configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
        if not verify:
            configuration.verify_mode = ssl.CERT_NONE
        elif ca_certs:
            configuration.load_verify_locations(ca_certs)

        class _Client(QuicConnectionProtocol):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._http = H3Connection(self._quic)
                self._request_events = {}
                self._request_waiter = {}

            def http_event_received(self, event):
                if isinstance(event, (HeadersReceived, DataReceived)):
                    stream_id = event.stream_id
                    if stream_id in self._request_events:
                        self._request_events[stream_id].append(event)
                        if event.stream_ended:
                            waiter = self._request_waiter.pop(stream_id)
                            waiter.set_result(self._request_events.pop(stream_id))

            def quic_event_received(self, event: QuicEvent):
                for http_event in self._http.handle_event(event):
                    self.http_event_received(http_event)

            async def post_bytes(self, path, authority, user_agent, data):
                stream_id = self._quic.get_next_available_stream_id()
                headers = [
                    (b":method", b"POST"),
                    (b":scheme", b"https"),
                    (b":authority", authority.encode()),
                    (b":path", path.encode()),
                    (b"user-agent", user_agent.encode()),
                    (b"content-type", b"application/octet-stream"),
                    (b"content-length", str(len(data)).encode()),
                ]
                self._http.send_headers(
                    stream_id=stream_id,
                    headers=headers,
                    end_stream=not data,
                )
                if data:
                    self._http.send_data(
                        stream_id=stream_id, data=data, end_stream=True
                    )

                waiter = self._loop.create_future()
                self._request_events[stream_id] = deque()
                self._request_waiter[stream_id] = waiter
                self.transmit()
                events = await asyncio.shield(waiter)

                status = 0
                body = b""
                for event in events:
                    if isinstance(event, HeadersReceived):
                        for key, value in event.headers:
                            if key == b":status":
                                status = int(value.decode())
                    elif isinstance(event, DataReceived):
                        body += event.data
                return status, body

        self._Client = _Client
        self._connect = connect
        self._configuration = configuration
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_loop,
            name="h3-client-loop",
            daemon=True,
        )
        self._ready = threading.Event()
        self._error = None
        self._client = None
        self._cm = None
        self._loop_thread.start()
        if not self._ready.wait(timeout=30):
            raise TimeoutError("HTTP/3 client failed to connect")
        if self._error is not None:
            raise self._error

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._open())
            self._ready.set()
            self._loop.run_forever()
        except Exception as exc:
            self._error = exc
            self._ready.set()

    async def _open(self):
        self._cm = self._connect(
            self._host,
            self._port,
            configuration=self._configuration,
            create_protocol=self._Client,
        )
        self._client = await self._cm.__aenter__()

    def post(self, data, timeout=10.0):
        if self._closed:
            raise RuntimeError("HTTP/3 session is closed")

        async def _do_post():
            status, body = await self._client.post_bytes(
                self._path,
                self._authority,
                self._user_agent,
                data,
            )
            self._request_count += 1
            if status >= 400:
                raise RuntimeError(f"HTTP/3 status {status}")
            return body

        fut = asyncio.run_coroutine_threadsafe(_do_post(), self._loop)
        return fut.result(timeout=timeout)

    def close(self):
        if self._closed:
            return
        self._closed = True

        async def _close():
            if self._cm is not None:
                await self._cm.__aexit__(None, None, None)

        try:
            fut = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            fut.result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join(timeout=5)


class HTTPTunnelInterface(Interface):
    """HTTP Tunnel Interface for Reticulum.

    Bidirectional RNS transport over HTTP POST with pipe-compatible HDLC
    framing. Supports HTTP/1.1 (default), HTTP/2, and HTTP/3.

    Engineering defaults:
      - http_version=1 uses a stdlib HTTP/1.1 server and httpx client.
        Works over cleartext http:// and is ideal behind Caddy/nginx.
      - http_version=2 requires TLS and uses Hypercorn (h2) + httpx(http2).
      - http_version=3 requires TLS and uses Hypercorn QUIC + a persistent
        aioquic HTTP/3 client session.

    Configuration highlights:
        http_version: 1, 2, or 3 (default: 1)
        tls_certfile / tls_keyfile: required for versions 2 and 3 on server
        tls_verify: verify TLS certs on client (default: true)
        tls_ca_certs: optional CA bundle path for client verify
        server_url: use https:// for versions 2 and 3
    """

    DEFAULT_IFAC_SIZE = 16
    BITRATE_GUESS = 10_000_000
    AUTOCONFIGURE_MTU = True

    DEFAULT_MTU = 4096
    TUNNEL_USER_AGENT = "RNS-HTTP-Tunnel/1.0"
    DEFAULT_POLL_INTERVAL = 0.1
    DEFAULT_POOL_CONNECTIONS = 1
    DEFAULT_POOL_MAXSIZE = 1
    DEFAULT_KEEPALIVE_TIMEOUT = 60
    DEFAULT_HTTP_VERSION = 1

    def __init__(self, owner, configuration):
        super().__init__()

        ifconf = Interface.get_config_obj(configuration)

        self.name = ifconf["name"]

        mode = str(ifconf["mode"]).lower() if "mode" in ifconf else "client"
        listen_host = ifconf["listen_host"] if "listen_host" in ifconf else "0.0.0.0"
        listen_port = int(ifconf["listen_port"]) if "listen_port" in ifconf else 8080
        server_url = ifconf["server_url"] if "server_url" in ifconf else None
        poll_interval = (
            float(ifconf["poll_interval"])
            if "poll_interval" in ifconf
            else self.DEFAULT_POLL_INTERVAL
        )
        check_user_agent = (
            ifconf.as_bool("check_user_agent") if "check_user_agent" in ifconf else True
        )
        user_agent = (
            str(ifconf["user_agent"])
            if "user_agent" in ifconf
            else self.TUNNEL_USER_AGENT
        )
        mtu = int(ifconf["mtu"]) if "mtu" in ifconf else self.DEFAULT_MTU
        serve_html_page = (
            ifconf.as_bool("serve_html_page") if "serve_html_page" in ifconf else False
        )
        html_file_path = (
            ifconf["html_file_path"] if "html_file_path" in ifconf else None
        )
        pool_connections = (
            int(ifconf["pool_connections"])
            if "pool_connections" in ifconf
            else self.DEFAULT_POOL_CONNECTIONS
        )
        pool_maxsize = (
            int(ifconf["pool_maxsize"])
            if "pool_maxsize" in ifconf
            else self.DEFAULT_POOL_MAXSIZE
        )
        keepalive_timeout = (
            int(ifconf["keepalive_timeout"])
            if "keepalive_timeout" in ifconf
            else self.DEFAULT_KEEPALIVE_TIMEOUT
        )
        http_version = (
            int(ifconf["http_version"])
            if "http_version" in ifconf
            else self.DEFAULT_HTTP_VERSION
        )
        tls_certfile = ifconf["tls_certfile"] if "tls_certfile" in ifconf else None
        tls_keyfile = ifconf["tls_keyfile"] if "tls_keyfile" in ifconf else None
        tls_verify = ifconf.as_bool("tls_verify") if "tls_verify" in ifconf else True
        tls_ca_certs = ifconf["tls_ca_certs"] if "tls_ca_certs" in ifconf else None

        self.mode = mode
        self.http_version = http_version

        if mode not in ["client", "server"]:
            raise ValueError(
                f"Invalid mode '{mode}' for {self}. Must be 'client' or 'server'",
            )

        if http_version not in (1, 2, 3):
            raise ValueError(
                f"Invalid http_version '{http_version}' for {self}. Must be 1, 2, or 3",
            )

        if mode == "client" and server_url is None:
            raise ValueError(f"No server_url specified for client mode in {self}")

        if pool_connections < 1 or pool_maxsize < 1:
            raise ValueError(
                f"pool_connections and pool_maxsize must be >= 1 for {self}",
            )

        if http_version >= 2:
            if mode == "server" and (not tls_certfile or not tls_keyfile):
                raise ValueError(
                    f"tls_certfile and tls_keyfile are required for "
                    f"HTTP/{http_version} server mode in {self}",
                )
            if mode == "client":
                parsed = urlparse(server_url)
                if parsed.scheme != "https":
                    raise ValueError(
                        f"HTTP/{http_version} client requires https:// server_url in {self}",
                    )

        self.owner = owner
        self.IN = True
        self.mtu = mtu
        self.check_user_agent = check_user_agent
        self.user_agent = user_agent
        self.serve_html_page = serve_html_page
        self.html_file_path = html_file_path
        self.html_content = None
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.keepalive_timeout = keepalive_timeout
        self.tls_certfile = tls_certfile
        self.tls_keyfile = tls_keyfile
        self.tls_verify = tls_verify
        self.tls_ca_certs = tls_ca_certs
        self._tcp_accepts = 0
        self._http_requests = 0
        self._stats_lock = threading.Lock()
        self._last_http_version = None
        self._client_requests = 0
        self.session = None
        self._h3_session = None
        self._asgi_shutdown = None
        self._asgi_loop = None

        if self.serve_html_page and self.html_file_path:
            self._load_html_content()

        self._recv_queue = Queue()
        self._send_queue = Queue()
        self._stop_event = threading.Event()
        self._frame_remainder = b""
        self._frame_lock = threading.Lock()

        self.HW_MTU = mtu
        self.online = False
        self.bitrate = HTTPTunnelInterface.BITRATE_GUESS

        if mode == "server":
            self.listen_host = listen_host
            self.listen_port = listen_port
        else:
            self.server_url = server_url
            self.poll_interval = poll_interval

        self.optimise_mtu()

        if mode == "server":
            if http_version == 1:
                self.setup_server_http1()
            else:
                self.setup_server_asgi()
        else:
            self.setup_client()

    def _load_html_content(self):
        try:
            if os.path.isfile(self.html_file_path):
                with open(self.html_file_path, encoding="utf-8") as f:
                    self.html_content = f.read()
                RNS.log(f"Loaded HTML content from {self.html_file_path}", RNS.LOG_INFO)
            else:
                RNS.log(f"HTML file not found: {self.html_file_path}", RNS.LOG_WARNING)
                self.html_content = None
        except Exception as e:
            RNS.log(
                f"Error loading HTML file {self.html_file_path}: {e}",
                RNS.LOG_ERROR,
            )
            self.html_content = None

    def _drain_send_frames(self):
        parts = []
        while not self._send_queue.empty():
            try:
                packet = self._send_queue.get_nowait()
            except Empty:
                break
            if packet:
                parts.append(HDLC.frame(packet))
        return b"".join(parts)

    def _ingest_wire_bytes(self, wire_data):
        if not wire_data:
            return

        with self._frame_lock:
            buffer = self._frame_remainder + wire_data
            packets, self._frame_remainder = HDLC.deframe(buffer, self.HW_MTU)

        for packet in packets:
            if packet:
                self._recv_queue.put(packet)

    def _record_http_request(self):
        with self._stats_lock:
            self._http_requests += 1

    def _handle_tunnel_exchange(self, method, path, headers, body):
        """Shared request handler for HTTP/1.1 and ASGI paths.

        Returns (status, content_type, response_body).
        """
        self._record_http_request()
        headers_l = {str(k).lower(): str(v) for k, v in headers.items()}

        if method == "GET" and path == "/":
            if self.serve_html_page and self.html_content:
                return (
                    200,
                    "text/html; charset=utf-8",
                    self.html_content.encode("utf-8"),
                )
            return 404, "text/plain", b""

        if method == "POST" and path == "/":
            if self.check_user_agent:
                user_agent = headers_l.get("user-agent", "")
                if user_agent != self.user_agent:
                    RNS.log(
                        f"Rejected request with invalid User-Agent: {user_agent}",
                        RNS.LOG_WARNING,
                    )
                    return 403, "text/plain", b"Forbidden"

            if body:
                RNS.log(f"Received {len(body)} bytes from client", RNS.LOG_EXTREME)
                self._ingest_wire_bytes(body)

            server_data = self._drain_send_frames()
            if server_data:
                RNS.log(
                    f"Sending {len(server_data)} framed bytes to client",
                    RNS.LOG_EXTREME,
                )
            return 200, "application/octet-stream", server_data

        return 404, "text/plain", b""

    def connection_stats(self):
        with self._stats_lock:
            stats = {
                "tcp_accepts": self._tcp_accepts,
                "http_requests": self._http_requests,
                "client_requests": self._client_requests,
                "last_http_version": self._last_http_version,
                "configured_http_version": self.http_version,
            }
        if self._h3_session is not None:
            stats["pool_num_connections"] = 0 if self._h3_session._closed else 1
            stats["pool_num_requests"] = self._h3_session._request_count
        return stats

    def _build_asgi_app(self):
        interface = self

        async def app(scope, receive, send):
            if scope["type"] != "http":
                return

            headers = {
                key.decode("latin1"): value.decode("latin1")
                for key, value in scope.get("headers", [])
            }
            body = b""
            while True:
                message = await receive()
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

            status, content_type, response_body = interface._handle_tunnel_exchange(
                scope.get("method", "GET"),
                scope.get("path", "/"),
                headers,
                body,
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [
                        (b"content-type", content_type.encode()),
                        (b"content-length", str(len(response_body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": response_body})

        return app

    def setup_server_http1(self):
        interface_instance = self

        class TunnelRequestHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _send_common_headers(self, content_type, content_length):
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(content_length))
                self.send_header("Connection", "keep-alive")
                self.send_header(
                    "Keep-Alive",
                    f"timeout={interface_instance.keepalive_timeout}, max=1000",
                )

            def do_GET(self):
                status, content_type, body = interface_instance._handle_tunnel_exchange(
                    "GET",
                    self.path,
                    self.headers,
                    b"",
                )
                self.send_response(status)
                self._send_common_headers(content_type, len(body))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length > 0 else b""
                status, content_type, response = (
                    interface_instance._handle_tunnel_exchange(
                        "POST",
                        self.path,
                        self.headers,
                        body,
                    )
                )
                self.send_response(status)
                self._send_common_headers(content_type, len(response))
                self.end_headers()
                if response:
                    self.wfile.write(response)

            def log_message(self, fmt, *args):
                pass

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

            def get_request(self):
                request, client_address = super().get_request()
                with interface_instance._stats_lock:
                    interface_instance._tcp_accepts += 1
                try:
                    request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except OSError:
                    pass
                return request, client_address

        def run_server():
            try:
                self._http_server = ThreadedHTTPServer(
                    (self.listen_host, self.listen_port),
                    TunnelRequestHandler,
                )
                self._http_server.daemon_threads = True
                self._http_server.serve_forever()
            except Exception as e:
                if not self._stop_event.is_set():
                    RNS.log(f"HTTP server error for {self}: {e}", RNS.LOG_ERROR)
                    if RNS.Reticulum.panic_on_interface_error:
                        RNS.panic()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        self._start_receive_loop()
        self.online = True
        RNS.log(
            f"HTTP/1.1 server started on http://{self.listen_host}:{self.listen_port}",
            RNS.LOG_NOTICE,
        )

    def setup_server_asgi(self):
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        bind = f"{self.listen_host}:{self.listen_port}"
        config.bind = [bind]
        config.certfile = self.tls_certfile
        config.keyfile = self.tls_keyfile
        config.alpn_protocols = ["h2", "http/1.1"]
        if self.http_version == 3:
            config.quic_bind = [bind]
            config.alpn_protocols = ["h3", "h2", "http/1.1"]

        app = self._build_asgi_app()
        self._asgi_shutdown = asyncio.Event()

        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._asgi_loop = loop
            try:
                loop.run_until_complete(
                    serve(app, config, shutdown_trigger=self._asgi_shutdown.wait),
                )
            except Exception as e:
                if not self._stop_event.is_set():
                    RNS.log(f"ASGI HTTP server error for {self}: {e}", RNS.LOG_ERROR)
                    if RNS.Reticulum.panic_on_interface_error:
                        RNS.panic()
            finally:
                loop.close()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        self._start_receive_loop()
        self.online = True
        proto = f"HTTP/{self.http_version}"
        RNS.log(
            f"{proto} server started on https://{self.listen_host}:{self.listen_port}",
            RNS.LOG_NOTICE,
        )

    def _start_receive_loop(self):
        thread = threading.Thread(target=self.receive_loop, daemon=True)
        thread.start()

    def setup_client(self):
        self._consecutive_failures = 0
        self._max_backoff = 30.0

        if self.http_version == 3:
            self._h3_session = _H3Session(
                self.server_url,
                self.user_agent,
                verify=self.tls_verify,
                ca_certs=self.tls_ca_certs,
            )
            self._last_http_version = "HTTP/3"
        else:
            verify = self.tls_ca_certs if self.tls_ca_certs else self.tls_verify
            limits = httpx.Limits(
                max_connections=max(self.pool_maxsize, 1),
                max_keepalive_connections=max(self.pool_maxsize, 1),
                keepalive_expiry=float(self.keepalive_timeout),
            )
            self.session = httpx.Client(
                http2=(self.http_version == 2),
                verify=verify,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "identity",
                },
                limits=limits,
                timeout=httpx.Timeout(5.0),
            )

        thread = threading.Thread(target=self.client_loop, daemon=True)
        thread.start()
        self.online = True
        RNS.log(
            f"HTTP/{self.http_version} client started, connecting to {self.server_url}",
            RNS.LOG_NOTICE,
        )

    def receive_loop(self):
        while not self._stop_event.is_set():
            try:
                received_data = self._recv_queue.get(timeout=1)
                if received_data:
                    self.process_incoming(received_data)
            except Empty:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    RNS.log(f"Error in receive loop for {self}: {e}", RNS.LOG_ERROR)

    def _client_exchange(self, data_to_send):
        if self.http_version == 3:
            body = self._h3_session.post(data_to_send, timeout=5.0)
            self._client_requests += 1
            self._last_http_version = "HTTP/3"
            return body

        response = self.session.post(self.server_url, content=data_to_send)
        response.raise_for_status()
        self._client_requests += 1
        self._last_http_version = response.http_version
        return response.content

    def client_loop(self):
        while not self._stop_event.is_set():
            data_to_send = self._drain_send_frames()

            try:
                RNS.log(
                    f"Sending {len(data_to_send)} framed bytes to server",
                    RNS.LOG_EXTREME,
                )
                content = self._client_exchange(data_to_send)

                if content:
                    RNS.log(
                        f"Received {len(content)} bytes from server",
                        RNS.LOG_EXTREME,
                    )
                    self._ingest_wire_bytes(content)

                    while not self._recv_queue.empty():
                        try:
                            packet = self._recv_queue.get_nowait()
                        except Empty:
                            break
                        if packet:
                            self.process_incoming(packet)

                if self._consecutive_failures > 0:
                    RNS.log(f"Reconnected to server for {self}", RNS.LOG_INFO)
                    self._consecutive_failures = 0

            except Exception as e:
                if self._stop_event.is_set():
                    break
                self._consecutive_failures += 1
                if self._consecutive_failures % 10 == 1:
                    RNS.log(
                        f"Error communicating with server for {self} "
                        f"(attempt {self._consecutive_failures}): {e}",
                        RNS.LOG_WARNING,
                    )

            if self._stop_event.is_set():
                break

            if self._consecutive_failures > 0:
                delay = min(
                    self.poll_interval * (2 ** min(self._consecutive_failures - 1, 5)),
                    self._max_backoff,
                )
            else:
                delay = self.poll_interval

            self._stop_event.wait(delay)

    def process_incoming(self, data):
        if len(data) > 0 and self.online:
            self.rxb += len(data)
            self.owner.inbound(data, self)

    def process_outgoing(self, data):
        if self.online:
            if len(data) > self.mtu:
                RNS.log(
                    f"Payload too large ({len(data)} > {self.mtu}) for {self}",
                    RNS.LOG_ERROR,
                )
                return

            self._send_queue.put(data)
            self.txb += len(data)

    def detach(self):
        RNS.log(f"Detaching {self}", RNS.LOG_DEBUG)
        self._stop_event.set()
        self.online = False

        if self.mode == "client":
            if self.session is not None:
                try:
                    self.session.close()
                except Exception as e:
                    RNS.log(
                        f"Error closing HTTP session for {self}: {e}",
                        RNS.LOG_DEBUG,
                    )
            if self._h3_session is not None:
                try:
                    self._h3_session.close()
                except Exception as e:
                    RNS.log(
                        f"Error closing HTTP/3 session for {self}: {e}",
                        RNS.LOG_DEBUG,
                    )

        if self.mode == "server":
            if self.http_version == 1:
                httpd = getattr(self, "_http_server", None)
                if httpd is not None:

                    def _shutdown():
                        try:
                            httpd.shutdown()
                        except Exception:
                            pass
                        try:
                            httpd.server_close()
                        except Exception:
                            pass

                    threading.Thread(target=_shutdown, daemon=True).start()

                if hasattr(self, "_server_thread") and self._server_thread:
                    self._server_thread.join(timeout=2)
                    if self._server_thread.is_alive() and httpd is not None:
                        try:
                            httpd.socket.close()
                        except Exception:
                            pass
                        self._server_thread.join(timeout=1)
            else:
                if self._asgi_loop is not None and self._asgi_shutdown is not None:
                    self._asgi_loop.call_soon_threadsafe(self._asgi_shutdown.set)
                if hasattr(self, "_server_thread") and self._server_thread:
                    self._server_thread.join(timeout=5)

    def should_ingress_limit(self):
        return False

    def __str__(self):
        name = getattr(self, "name", "?")
        ver = getattr(self, "http_version", "?")
        if self.mode == "server":
            lh = getattr(self, "listen_host", "?")
            lp = getattr(self, "listen_port", "?")
            return f"HTTPTunnelInterface[{name}/HTTP{ver}/server/{lh}:{lp}]"
        if self.mode == "client" and getattr(self, "server_url", None) is not None:
            return f"HTTPTunnelInterface[{name}/HTTP{ver}/client/{self.server_url}]"
        return f"HTTPTunnelInterface[{name}/HTTP{ver}/{self.mode}]"


interface_class = HTTPTunnelInterface
