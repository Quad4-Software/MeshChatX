"""TrafficStats meter, rate diffing, residual math, and hint computation."""

import time

from meshchatx.src.backend.traffic_stats import (
    COMPONENT_CRAWLER,
    COMPONENT_LXMF,
    COMPONENT_RRC,
    TrafficStats,
    compute_hints,
)


def _iface(
    name, txb=0, rxb=0, atxb=0, arxb=0, ptxb=0, prxb=0, itype="TCPClientInterface"
):
    return {
        "name": name,
        "short_name": name,
        "type": itype,
        "txb": txb,
        "rxb": rxb,
        "atxb": atxb,
        "arxb": arxb,
        "ptxb": ptxb,
        "prxb": prxb,
    }


def test_record_and_snapshot_components():
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=100, rx=50)
    meter.record(COMPONENT_RRC, tx=10)
    first = meter.snapshot([_iface("i0", txb=1000, rxb=800)])
    # First sample establishes the baseline: no rates yet.
    assert first["totals"]["tx_bytes"] == 1000
    assert first["totals"]["tx_bps"] == 0.0
    by_id = {c["id"]: c for c in first["components"]}
    assert by_id[COMPONENT_LXMF]["tx_bytes"] == 100
    assert by_id[COMPONENT_RRC]["tx_bytes"] == 10
    # Residual subtracts attributed component bytes.
    assert first["residual"]["tx_bytes"] == 1000 - 110


def test_rates_computed_between_snapshots():
    meter = TrafficStats()
    meter.snapshot([_iface("i0", txb=1000, rxb=1000)])
    time.sleep(0.3)
    meter.record(COMPONENT_LXMF, rx=300)
    second = meter.snapshot([_iface("i0", txb=1300, rxb=1600)])
    # ~0.3s for 300 bytes -> ~1000 B/s raw; EMA blends with the prior
    # zero sample, so the displayed rate lands well under raw.
    assert 200 < second["totals"]["rx_bps"] < 1200
    assert 200 < second["interfaces"][0]["tx_bps"] < 1200
    lxmf = {c["id"]: c for c in second["components"]}[COMPONENT_LXMF]
    assert 200 < lxmf["rx_bps"] < 1200


def test_sub_second_poll_reuses_last_payload():
    meter = TrafficStats()
    first = meter.snapshot([_iface("i0", txb=1, rxb=1)])
    second = meter.snapshot([_iface("i0", txb=9999, rxb=9999)])
    assert second is first


def test_residual_never_negative():
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=10_000)
    payload = meter.snapshot([_iface("i0", txb=5, rxb=5)])
    assert payload["residual"]["tx_bytes"] == 0
    # rx was never attributed, so the whole 5 bytes remain residual.
    assert payload["residual"]["rx_bytes"] == 5


def test_history_ring_grows():
    meter = TrafficStats()
    for _ in range(3):
        meter.snapshot([_iface("i0")])
        time.sleep(0.26)
    assert len(meter.snapshot([_iface("i0")])["history"]) >= 3


class _Cfg:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _BoolCfg:
    """Mimic config_manager.BoolConfig - wraps a value, read via get()."""

    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _Ctx:
    def __init__(self, config=None, rrc_manager=None):
        self.config = config
        self.rrc_manager = rrc_manager


class _App:
    def __init__(self, ctx):
        self.current_context = ctx


def test_hints_idle_when_quiet():
    payload = {
        "totals": {"tx_bps": 0.0, "rx_bps": 0.0},
        "residual": {"tx_bps": 0.0, "rx_bps": 0.0},
        "components": [],
        "interfaces": [],
    }
    hints = compute_hints(payload, _App(_Ctx()))
    assert [h["id"] for h in hints] == ["idle"]


def test_hints_transport_mode_dominates():
    payload = {
        "totals": {"tx_bps": 4000.0, "rx_bps": 3000.0},
        "residual": {"tx_bps": 3900.0, "rx_bps": 2900.0},
        "components": [],
        "interfaces": [_iface("i0")],
    }

    class _Rns:
        def transport_enabled(self):
            return True

    app = _App(_Ctx())
    app.reticulum = _Rns()
    hints = compute_hints(payload, app)
    assert "transport_mode" in [h["id"] for h in hints]


def test_hints_announce_and_rrc_and_crawler():
    meter = TrafficStats()
    meter.record(COMPONENT_RRC, tx=100)
    meter.record(COMPONENT_CRAWLER, rx=500)
    payload = {
        "totals": {"tx_bps": 500.0, "rx_bps": 500.0},
        "residual": {"tx_bps": 100.0, "rx_bps": 100.0},
        "components": [
            {"id": COMPONENT_RRC, "tx_bytes": 100, "rx_bytes": 0},
            {
                "id": COMPONENT_CRAWLER,
                "tx_bytes": 0,
                "rx_bytes": 500,
                "rx_bps": 12.0,
            },
        ],
        "interfaces": [
            {
                **_iface("auto", itype="AutoInterface"),
                "announce_tx_bps": 4.0,
                "announce_rx_bps": 2.0,
            },
        ],
    }
    from meshchatx.src.backend.rrc.manager import RRCHub

    hints = compute_hints(
        payload,
        _App(
            _Ctx(
                config=_Cfg(crawler_enabled=_BoolCfg(True)),
                rrc_manager=type(
                    "M",
                    (),
                    {
                        "hubs": [
                            type("H", (), {"status": RRCHub.STATUS_CONNECTED})(),
                            type("H", (), {"status": RRCHub.STATUS_CONNECTED})(),
                            type("H", (), {"status": RRCHub.STATUS_DISCONNECTED})(),
                        ],
                    },
                )(),
            )
        ),
    )
    ids = [h["id"] for h in hints]
    assert "announce_discovery" in ids
    assert "rrc_hubs" in ids
    assert "crawler" in ids
    hubs_hint = next(h for h in hints if h["id"] == "rrc_hubs")
    assert hubs_hint["params"]["hubs"] == 2


