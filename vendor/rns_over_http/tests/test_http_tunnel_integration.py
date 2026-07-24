import io
import socket
import threading
import time

import httpx
import pytest
from RNS.vendor.configobj import ConfigObj

import HTTPInterface as http_mod
from HTTPInterface import HDLC

HTTPTunnelInterface = http_mod.HTTPTunnelInterface


def free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_tcp_open(host, port, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return
        except OSError:
            time.sleep(0.05)
    pytest.fail(f"port {host}:{port} did not open within {timeout}s")


def configobj_from_lines(lines):
    return ConfigObj(io.StringIO("\n".join(lines) + "\n"))


def ping_client_to_server(owner_s, client, token=b"\xfe\xd2tunnel-pingpytest"):
    client.process_outgoing(token)
    assert owner_s.last_payload(timeout=10.0) == token


@pytest.fixture
def free_port():
    return free_tcp_port()


class RecordingOwner:
    def __init__(self):
        self._lock = threading.Lock()
        self.packets = []

    def inbound(self, data, iface):
        with self._lock:
            self.packets.append((bytes(data), iface))

    def last_payload(self, timeout=6.0, poll=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self.packets:
                    return self.packets[-1][0]
            time.sleep(poll)
        return None

    def payloads(self):
        with self._lock:
            return [bytes(p) for p, _ in self.packets]

    def packet_count(self):
        with self._lock:
            return len(self.packets)

    def wait_packet_count_at_least(self, n, timeout=8.0, poll=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if len(self.packets) >= n:
                    return [bytes(p) for p, _ in self.packets]
            time.sleep(poll)
        return None


def make_pair(free_port, poll_interval=0.05, **extra_server):
    owner_s = RecordingOwner()
    owner_c = RecordingOwner()
    srv_lines = [
        "name = srv",
        "mode = server",
        "listen_host = 127.0.0.1",
        f"listen_port = {free_port}",
        f"poll_interval = {poll_interval}",
    ]
    for k, v in extra_server.items():
        srv_lines.append(f"{k} = {v}")
    server = HTTPTunnelInterface(owner_s, configobj_from_lines(srv_lines))
    wait_tcp_open("127.0.0.1", free_port)
    url = f"http://127.0.0.1:{free_port}/"
    client = HTTPTunnelInterface(
        owner_c,
        configobj_from_lines(
            [
                "name = cli",
                "mode = client",
                f"server_url = {url}",
                f"poll_interval = {poll_interval}",
            ]
        ),
    )
    return owner_s, owner_c, server, client


def test_client_mode_requires_server_url():
    with pytest.raises(ValueError, match="server_url"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = c",
                    "mode = client",
                ]
            ),
        )


def test_invalid_tunnel_mode():
    with pytest.raises(ValueError, match="Invalid mode"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = x",
                    "mode = bridge",
                    "listen_host = 127.0.0.1",
                    "listen_port = 9",
                ]
            ),
        )


def test_process_outgoing_rejects_over_mtu(free_port):
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
            "mtu = 32",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        payload = b"x" * 64
        iface.process_outgoing(payload)
        assert iface._send_queue.empty()
    finally:
        iface.detach()


