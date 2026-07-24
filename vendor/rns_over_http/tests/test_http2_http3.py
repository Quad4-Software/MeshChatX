"""HTTP/2 and HTTP/3 tunnel tests over TLS."""

from __future__ import annotations

import io
import socket
import time

import httpx
import pytest
from RNS.vendor.configobj import ConfigObj

import HTTPInterface as http_mod
from HTTPInterface import HDLC, HTTPTunnelInterface
from tests.tls_certs import write_self_signed_cert


def free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_tcp_open(host, port, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.05)
    pytest.fail(f"port {host}:{port} did not open within {timeout}s")


def wait_udp_bound(host, port, timeout=15.0):
    """Best-effort wait until something is listening on UDP port."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # Hypercorn QUIC bind is harder to probe; give the ASGI thread time.
        time.sleep(0.1)
        # Also accept TCP (Hypercorn binds TCP even for HTTP/3 mode).
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            continue
    pytest.fail(f"HTTP/3 server did not become ready on {host}:{port}")


def configobj_from_lines(lines):
    return ConfigObj(io.StringIO("\n".join(lines) + "\n"))


class RecordingOwner:
    def __init__(self):
        self.packets = []

    def inbound(self, data, iface):
        self.packets.append(bytes(data))

    def last_payload(self, timeout=10.0, poll=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.packets:
                return self.packets[-1]
            time.sleep(poll)
        return None

    def wait_count(self, n, timeout=15.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(self.packets) >= n:
                return list(self.packets)
            time.sleep(0.05)
        return None


def make_tls_pair(tmp_path, free_port, http_version, poll_interval=0.05):
    cert, key = write_self_signed_cert(tmp_path / f"certs-h{http_version}")
    owner_s = RecordingOwner()
    owner_c = RecordingOwner()
    server = HTTPTunnelInterface(
        owner_s,
        configobj_from_lines(
            [
                "name = srv",
                "mode = server",
                "listen_host = 127.0.0.1",
                f"listen_port = {free_port}",
                f"http_version = {http_version}",
                f"tls_certfile = {cert}",
                f"tls_keyfile = {key}",
                f"poll_interval = {poll_interval}",
            ]
        ),
    )
    if http_version == 3:
        wait_udp_bound("127.0.0.1", free_port)
    else:
        wait_tcp_open("127.0.0.1", free_port)

    # Extra settle time for Hypercorn TLS/QUIC startup
    time.sleep(0.3)

    url = f"https://127.0.0.1:{free_port}/"
    client = HTTPTunnelInterface(
        owner_c,
        configobj_from_lines(
            [
                "name = cli",
                "mode = client",
                f"server_url = {url}",
                f"http_version = {http_version}",
                "tls_verify = false",
                f"poll_interval = {poll_interval}",
            ]
        ),
    )
    return owner_s, owner_c, server, client


@pytest.fixture
def free_port():
    return free_tcp_port()


def test_http2_requires_tls_on_server(free_port):
    with pytest.raises(ValueError, match="tls_certfile"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = srv",
                    "mode = server",
                    "listen_host = 127.0.0.1",
                    f"listen_port = {free_port}",
                    "http_version = 2",
                ]
            ),
        )


def test_http3_client_requires_https_url():
    with pytest.raises(ValueError, match="https://"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = cli",
                    "mode = client",
                    "server_url = http://127.0.0.1:9/",
                    "http_version = 3",
                ]
            ),
        )


def test_invalid_http_version_rejected(free_port):
    with pytest.raises(ValueError, match="http_version"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = srv",
                    "mode = server",
                    "listen_host = 127.0.0.1",
                    f"listen_port = {free_port}",
                    "http_version = 4",
                ]
            ),
        )


def test_http2_bidirectional_tunnel(tmp_path, free_port):
    owner_s, owner_c, server, client = make_tls_pair(tmp_path, free_port, 2)
    try:
        client.process_outgoing(b"h2-client")
        assert owner_s.last_payload(timeout=15.0) == b"h2-client"

        server.process_outgoing(b"h2-server")
        assert owner_c.last_payload(timeout=15.0) == b"h2-server"

        # Confirm httpx negotiated HTTP/2
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if client.connection_stats().get("last_http_version") == "HTTP/2":
                break
            time.sleep(0.05)
        assert client.connection_stats()["last_http_version"] == "HTTP/2"
        assert server.connection_stats()["http_requests"] >= 1
    finally:
        client.detach()
        server.detach()


def test_http2_reuses_connection_across_polls(tmp_path, free_port):
    owner_s, owner_c, server, client = make_tls_pair(tmp_path, free_port, 2)
    try:
        for i in range(6):
            client.process_outgoing(f"h2p-{i}".encode())
        payloads = owner_s.wait_count(6, timeout=20.0)
        assert payloads is not None
        assert payloads[-6:] == [f"h2p-{i}".encode() for i in range(6)]
        stats = client.connection_stats()
        # Packets may be batched into fewer HTTP exchanges on one h2 connection
        assert stats["client_requests"] >= 1
        assert stats["client_requests"] <= 6
        assert stats["last_http_version"] == "HTTP/2"
    finally:
        client.detach()
        server.detach()


def test_http2_external_client_sees_h2(tmp_path, free_port):
    cert, key = write_self_signed_cert(tmp_path / "certs-ext")
    server = HTTPTunnelInterface(
        RecordingOwner(),
        configobj_from_lines(
            [
                "name = srv",
                "mode = server",
                "listen_host = 127.0.0.1",
                f"listen_port = {free_port}",
                "http_version = 2",
                f"tls_certfile = {cert}",
                f"tls_keyfile = {key}",
            ]
        ),
    )
    try:
        wait_tcp_open("127.0.0.1", free_port)
        time.sleep(0.3)
        with httpx.Client(http2=True, verify=False, timeout=5.0) as c:
            r = c.post(
                f"https://127.0.0.1:{free_port}/",
                content=HDLC.frame(b"ext-h2"),
                headers={"User-Agent": HTTPTunnelInterface.TUNNEL_USER_AGENT},
            )
        assert r.status_code == 200
        assert r.http_version == "HTTP/2"
    finally:
        server.detach()


def test_http3_bidirectional_tunnel(tmp_path, free_port):
    owner_s, owner_c, server, client = make_tls_pair(tmp_path, free_port, 3)
    try:
        client.process_outgoing(b"h3-client")
        assert owner_s.last_payload(timeout=20.0) == b"h3-client"

        server.process_outgoing(b"h3-server")
        assert owner_c.last_payload(timeout=20.0) == b"h3-server"

        assert client.connection_stats()["last_http_version"] == "HTTP/3"
        assert client.connection_stats()["client_requests"] >= 1
        assert server.connection_stats()["http_requests"] >= 1
    finally:
        client.detach()
        server.detach()


def test_http3_persistent_session_multiple_posts(tmp_path, free_port):
    owner_s, owner_c, server, client = make_tls_pair(tmp_path, free_port, 3)
    try:
        for i in range(5):
            client.process_outgoing(f"h3p-{i}".encode())
        payloads = owner_s.wait_count(5, timeout=25.0)
        assert payloads is not None
        assert payloads[-5:] == [f"h3p-{i}".encode() for i in range(5)]
        stats = client.connection_stats()
        assert stats["pool_num_connections"] == 1
        assert stats["pool_num_requests"] >= 1
        assert stats["pool_num_requests"] <= 5
        assert stats["last_http_version"] == "HTTP/3"
    finally:
        client.detach()
        server.detach()


def test_module_still_exports_interface_class():
    assert http_mod.interface_class is HTTPTunnelInterface
