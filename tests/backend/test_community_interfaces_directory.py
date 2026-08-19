# SPDX-License-Identifier: 0BSD

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.community_interfaces_directory import (
    DEFAULT_DIRECTORY_URL,
    rows_from_payload,
    transform_directory_rows,
    validate_directory_fetch_url,
)


def test_rows_from_payload_dict_data():
    rows = rows_from_payload({"data": [{"id": 1}]})
    assert rows == [{"id": 1}]


def test_rows_from_payload_list():
    rows = rows_from_payload([{"id": 2}])
    assert rows == [{"id": 2}]


def test_rows_from_payload_interfaces_key():
    rows = rows_from_payload({"interfaces": [{"id": 3}]})
    assert rows == [{"id": 3}]


def test_rows_from_payload_invalid():
    with pytest.raises(ValueError, match="Expected list"):
        rows_from_payload({"foo": 1})


def test_validate_directory_fetch_url_accepts_mcx():
    url = DEFAULT_DIRECTORY_URL
    assert validate_directory_fetch_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://meshchatx.com/api/mcx-interfaces",
        "https://directory.rns.recipes/api/directory/submitted?status=online",
        "https://user:pass@meshchatx.com/api/mcx-interfaces",
        "https://meshchatx.com.evil.example/api/mcx-interfaces",
        "https://127.0.0.1:9337@meshchatx.com/api/mcx-interfaces",
        "https://evil.example/https://meshchatx.com/api/mcx-interfaces",
        "",
    ],
)
def test_validate_directory_fetch_url_rejects(url):
    with pytest.raises(ValueError):
        validate_directory_fetch_url(url)


def test_transform_mcx_interfaces_payload():
    payload = {
        "source": "https://directory.rns.recipes/",
        "interfaces": [
            {
                "id": 74,
                "name": "Catz Node TCP",
                "type": "tcp",
                "typeName": "TCPClientInterface",
                "host": "77.37.146.243",
                "port": 4242,
                "status": "online",
                "config": "",
            },
            {
                "id": 48,
                "name": "Casbah I2P Relay",
                "type": "i2p",
                "typeName": "I2PInterface",
                "host": "nckymqd5qchedbvjqsrlovgwc5iupasu3jjnt7fwws5vd4l552yq.b32.i2p",
                "port": None,
                "config": "",
            },
        ],
    }
    out = transform_directory_rows(rows_from_payload(payload))
    by_name = {item["name"]: item for item in out}
    assert by_name["Catz Node TCP"]["type"] == "TCPClientInterface"
    assert by_name["Catz Node TCP"]["target_host"] == "77.37.146.243"
    assert by_name["Catz Node TCP"]["target_port"] == 4242
    assert by_name["Casbah I2P Relay"]["type"] == "I2PInterface"
    assert by_name["Casbah I2P Relay"]["i2p_peers"] == [
        "nckymqd5qchedbvjqsrlovgwc5iupasu3jjnt7fwws5vd4l552yq.b32.i2p",
    ]


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