def test_client_payload_reaches_server_owner(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        payload = b"rnstest-bytes-1"
        client.process_outgoing(payload)
        got = owner_s.last_payload(timeout=8.0)
        assert got == payload
    finally:
        client.detach()
        server.detach()


def test_server_payload_reaches_client_owner(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        ping_client_to_server(owner_s, client)
        reply = b"rnstest-reply-2"
        server.process_outgoing(reply)
        got = owner_c.last_payload(timeout=8.0)
        assert got == reply
    finally:
        client.detach()
        server.detach()


def test_server_rejects_wrong_user_agent(free_port):
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
            "check_user_agent = true",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        r = httpx.post(
            f"http://127.0.0.1:{free_port}/",
            content=HDLC.frame(b"probe"),
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        assert r.status_code == 403
        time.sleep(0.2)
        assert owner.packets == []
    finally:
        iface.detach()


def test_client_default_mode_requires_server_url_when_mode_omitted():
    with pytest.raises(ValueError, match="server_url"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = c",
                ]
            ),
        )


def test_tunnel_mode_case_insensitive_SERVER(free_port):
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = SERVER",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
        ]
    )
    iface = HTTPTunnelInterface(RecordingOwner(), cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        assert iface.mode == "server"
    finally:
        iface.detach()


def test_process_outgoing_exact_mtu_accepted(free_port):
    owner = RecordingOwner()
    mtu = 80
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
            f"mtu = {mtu}",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        payload = b"p" * mtu
        tx_before = iface.txb
        iface.process_outgoing(payload)
        assert not iface._send_queue.empty()
        assert iface._send_queue.get_nowait() == payload
        assert iface.txb == tx_before + mtu
    finally:
        iface.detach()


def test_process_outgoing_when_offline_does_not_queue(free_port):
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
        ]
    )
    iface = HTTPTunnelInterface(RecordingOwner(), cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        iface.detach()
        iface.process_outgoing(b"ignored")
        assert iface._send_queue.empty()
        assert iface.txb == 0
        assert iface.online is False
    finally:
        if iface.online:
            iface.detach()


def test_process_incoming_empty_not_forwarded(free_port):
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        prev = iface.rxb
        iface.process_incoming(b"")
        iface.process_incoming(b"")
        assert iface.rxb == prev
        assert owner.packets == []
    finally:
        iface.detach()


def test_server_queued_packets_arrive_as_separate_frames(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        ping_client_to_server(owner_s, client)
        server.process_outgoing(b"A")
        server.process_outgoing(b"B")
        payloads = owner_c.wait_packet_count_at_least(2, timeout=10.0)
        assert payloads is not None
        assert payloads == [b"A", b"B"]
    finally:
        client.detach()
        server.detach()


def test_sequential_client_out_two_server_packets(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        ping_client_to_server(owner_s, client)
        client.process_outgoing(b"\x01first")
        client.process_outgoing(b"\x02second")
        payloads = owner_s.wait_packet_count_at_least(3, timeout=15.0)
        assert payloads is not None
        assert payloads[-2:] == [b"\x01first", b"\x02second"]
    finally:
        client.detach()
        server.detach()


def test_check_user_agent_false_accepts_foreign_ua(free_port):
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
            "check_user_agent = false",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        r = httpx.post(
            f"http://127.0.0.1:{free_port}/",
            content=HDLC.frame(b"foreign"),
            headers={"User-Agent": "ForeignAgent/9"},
            timeout=5,
        )
        assert r.status_code == 200
        assert owner.last_payload(timeout=6.0) == b"foreign"
    finally:
        iface.detach()


def test_wrong_post_path_404_never_queues(free_port):
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        r = httpx.post(
            f"http://127.0.0.1:{free_port}/bogus",
            content=HDLC.frame(b"x"),
            headers={"User-Agent": HTTPTunnelInterface.TUNNEL_USER_AGENT},
            timeout=5,
        )
        assert r.status_code == 404
        time.sleep(0.25)
        assert owner.packets == []
    finally:
        iface.detach()


def test_serve_html_on_get_when_configured(tmp_path, free_port):
    html_path = tmp_path / "stub.html"
    html_path.write_text("<title>t</title><p>h</p>", encoding="utf-8")
    owner = RecordingOwner()
    cfg = configobj_from_lines(
        [
            "name = srv",
            "mode = server",
            "listen_host = 127.0.0.1",
            f"listen_port = {free_port}",
            "serve_html_page = true",
            f"html_file_path = {html_path}",
        ]
    )
    iface = HTTPTunnelInterface(owner, cfg)
    try:
        wait_tcp_open("127.0.0.1", free_port)
        r = httpx.get(f"http://127.0.0.1:{free_port}/", timeout=5)
        assert r.status_code == 200
        assert b"<title>t</title>" in r.content
    finally:
        iface.detach()


def test_client_requests_use_configured_user_agent(free_port):
    custom_ua = "CustomTunnelAgent/2.0"
    owner_s, owner_c, server, client = make_pair(
        free_port,
        user_agent=custom_ua,
    )
    # rebuild client with matching UA
    client.detach()
    url = f"http://127.0.0.1:{free_port}/"
    client = HTTPTunnelInterface(
        owner_c,
        configobj_from_lines(
            [
                "name = cli",
                "mode = client",
                f"server_url = {url}",
                "poll_interval = 0.05",
                f"user_agent = {custom_ua}",
            ]
        ),
    )
    try:
        ua = client.session.headers["User-Agent"]
        assert ua == custom_ua
        client.process_outgoing(b"ua-ok")
        assert owner_s.last_payload(timeout=8.0) == b"ua-ok"
    finally:
        client.detach()
        server.detach()


def test_counters_after_tunnel_roundtrip_stay_consistent(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        p = b"dcounter-test"
        client.process_outgoing(p)
        assert owner_s.last_payload(timeout=8.0) == p
        assert client.txb >= len(p)
        assert server.rxb >= len(p)

        reply = b"back-at-you"
        time.sleep(0.05)
        server.process_outgoing(reply)
        assert owner_c.last_payload(timeout=8.0) == reply
        assert server.txb >= len(reply)
        assert client.rxb >= len(reply)
    finally:
        client.detach()
        server.detach()


def test_subclass_matches_rns_interface():
    from RNS.Interfaces.Interface import Interface

    assert issubclass(HTTPTunnelInterface, Interface)
    assert http_mod.interface_class is HTTPTunnelInterface


def test_payloads_with_flag_and_esc_bytes_survive_roundtrip(free_port):
    owner_s, owner_c, server, client = make_pair(free_port)
    try:
        payload = bytes([HDLC.FLAG, 0x00, HDLC.ESC, 0xFF, HDLC.FLAG, HDLC.ESC])
        client.process_outgoing(payload)
        assert owner_s.last_payload(timeout=8.0) == payload
    finally:
        client.detach()
        server.detach()


def test_client_reuses_single_pooled_tcp_connection(free_port):
    owner_s, owner_c, server, client = make_pair(free_port, poll_interval=0.05)
    try:
        expected = []
        for i in range(8):
            payload = f"pool-{i}".encode()
            expected.append(payload)
            client.process_outgoing(payload)

        payloads = owner_s.wait_packet_count_at_least(8, timeout=15.0)
        assert payloads is not None
        assert payloads[-8:] == expected

        deadline = time.monotonic() + 5.0
        stats = {}
        while time.monotonic() < deadline:
            stats = server.connection_stats()
            if stats.get("http_requests", 0) >= 8 and stats.get("tcp_accepts", 0) >= 1:
                break
            time.sleep(0.05)

        assert stats["http_requests"] >= 8
        # wait_tcp_open probes once, then the client should reuse a single TCP session
        assert stats["tcp_accepts"] <= 2
        assert stats["http_requests"] > stats["tcp_accepts"]

        cstats = client.connection_stats()
        assert cstats.get("client_requests", 0) >= 8
        assert cstats.get("last_http_version") == "HTTP/1.1"
        assert client.http_version == 1
    finally:
        client.detach()
        server.detach()


def test_server_advertises_http11_keepalive_headers(free_port):
    owner_s, owner_c, server, client = make_pair(
        free_port,
        poll_interval=0.05,
        keepalive_timeout=45,
    )
    try:
        ping_client_to_server(owner_s, client)
        r = httpx.post(
            f"http://127.0.0.1:{free_port}/",
            content=HDLC.frame(b"hdr"),
            headers={
                "User-Agent": HTTPTunnelInterface.TUNNEL_USER_AGENT,
                "Connection": "keep-alive",
            },
            timeout=5,
        )
        assert r.status_code == 200
        assert r.headers.get("Connection", "").lower() == "keep-alive"
        assert "timeout=45" in r.headers.get("Keep-Alive", "")
    finally:
        client.detach()
        server.detach()


def test_invalid_pool_size_rejected():
    with pytest.raises(ValueError, match="pool_connections"):
        HTTPTunnelInterface(
            RecordingOwner(),
            configobj_from_lines(
                [
                    "name = c",
                    "mode = client",
                    "server_url = http://127.0.0.1:9/",
                    "pool_maxsize = 0",
                ]
            ),
        )