def test_hints_propagation_inbound_only():
    iface = _iface("i0")
    iface["propagated_rx_bps"] = 3.0
    payload = {
        "totals": {"tx_bps": 100.0, "rx_bps": 300.0},
        "residual": {"tx_bps": 100.0, "rx_bps": 300.0},
        "components": [],
        "interfaces": [iface],
    }
    hints = compute_hints(payload, _App(_Ctx(config=_Cfg())))
    # propagated counters moved but local propagation node is off
    assert "propagation_node_inbound" in [h["id"] for h in hints]


def test_hints_crawler_states():
    """Enabled-but-idle, actively fetching, and observed-while-disabled."""
    base = {
        "totals": {"tx_bps": 100.0, "rx_bps": 100.0},
        "residual": {"tx_bps": 100.0, "rx_bps": 100.0},
        "components": [],
        "interfaces": [],
    }
    app_on = _App(_Ctx(config=_Cfg(crawler_enabled=_BoolCfg(True))))
    app_off = _App(_Ctx(config=_Cfg(crawler_enabled=_BoolCfg(False))))

    # enabled, no traffic -> enabled-idle, not "active"
    hints = compute_hints(base, app_on)
    assert [h["id"] for h in hints] == ["crawler_enabled"]

    # enabled + moving -> active
    active = dict(base)
    active["components"] = [
        {"id": COMPONENT_CRAWLER, "tx_bytes": 10, "rx_bytes": 500, "rx_bps": 5.0}
    ]
    hints = compute_hints(active, app_on)
    assert [h["id"] for h in hints] == ["crawler"]

    # disabled + bytes -> observed (queued task finishing)
    hints = compute_hints(active, app_off)
    assert [h["id"] for h in hints] == ["crawler_observed"]

    # disabled + nothing -> no hint
    hints = compute_hints(base, app_off)
    assert not hints


def test_hints_propagation_states():
    base = {
        "totals": {"tx_bps": 100.0, "rx_bps": 100.0},
        "residual": {"tx_bps": 100.0, "rx_bps": 100.0},
        "components": [],
        "interfaces": [],
    }
    on = _App(_Ctx(config=_Cfg(lxmf_local_propagation_node_enabled=_BoolCfg(True))))
    off = _App(_Ctx(config=_Cfg(lxmf_local_propagation_node_enabled=_BoolCfg(False))))

    idle = dict(base, interfaces=[dict(_iface("i0"), propagated_rx_bps=0.0)])
    assert [h["id"] for h in compute_hints(idle, on)] == ["propagation_node_enabled"]
    assert compute_hints(idle, off) == []

    serving = dict(base, interfaces=[dict(_iface("i0"), propagated_rx_bps=3.0)])
    assert [h["id"] for h in compute_hints(serving, on)] == ["propagation_node_serving"]
    assert [h["id"] for h in compute_hints(serving, off)] == [
        "propagation_node_inbound"
    ]


def test_peer_attribution():
    """record() with peer= rolls bytes into a per-peer bucket."""
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=100, rx=50, peer="ab" * 16)
    meter.record(COMPONENT_RRC, tx=40, peer="ab" * 16)
    meter.record(COMPONENT_RRC, rx=20, peer="cd" * 16)
    payload = meter.snapshot([_iface("i0", txb=500, rxb=500)])
    peers = {p["hash"]: p for p in payload["peers"]}
    ab = peers["ab" * 16]
    assert ab["tx_bytes"] == 140
    assert ab["rx_bytes"] == 50
    assert ab["components"]["lxmf"] == {"tx": 100, "rx": 50}
    assert ab["components"]["rrc"] == {"tx": 40, "rx": 0}
    assert peers["cd" * 16]["rx_bytes"] == 20
    # peers sort by total bytes desc
    assert payload["peers"][0]["hash"] == "ab" * 16


def test_peer_rates_smoothed():
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=300, peer="ef" * 16)
    meter.snapshot([_iface("i0", txb=0, rxb=0)])
    time.sleep(0.3)
    meter.record(COMPONENT_LXMF, tx=300, peer="ef" * 16)
    payload = meter.snapshot([_iface("i0", txb=300, rxb=0)])
    peer = payload["peers"][0]
    assert peer["tx_bytes"] == 600
    assert 0 < peer["tx_bps"] < 2000
