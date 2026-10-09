"""TrafficStats meter, rate diffing, residual math, and hint computation."""

import logging
import threading
import time

from meshchatx.src.backend.traffic_stats import (
    COMPONENT_CRAWLER,
    COMPONENT_LXMF,
    COMPONENT_NOMADNET,
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
    # ~0.3s for 300 bytes -> ~1000 B/s raw. EMA blends with the prior
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


def test_flood_guard_warns_above_component_threshold(caplog):
    """A sustained component rate above the threshold logs one warning."""
    meter = TrafficStats()
    meter.record(COMPONENT_RRC, tx=1)
    meter.check_flood_rates(now=100.0)  # baseline sample, no rates yet
    # 80 KB/s for 10s: above the 64 KB/s component floor, below the
    # 128 KB/s total floor, so exactly one warning fires.
    meter.record(COMPONENT_RRC, tx=(80 * 1024 * 10))
    with caplog.at_level(logging.WARNING, logger="meshchatx.traffic"):
        emitted = meter.check_flood_rates(now=110.0)
    assert len(emitted) == 1
    warning = emitted[0]
    assert warning["component"] == COMPONENT_RRC
    assert warning["direction"] == "tx"
    assert warning["kbps"] == 80.0
    assert "RRC hubs" in caplog.text
    assert meter.recent_warnings() == emitted


def test_flood_guard_rate_limits_repeats():
    """A second breach inside the warn window stays silent."""
    meter = TrafficStats()
    meter.record(COMPONENT_RRC, tx=1)
    meter.check_flood_rates(now=100.0)
    meter.record(COMPONENT_RRC, tx=(80 * 1024 * 10))
    assert len(meter.check_flood_rates(now=110.0)) == 1
    meter.record(COMPONENT_RRC, tx=(80 * 1024 * 10))
    assert meter.check_flood_rates(now=120.0) == []
    # After the window passes, the same breach warns again. The byte delta
    # scales with the sampled window so the rate stays at 80 KB/s.
    meter.record(COMPONENT_RRC, tx=(80 * 1024 * 180))
    assert len(meter.check_flood_rates(now=300.0)) == 1


def test_flood_guard_ignores_normal_traffic():
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=1)
    meter.check_flood_rates(now=100.0)
    meter.record(COMPONENT_LXMF, tx=(16 * 1024 * 10))
    assert meter.check_flood_rates(now=110.0) == []
    assert meter.recent_warnings() == []


def test_flood_guard_total_threshold_across_components():
    """Two components under the per-component floor can still sum over."""
    meter = TrafficStats()
    meter.record(COMPONENT_LXMF, tx=1)
    meter.record(COMPONENT_NOMADNET, tx=1)
    meter.check_flood_rates(now=100.0)
    each = 70 * 1024 * 10
    meter.record(COMPONENT_LXMF, tx=each)
    meter.record(COMPONENT_NOMADNET, tx=each)
    emitted = meter.check_flood_rates(now=110.0)
    keys = {(w["component"], w["direction"]) for w in emitted}
    assert ("total", "tx") in keys
    assert ("lxmf", "tx") in keys
    assert ("nomadnet", "tx") in keys


def test_flood_guard_payload_and_hint():
    meter = TrafficStats()
    meter.record(COMPONENT_RRC, tx=1)
    meter.check_flood_rates(now=100.0)
    meter.record(COMPONENT_RRC, tx=(80 * 1024 * 10))
    meter.check_flood_rates(now=110.0)
    payload = meter.snapshot([_iface("i0", txb=0, rxb=0)])
    assert payload["warnings"]
    hints = compute_hints(payload, _App(_Ctx()))
    assert hints[0]["id"] == "flood_warning"
    assert hints[0]["severity"] == "warning"
    assert hints[0]["params"]["component"] == "RRC hubs"


def test_flood_guard_thread_starts_once():
    before = sum(1 for t in threading.enumerate() if t.name == "mcx-traffic-guard")
    meter = TrafficStats()
    meter.start_flood_guard()
    meter.start_flood_guard()
    after = sum(1 for t in threading.enumerate() if t.name == "mcx-traffic-guard")
    # Other meters in the same process may already own a guard thread.
    assert after - before == 1
    assert meter._flood_started is True


def test_sample_interfaces_detects_residual_flood():
    """Wire totals above the floor warn even with zero component bytes."""
    meter = TrafficStats()
    meter.sample_interfaces([_iface("i0", txb=0, rxb=0)])
    # Simulate a 10s window with 2 MiB sent: 204.8 KB/s, above the floor.
    meter._iface_sample_at -= 10.0
    emitted = meter.sample_interfaces([_iface("i0", txb=2 * 1024 * 1024, rxb=0)])
    assert [(w["component"], w["direction"]) for w in emitted] == [("total", "tx")]
    assert emitted[0]["kbps"] == 204.8


def test_sample_interfaces_dedupes_rapid_samples():
    meter = TrafficStats()
    meter.sample_interfaces([_iface("i0", txb=0, rxb=0)])
    assert meter.sample_interfaces([_iface("i0", txb=10**9, rxb=0)]) == []


def test_snapshot_warns_on_hot_interface_totals(caplog):
    """A UI poll of a hot wire logs the same total warning."""
    meter = TrafficStats()
    meter.snapshot([_iface("i0", txb=0, rxb=0)])
    time.sleep(0.3)
    with caplog.at_level(logging.WARNING, logger="meshchatx.traffic"):
        payload = meter.snapshot([_iface("i0", txb=int(200 * 1024 * 0.3), rxb=0)])
    assert payload["warnings"]
    assert payload["warnings"][0]["component"] == "total"
    assert "total" in caplog.text or "KB/s" in caplog.text
