# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.rnstatus_handler import (
    fmt_packet_count,
    fmt_per_second,
    fmt_percentage,
    speed_str,
)


def test_fmt_per_second_human_readable():
    assert fmt_per_second(0) == "0"
    assert fmt_per_second(0.4674843123420399) == "0.467"
    assert fmt_per_second(12.3456789) == "12.35"
    assert fmt_per_second(100.2) == "100.2"


def test_fmt_packet_count_integers():
    assert fmt_packet_count(1575.786604215814) == "1,576"
    assert fmt_packet_count(0) == "0"


def test_fmt_percentage():
    assert fmt_percentage(3.14159265) == "3.14"
    assert fmt_percentage(101.2) == "101.2"
    assert fmt_percentage(0.5) == "0.5"


def test_speed_str_bitrate_not_scaled():
    assert speed_str(100) == "100.00 bps"
    assert speed_str(5_000_000) == "5.00 Mbps"
    assert speed_str(8_000_000) == "8.00 Mbps"


def test_rnstatus_passes_i2p_and_transport_fields():
    from unittest.mock import MagicMock

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    handler = RNStatusHandler(MagicMock())
    status = handler.get_status(
        stats={
            "interfaces": [
                {
                    "name": "I2PInterface[I2P]",
                    "status": True,
                    "mode": 0,
                    "i2p_connectable": True,
                    "i2p_b32": "abc123.b32.i2p",
                    "tunnelstate": "Tunnel Active",
                    "rxb": 1000,
                    "txb": 2000,
                    "rxs": 50,
                    "txs": 75,
                },
            ],
            "rxb": 3000,
            "txb": 4000,
            "rxs": 10,
            "txs": 20,
            "transport_id": b"\xab" * 16,
            "network_id": b"\xcd" * 16,
            "transport_uptime": 90,
        },
        include_local_blackhole=False,
    )
    iface = status["interfaces"][0]
    assert iface["i2p_b32"] == "abc123.b32.i2p"
    assert iface["i2p_connectable"] is True
    assert iface["i2p_tunnel_state"] == "Tunnel Active"
    assert "rx_packets" not in iface
    assert iface["rx_speed_str"]
    assert status["transport_id"] == "ab" * 16
    assert status["network_id"] == "cd" * 16
    assert status["totals"]["rx_bytes"] == 3000
    assert status["totals"]["tx_bytes"] == 4000


def test_rnstatus_hides_client_interfaces_unless_show_all():
    from unittest.mock import MagicMock

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    handler = RNStatusHandler(MagicMock())
    stats = {
        "interfaces": [
            {"name": "TCPServerInterface[Public]", "status": True, "mode": 0},
            {"name": "TCPInterface[Client 1]", "status": True, "mode": 0},
        ],
    }
    hidden = handler.get_status(stats=stats, include_local_blackhole=False)
    names = [i["name"] for i in hidden["interfaces"]]
    assert names == ["TCPServerInterface[Public]"]
    shown = handler.get_status(
        stats=stats,
        include_local_blackhole=False,
        show_all=True,
    )
    assert [i["name"] for i in shown["interfaces"]] == [
        "TCPServerInterface[Public]",
        "TCPInterface[Client 1]",
    ]


def test_rnstatus_hides_non_connectable_i2p_unless_show_all():
    from unittest.mock import MagicMock

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    handler = RNStatusHandler(MagicMock())
    stats = {
        "interfaces": [
            {"name": "I2PInterface[Hidden]", "status": True, "mode": 0, "i2p_connectable": False},
            {"name": "I2PInterface[Public]", "status": True, "mode": 0, "i2p_connectable": True},
        ],
    }
    hidden = handler.get_status(stats=stats, include_local_blackhole=False)
    assert [i["name"] for i in hidden["interfaces"]] == ["I2PInterface[Public]"]
    shown = handler.get_status(
        stats=stats,
        include_local_blackhole=False,
        show_all=True,
    )
    assert len(shown["interfaces"]) == 2


def test_rnstatus_includes_queue_and_flow_totals():
    from unittest.mock import MagicMock

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    handler = RNStatusHandler(MagicMock())
    status = handler.get_status(
        stats={
            "interfaces": [
                {
                    "name": "RNodeInterface[Test]",
                    "status": True,
                    "mode": 0,
                    "rxb": 1000,
                    "txb": 2000,
                    "rxs": 100,
                    "txs": 200,
                    "arxc": 12,
                    "atxc": 34,
                    "prxc": 5,
                    "ptxc": 6,
                    "arxs": 10,
                    "atxs": 20,
                    "prxs": 2,
                    "ptxs": 3,
                    "protocol_violations": 1,
                    "ifac_violations": 2,
                    "packet_filter_hits": 9,
                },
            ],
            "rxb": 3000,
            "txb": 4000,
            "rxs": 100,
            "txs": 200,
            "arxb": 500,
            "atxb": 600,
            "arxs": 10,
            "atxs": 20,
            "prxb": 50,
            "ptxb": 60,
            "prxs": 2,
            "ptxs": 3,
            "rxqt": 4,
            "tqpressure": 0.25,
            "rxqtd": 1,
        },
        include_local_blackhole=False,
    )
    iface = status["interfaces"][0]
    assert iface["announce_totals"] == "↓12 ↑34"
    assert iface["path_request_totals"] == "↓5 ↑6"
    assert iface["violations"] == "1 protocol, 2 IFAC"
    assert iface["filter_hits"] == "9"
    assert iface["announce_flow_rx_pct"] == 10
    assert status["totals"]["announces"]["rx_bytes_str"]
    assert status["totals"]["path_requests"]["tx_bytes_str"]
    assert status["queues"]["queues"][0]["name"] == "total"


def test_rnstatus_mode_labels_match_rns_constants():
    from unittest.mock import MagicMock

    import RNS

    from meshchatx.src.backend.rnstatus_handler import RNStatusHandler

    iface = RNS.Interfaces.Interface.Interface
    cases = {
        iface.MODE_POINT_TO_POINT: "Point-to-Point",
        iface.MODE_ACCESS_POINT: "Access Point",
        iface.MODE_ROAMING: "Roaming",
        iface.MODE_BOUNDARY: "Boundary",
        iface.MODE_GATEWAY: "Gateway",
        iface.MODE_INTERNAL: "Internal",
    }
    handler = RNStatusHandler(MagicMock())
    for mode_value, label in cases.items():
        status = handler.get_status(
            stats={
                "interfaces": [
                    {
                        "name": "TestInterface",
                        "status": True,
                        "mode": mode_value,
                    },
                ],
            },
            include_local_blackhole=False,
        )
        assert status["interfaces"][0]["mode"] == label, mode_value
