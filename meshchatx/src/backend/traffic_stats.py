# SPDX-License-Identifier: 0BSD
"""Wire traffic attribution for the diagnostics surface.

Interface counters come from RNS's own get_interface_stats(): rxb/txb are
cumulative wire bytes per interface and arxb/atxb/prxb/ptxb are the
announce and propagated-message counters Reticulum already keeps. This
module diffs them into rates.

Application components (LXMF delivery, RRC hub links, NomadNet page
requests, the crawler) report their own payload bytes through
TrafficStats.record(). Whatever the interface totals leave unaccounted
for is reported as network overhead: announces, path requests, link
handshakes, resource framing, and transport forwarding.
"""

from __future__ import annotations

import threading
import time
from collections import deque

# Components that report their own wire traffic.
COMPONENT_LXMF = "lxmf"
COMPONENT_RRC = "rrc"
COMPONENT_NOMADNET = "nomadnet"
COMPONENT_CRAWLER = "crawler"

_COMPONENT_LABELS = {
    COMPONENT_LXMF: "LXMF messaging",
    COMPONENT_RRC: "RRC hubs",
    COMPONENT_NOMADNET: "NomadNet pages",
    COMPONENT_CRAWLER: "NomadNet crawler",
}

_MAX_HISTORY = 120

# Exponential smoothing for display rates: the UI polls on a 3 s cadence
# and raw per-window rates spike to zero between bursts. EMA keeps a
# short memory so numbers track smoothly instead of twitching.
_EMA_ALPHA = 0.35


class _Counter:
    __slots__ = ("components", "prev_rx", "prev_tx", "rx", "tx")

    def __init__(self):
        self.tx = 0
        self.rx = 0
        self.prev_tx = 0
        self.prev_rx = 0
        # peer buckets carry a per-component byte breakdown for drilldown
        self.components: dict[str, list[int]] = {}


