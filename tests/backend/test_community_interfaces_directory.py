# SPDX-License-Identifier: 0BSD

import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.community_interfaces_directory import (
    DEFAULT_SUBMITTED_URL,
    fetch_directory_payload,
    rows_from_payload,
    transform_directory_rows,
    validate_directory_fetch_url,
)


def test_default_url_is_submitted_online():
    assert "submitted" in DEFAULT_SUBMITTED_URL
    assert "status=online" in DEFAULT_SUBMITTED_URL


def test_validate_directory_fetch_url_accepts_default_host():
    u = "https://directory.rns.recipes/api/foo?bar=1"
    assert validate_directory_fetch_url(u) == u


@pytest.mark.parametrize(
    "bad",
    [
        "http://directory.rns.recipes/api",
        "https://127.0.0.1/",
        "https://metadata.internal/",
        "ftp://directory.rns.recipes/",
        "https://evil.com/https://directory.rns.recipes/",
        "https://user:pass@directory.rns.recipes/",
        "https://not-directory.rns.recipes.example/api",
    ],
)
def test_validate_directory_fetch_url_rejects_ssrf(bad):
    with pytest.raises(ValueError):
        validate_directory_fetch_url(bad)


class _Redirect302Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "http://127.0.0.1:9/")
        self.end_headers()

    def log_message(self, *args):
        return


class _Json200Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"data":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@pytest.fixture
def redirect_http_port():
    srv = HTTPServer(("127.0.0.1", 0), _Redirect302Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    port = srv.server_address[1]
    yield port
    srv.shutdown()


@pytest.fixture
def json_http_port():
    srv = HTTPServer(("127.0.0.1", 0), _Json200Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    port = srv.server_address[1]
    yield port
    srv.shutdown()


def test_directory_fetch_opener_blocks_http_redirect(redirect_http_port):
    from meshchatx.src.backend.community_interfaces_directory import (
        _DIRECTORY_FETCH_OPENER,
    )

    req = urllib.request.Request(f"http://127.0.0.1:{redirect_http_port}/")
    with pytest.raises(urllib.error.HTTPError) as ei:
        _DIRECTORY_FETCH_OPENER.open(req, timeout=3)
    assert ei.value.code == 302


def test_fetch_directory_payload_reads_json_when_no_redirect(
    monkeypatch,
    json_http_port,
):
    import meshchatx.src.backend.community_interfaces_directory as cid

    monkeypatch.setattr(
        cid,
        "validate_directory_fetch_url",
        lambda url: url,
    )
    out = fetch_directory_payload(
        f"http://127.0.0.1:{json_http_port}/x",
        timeout=3,
    )
    assert out == {"data": []}


def test_fetch_directory_payload_raises_on_redirect(monkeypatch, redirect_http_port):
    import meshchatx.src.backend.community_interfaces_directory as cid

    monkeypatch.setattr(
        cid,
        "validate_directory_fetch_url",
        lambda url: url,
    )
    with pytest.raises(urllib.error.HTTPError) as ei:
        fetch_directory_payload(
            f"http://127.0.0.1:{redirect_http_port}/",
            timeout=3,
        )
    assert ei.value.code == 302


def test_rows_from_payload_dict_data():
    rows = rows_from_payload({"data": [{"id": 1}]})
    assert rows == [{"id": 1}]


def test_rows_from_payload_list():
    rows = rows_from_payload([{"id": 2}])
    assert rows == [{"id": 2}]


def test_rows_from_payload_invalid():
    with pytest.raises(ValueError, match="Expected list"):
        rows_from_payload({"foo": 1})


def test_transform_submitted_backbone_without_identity_becomes_tcp():
    rows = [
        {
            "id": 39,
            "name": "CRN IPv4",
            "type": "backbone",
            "typeName": "BackboneInterface",
            "network": "clearnet",
            "host": "rns.example.org",
            "port": 4242,
            "status": "online",
            "config": "",
        },
    ]
    out = transform_directory_rows(rows)
    assert len(out) == 1
    assert out[0]["type"] == "TCPClientInterface"
    assert out[0]["target_host"] == "rns.example.org"
    assert out[0]["target_port"] == 4242


def test_transform_submitted_tcp_client():
    rows = [
        {
            "id": 51,
            "name": "Ether Whisperer",
            "type": "tcp",
            "typeName": "TCPClientInterface",
            "host": "132.145.75.143",
            "port": 4242,
            "status": "online",
            "config": "",
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["type"] == "TCPClientInterface"
    assert out[0]["target_host"] == "132.145.75.143"


def test_transform_backbone_with_transport_id():
    rows = [
        {
            "id": 1,
            "name": "BB",
            "type": "backbone",
            "typeName": "BackboneInterface",
            "host": "a.example",
            "port": 4242,
            "transportId": "e53433e51cde34c42a3245ba3fe1ad69",
            "config": "",
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["type"] == "BackboneInterface"
    assert out[0]["transport_identity"] == "e53433e51cde34c42a3245ba3fe1ad69"


def test_transform_transport_identity_from_config():
    cfg = "[[x]]\ntype = BackboneInterface\ntransport_identity = abcd0123ef\nremote = h.example\ntarget_port = 1"
    rows = [
        {
            "id": 2,
            "name": "X",
            "type": "backbone",
            "typeName": "BackboneInterface",
            "host": "",
            "port": 4242,
            "config": cfg,
        },
    ]
    out = transform_directory_rows(rows)
    assert len(out) == 1
    assert out[0]["type"] == "BackboneInterface"
    assert out[0]["transport_identity"] == "abcd0123ef"
    assert out[0]["remote"] == "h.example"


def test_transform_host_from_config_remote():
    cfg = "remote = cfg-host.example\ntarget_port = 4242"
    rows = [
        {
            "id": 3,
            "name": "Y",
            "type": "tcp",
            "typeName": "TCPClientInterface",
            "host": "",
            "port": 4242,
            "config": cfg,
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["target_host"] == "cfg-host.example"


def test_transform_i2p_uses_host():
    rows = [
        {
            "id": 48,
            "name": "Casbah",
            "type": "i2p",
            "typeName": "I2PInterface",
            "host": "aaa.b32.i2p",
            "port": None,
            "config": "",
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["type"] == "I2PInterface"
    assert out[0]["i2p_peers"] == ["aaa.b32.i2p"]


def test_transform_i2p_peer_from_config_only():
    cfg = "peers = bbb.b32.i2p"
    rows = [
        {
            "id": 49,
            "name": "Relay",
            "type": "i2p",
            "typeName": "I2PInterface",
            "host": "",
            "port": None,
            "config": cfg,
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["i2p_peers"] == ["bbb.b32.i2p"]


def test_transform_skips_rnode():
    rows = [{"id": 1, "type": "rnode", "host": "x", "port": 1}]
    assert transform_directory_rows(rows) == []


def test_transform_tcp_row_with_numeric_id():
    rows = [
        {
            "id": 207,
            "name": "Public TCP",
            "type": "tcp",
            "typeName": "TCPClientInterface",
            "host": "10.0.0.1",
            "port": 4242,
        },
    ]
    out = transform_directory_rows(rows)
    assert len(out) == 1
    assert out[0]["type"] == "TCPClientInterface"
    assert out[0]["target_host"] == "10.0.0.1"


def test_transform_tcp_with_backbone_in_config_and_identity():
    rows = [
        {
            "id": 10,
            "name": "Hybrid",
            "type": "tcp",
            "typeName": "TCPClientInterface",
            "host": "10.0.0.1",
            "port": 4242,
            "transportId": "a" * 32,
            "config": "BackboneInterface",
        },
    ]
    out = transform_directory_rows(rows)
    assert out[0]["type"] == "BackboneInterface"


@settings(max_examples=80)
@given(
    st.lists(
        st.fixed_dictionaries(
            {
                "id": st.one_of(
                    st.none(),
                    st.integers(min_value=-1000, max_value=10000),
                ),
                "name": st.text(max_size=40),
                "type": st.sampled_from(["backbone", "tcp", "i2p", "rnode", ""]),
                "typeName": st.sampled_from(
                    ["BackboneInterface", "TCPClientInterface", "I2PInterface", ""],
                ),
                "host": st.one_of(st.none(), st.text(max_size=30)),
                "address": st.one_of(st.none(), st.text(max_size=20)),
                "port": st.one_of(
                    st.none(),
                    st.integers(min_value=0, max_value=65535),
                    st.text(max_size=8),
                ),
                "transportId": st.one_of(
                    st.none(),
                    st.text(alphabet="0123456789abcdef", min_size=0, max_size=32),
                ),
                "config": st.one_of(st.none(), st.text(max_size=120)),
            },
        ),
        max_size=20,
    ),
)
def test_transform_directory_rows_fuzz(rows):
    out = transform_directory_rows(rows)
    assert isinstance(out, list)
    for item in out:
        assert isinstance(item, dict)
        assert "type" in item
        assert item["type"] in (
            "BackboneInterface",
            "TCPClientInterface",
            "I2PInterface",
        )