class TrafficStats:
    """Thread-safe traffic meter.

    Components call record() from wherever bytes move. The HTTP handler
    calls snapshot(interface_rows) with the current raw interface stats;
    rates are computed against the previous snapshot.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._components: dict[str, _Counter] = {}
        self._last_sample_at: float | None = None
        self._last_interfaces: dict[str, dict] = {}
        self._interface_rates: list[dict] = []
        self._last_totals = _Counter()
        self._total_rates = {"tx_bps": 0.0, "rx_bps": 0.0}
        self._history: deque = deque(maxlen=_MAX_HISTORY)
        self._last_payload: dict | None = None
        self._started_at = time.time()
        self._ema: dict[str, float] = {}
        self._peers: dict[str, _Counter] = {}

    def _smooth(self, key: str, value: float) -> float:
        prev = self._ema.get(key)
        if prev is None:
            self._ema[key] = value
            return value
        smoothed = prev + _EMA_ALPHA * (value - prev)
        self._ema[key] = smoothed
        return smoothed

    def record(
        self,
        component: str,
        tx: int = 0,
        rx: int = 0,
        peer: str | None = None,
    ) -> None:
        if not component or (not tx and not rx):
            return
        with self._lock:
            counter = self._components.get(component)
            if counter is None:
                counter = _Counter()
                self._components[component] = counter
            counter.tx += int(tx)
            counter.rx += int(rx)
            if peer:
                peer_counter = self._peers.get(peer)
                if peer_counter is None:
                    peer_counter = _Counter()
                    self._peers[peer] = peer_counter
                peer_counter.tx += int(tx)
                peer_counter.rx += int(rx)
                by_comp = peer_counter.components.setdefault(component, [0, 0])
                by_comp[0] += int(tx)
                by_comp[1] += int(rx)

    def snapshot(self, interface_rows: list[dict]) -> dict:
        """Build the traffic payload from the raw interface stats rows."""
        now = time.monotonic()
        with self._lock:
            elapsed = None
            if self._last_sample_at is not None:
                elapsed = now - self._last_sample_at
                if elapsed < 0.25 and self._last_payload is not None:
                    # Sub-second polls reuse the last computed payload so
                    # rapid refreshes do not divide tiny deltas by tiny
                    # windows.
                    return self._last_payload

            interfaces = self._diff_interfaces(interface_rows, elapsed)

            total_tx = sum(row.get("txb") or 0 for row in interfaces)
            total_rx = sum(row.get("rxb") or 0 for row in interfaces)
            if elapsed:
                self._total_rates = {
                    "tx_bps": self._smooth(
                        "tot:tx",
                        max(0.0, (total_tx - self._last_totals.tx) / elapsed),
                    ),
                    "rx_bps": self._smooth(
                        "tot:rx",
                        max(0.0, (total_rx - self._last_totals.rx) / elapsed),
                    ),
                }
            else:
                # Seed the smoother at zero on the first sample so the first
                # burst ramps like every other series does.
                self._smooth("tot:tx", 0.0)
                self._smooth("tot:rx", 0.0)
            self._last_totals.tx = total_tx
            self._last_totals.rx = total_rx
            self._last_sample_at = now
            self._history.append(
                {
                    "t": time.time(),
                    "tx_bps": self._total_rates["tx_bps"],
                    "rx_bps": self._total_rates["rx_bps"],
                }
            )
            self._last_payload = self._build_payload(elapsed_override=elapsed)
            return self._last_payload

    def _diff_interfaces(self, rows: list[dict], elapsed) -> list[dict]:
        out = []
        previous = self._last_interfaces
        current: dict[str, dict] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name") or row.get("short_name") or "unknown"
            txb = row.get("txb") or 0
            rxb = row.get("rxb") or 0
            arxb = row.get("arxb") or 0
            atxb = row.get("atxb") or 0
            prxb = row.get("prxb") or 0
            ptxb = row.get("ptxb") or 0
            prev = previous.get(name, {})

            def rate(now_v, prev_v, window=elapsed):
                if not window or prev_v is None:
                    return 0.0
                return max(0.0, (now_v - prev_v) / window)

            out.append(
                {
                    "name": name,
                    "short_name": row.get("short_name"),
                    "type": row.get("type"),
                    "txb": txb,
                    "rxb": rxb,
                    "tx_bps": self._smooth(f"i:{name}:tx", rate(txb, prev.get("txb"))),
                    "rx_bps": self._smooth(f"i:{name}:rx", rate(rxb, prev.get("rxb"))),
                    "announce_tx_bps": self._smooth(
                        f"i:{name}:atx", rate(atxb, prev.get("atxb"))
                    ),
                    "announce_rx_bps": self._smooth(
                        f"i:{name}:arx", rate(arxb, prev.get("arxb"))
                    ),
                    "propagated_tx_bps": self._smooth(
                        f"i:{name}:ptx", rate(ptxb, prev.get("ptxb"))
                    ),
                    "propagated_rx_bps": self._smooth(
                        f"i:{name}:prx", rate(prxb, prev.get("prxb"))
                    ),
                }
            )
            current[name] = {
                "txb": txb,
                "rxb": rxb,
                "atxb": atxb,
                "arxb": arxb,
                "ptxb": ptxb,
                "prxb": prxb,
            }
        self._last_interfaces = current
        self._interface_rates = out
        return out

    def _build_payload(self, elapsed_override) -> dict:
        elapsed = elapsed_override
        components = []
        comp_tx = comp_rx = 0.0
        comp_tx_rate = comp_rx_rate = 0.0
        for comp_id, counter in self._components.items():
            tx_rate = rx_rate = 0.0
            if elapsed:
                tx_rate = (counter.tx - counter.prev_tx) / elapsed
                rx_rate = (counter.rx - counter.prev_rx) / elapsed
            tx_rate = self._smooth(f"c:{comp_id}:tx", tx_rate)
            rx_rate = self._smooth(f"c:{comp_id}:rx", rx_rate)
            counter.prev_tx = counter.tx
            counter.prev_rx = counter.rx
            components.append(
                {
                    "id": comp_id,
                    "label": _COMPONENT_LABELS.get(comp_id, comp_id),
                    "tx_bytes": counter.tx,
                    "rx_bytes": counter.rx,
                    "tx_bps": tx_rate,
                    "rx_bps": rx_rate,
                }
            )
            comp_tx += counter.tx
            comp_rx += counter.rx
            comp_tx_rate += tx_rate
            comp_rx_rate += rx_rate
        components.sort(key=lambda c: c["tx_bytes"] + c["rx_bytes"], reverse=True)

        peers = []
        for peer_hash, pc in self._peers.items():
            ptx_rate = prx_rate = 0.0
            if elapsed:
                ptx_rate = (pc.tx - pc.prev_tx) / elapsed
                prx_rate = (pc.rx - pc.prev_rx) / elapsed
            pc.prev_tx = pc.tx
            pc.prev_rx = pc.rx
            peers.append(
                {
                    "hash": peer_hash,
                    "tx_bytes": pc.tx,
                    "rx_bytes": pc.rx,
                    "tx_bps": self._smooth(f"p:{peer_hash}:tx", ptx_rate),
                    "rx_bps": self._smooth(f"p:{peer_hash}:rx", prx_rate),
                    "components": {
                        comp: {"tx": t, "rx": r}
                        for comp, (t, r) in pc.components.items()
                    },
                }
            )
        peers.sort(key=lambda p: p["tx_bytes"] + p["rx_bytes"], reverse=True)
        peers = peers[:40]

        totals = {
            "tx_bytes": self._last_totals.tx,
            "rx_bytes": self._last_totals.rx,
            "tx_bps": self._total_rates["tx_bps"],
            "rx_bps": self._total_rates["rx_bps"],
        }
        residual = {
            "tx_bytes": max(0, totals["tx_bytes"] - comp_tx),
            "rx_bytes": max(0, totals["rx_bytes"] - comp_rx),
            "tx_bps": max(0.0, totals["tx_bps"] - comp_tx_rate),
            "rx_bps": max(0.0, totals["rx_bps"] - comp_rx_rate),
        }
        return {
            "updated_at": time.time(),
            "uptime_s": max(0, int(time.time() - self._started_at)),
            "interfaces": list(self._interface_rates),
            "components": components,
            "peers": peers,
            "totals": totals,
            "residual": residual,
            "history": list(self._history),
        }


def _cfg_bool(config, name: str) -> bool:
    """Read a BoolConfig-or-plain value without tripping on wrapper truthiness."""
    value = getattr(config, name, None) if config is not None else None
    if hasattr(value, "get") and callable(value.get):
        try:
            return bool(value.get())
        except Exception:
            return False
    return bool(value)


def _transport_enabled(app) -> bool:
    reticulum = getattr(app, "reticulum", None)
    if reticulum is None:
        return False
    try:
        return bool(reticulum.transport_enabled())
    except Exception:
        return False


def compute_hints(payload: dict, app) -> list[dict]:
    """Translate traffic shape into plain-language explanations.

    Each hint is a structured {id, params} pair so the frontend can
    localize; severity is informational unless a component dominates.
    """
    hints: list[dict] = []
    totals = payload.get("totals") or {}
    residual = payload.get("residual") or {}
    components = payload.get("components") or []
    interfaces = payload.get("interfaces") or []
    tx_bps = totals.get("tx_bps") or 0.0
    rx_bps = totals.get("rx_bps") or 0.0

    if tx_bps + rx_bps < 8:
        hints.append({"id": "idle", "severity": "info", "params": {}})
        return hints

    ctx = getattr(app, "current_context", None)
    config = getattr(ctx, "config", None)

    # Transport mode forwards third-party traffic: residual that dwarfs
    # attributed components means the wire load is network overhead.
    residual_share = 0.0
    if tx_bps + rx_bps > 0:
        residual_share = (
            (residual.get("tx_bps") or 0) + (residual.get("rx_bps") or 0)
        ) / (tx_bps + rx_bps)
    transport_enabled = _transport_enabled(app)
    if transport_enabled and residual_share > 0.5:
        hints.append(
            {
                "id": "transport_mode",
                "severity": "info",
                "params": {
                    "tx_bps": round(residual.get("tx_bps") or 0, 1),
                    "rx_bps": round(residual.get("rx_bps") or 0, 1),
                },
            }
        )

    # Announce churn: discovery-capable interfaces and announce byte rates.
    announce_rate = sum(
        (i.get("announce_tx_bps") or 0) + (i.get("announce_rx_bps") or 0)
        for i in interfaces
    )
    discovery_kinds = {"autointerface", "autodiscoveryinterface"}
    discovery_count = sum(
        1 for i in interfaces if (i.get("type") or "").lower() in discovery_kinds
    )
    if announce_rate > 0 or discovery_count:
        hints.append(
            {
                "id": "announce_discovery",
                "severity": "info",
                "params": {
                    "bps": round(announce_rate, 1),
                    "discovery_interfaces": discovery_count,
                },
            }
        )

    # Propagated message traffic on a propagation node.
    propagated_rate = sum(
        (i.get("propagated_tx_bps") or 0) + (i.get("propagated_rx_bps") or 0)
        for i in interfaces
    )
    propagation_enabled = _cfg_bool(config, "lxmf_local_propagation_node_enabled")
    if propagation_enabled and propagated_rate > 0.5:
        hint_id = "propagation_node_serving"
    elif propagation_enabled:
        hint_id = "propagation_node_enabled"
    elif propagated_rate > 0.5:
        hint_id = "propagation_node_inbound"
    else:
        hint_id = None
    if hint_id:
        hints.append(
            {
                "id": hint_id,
                "severity": "info",
                "params": {"bps": round(propagated_rate, 1)},
            }
        )

    # Connected RRC hubs keep links warm: show count when hub traffic is
    # a visible component.
    rrc = next((c for c in components if c.get("id") == COMPONENT_RRC), None)
    hubs = 0
    rrc_manager = getattr(ctx, "rrc_manager", None) if ctx else None
    if rrc_manager is not None:
        try:
            from meshchatx.src.backend.rrc.manager import RRCHub

            hubs = sum(
                1
                for h in getattr(rrc_manager, "hubs", [])
                if getattr(h, "status", None) == RRCHub.STATUS_CONNECTED
            )
        except Exception:
            hubs = 0
    if hubs or (rrc and rrc.get("tx_bytes", 0) + rrc.get("rx_bytes", 0) > 0):
        hints.append(
            {
                "id": "rrc_hubs",
                "severity": "info",
                "params": {"hubs": hubs},
            }
        )

    # Crawler: distinguish actively fetching from merely enabled.
    crawler = next((c for c in components if c.get("id") == COMPONENT_CRAWLER), None)
    crawler_enabled = _cfg_bool(config, "crawler_enabled")
    crawler_rate = (
        (crawler.get("tx_bps") or 0) + (crawler.get("rx_bps") or 0) if crawler else 0.0
    )
    crawler_bytes = (
        (crawler.get("tx_bytes") or 0) + (crawler.get("rx_bytes") or 0)
        if crawler
        else 0
    )
    if crawler_enabled and crawler_rate > 0.5:
        hint_id = "crawler"
    elif crawler_enabled:
        hint_id = "crawler_enabled"
    elif crawler_bytes > 0:
        hint_id = "crawler_observed"
    else:
        hint_id = None
    if hint_id:
        hints.append(
            {
                "id": hint_id,
                "severity": "info",
                "params": {"bps": round(crawler_rate, 1)},
            }
        )

    return hints


_meter: TrafficStats | None = None


def get_meter() -> TrafficStats:
    global _meter
    if _meter is None:
        _meter = TrafficStats()
    return _meter
