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

import contextlib
import logging
import threading
import time
from collections import deque

_log = logging.getLogger("meshchatx.traffic")

# Components that report their own wire traffic.
COMPONENT_LXMF = "lxmf"
COMPONENT_RRC = "rrc"
COMPONENT_NOMADNET = "nomadnet"
COMPONENT_CRAWLER = "crawler"
COMPONENT_RNCP = "rncp"
COMPONENT_FILESYNC = "filesync"

_COMPONENT_LABELS = {
    COMPONENT_LXMF: "LXMF messaging",
    COMPONENT_RRC: "RRC hubs",
    COMPONENT_NOMADNET: "NomadNet pages",
    COMPONENT_CRAWLER: "NomadNet crawler",
    COMPONENT_RNCP: "RNCP transfers",
    COMPONENT_FILESYNC: "File sync",
}

# Active transfer registry bounds. Entries leave on finish; the cap and the
# stale sweep protect against a missed finish call.
MAX_TRANSFERS = 32
TRANSFER_STALE_S = 600.0

_MAX_HISTORY = 120

# Exponential smoothing for display rates: the UI polls on a 3 s cadence
# and raw per-window rates spike to zero between bursts. EMA keeps a
# short memory so numbers track smoothly instead of twitching.
_EMA_ALPHA = 0.35

# Flood detection: sustained rates above these thresholds log a rate
# limited warning naming the component. Defaults sit far above healthy
# mesh traffic (a busy TCP peer peaks in the tens of KB/s) so they only
# trip on a genuine runaway loop or message storm.
FLOOD_WINDOW_S = 10.0
FLOOD_SAMPLE_INTERVAL_S = 5.0
FLOOD_TOTAL_TX_BPS = 128 * 1024
FLOOD_TOTAL_RX_BPS = 1024 * 1024
FLOOD_COMPONENT_TX_BPS = 64 * 1024
FLOOD_COMPONENT_RX_BPS = 512 * 1024
FLOOD_WARN_MIN_INTERVAL_S = 120.0
FLOOD_WARN_HISTORY = 16


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
        # Flood guard state: cumulative counters sampled on an interval by
        # the background thread so runaway traffic is logged even when no
        # UI page is open to poll snapshots.
        self._flood_started = False
        self._flood_last_sample = time.monotonic()
        self._flood_last_counters: dict[str, tuple[int, int]] = {}
        self._flood_last_total = (0, 0)
        self._flood_warned_at: dict[str, float] = {}
        self._flood_warnings: deque = deque(maxlen=FLOOD_WARN_HISTORY)
        # Separate lock: snapshot() holds the main lock and also samples
        # totals, so the warning path must not re-enter it.
        self._flood_warn_lock = threading.Lock()
        # Interface counter samples for residual detection (announces, path
        # requests, link handshakes, forwarding): fed by the app's bounded
        # interface stats path so the guard thread never touches RNS RPC.
        self._iface_sample_at = 0.0
        self._iface_totals: tuple[int, int] | None = None
        # Active transfers: components push progress here so the Traffic
        # page can show in-flight work and byte attribution stays in one
        # place (deltas are metered as progress arrives).
        self._transfers: dict[str, dict] = {}

    def start_flood_guard(self) -> None:
        """Start the background flood detector once per meter."""
        with self._lock:
            if self._flood_started:
                return
            self._flood_started = True
        thread = threading.Thread(
            target=self._flood_loop,
            daemon=True,
            name="mcx-traffic-guard",
        )
        thread.start()

    def _flood_loop(self) -> None:
        while True:
            time.sleep(FLOOD_SAMPLE_INTERVAL_S)
            with contextlib.suppress(Exception):
                self.check_flood_rates()

    def check_flood_rates(self, now: float | None = None) -> list[dict]:
        """Sample component rates and log rate limited flood warnings.

        Returns the warnings emitted by this call. Kept callable so tests
        and future callers can drive detection without the thread.
        """
        now = time.monotonic() if now is None else float(now)
        with self._lock:
            elapsed = max(0.001, now - self._flood_last_sample)
            self._flood_last_sample = now
            samples = {cid: (c.tx, c.rx) for cid, c in self._components.items()}
            total_tx = sum(v[0] for v in samples.values())
            total_rx = sum(v[1] for v in samples.values())

        emitted = []
        for component, (tx, rx) in samples.items():
            prev = self._flood_last_counters.get(component)
            if prev is None:
                continue
            tx_rate = max(0.0, (tx - prev[0]) / elapsed)
            rx_rate = max(0.0, (rx - prev[1]) / elapsed)
            if tx_rate >= FLOOD_COMPONENT_TX_BPS:
                warning = self._emit_flood_warning(component, "tx", tx_rate, now=now)
                if warning is not None:
                    emitted.append(warning)
            if rx_rate >= FLOOD_COMPONENT_RX_BPS:
                warning = self._emit_flood_warning(component, "rx", rx_rate, now=now)
                if warning is not None:
                    emitted.append(warning)
        self._flood_last_counters = samples

        prev_total = self._flood_last_total
        self._flood_last_total = (total_tx, total_rx)
        total_tx_rate = max(0.0, (total_tx - prev_total[0]) / elapsed)
        total_rx_rate = max(0.0, (total_rx - prev_total[1]) / elapsed)
        emitted.extend(self._check_total_rates(total_tx_rate, total_rx_rate, now))
        return emitted

    def _emit_flood_warning(
        self,
        component: str,
        direction: str,
        rate: float,
        now: float | None = None,
    ):
        key = component + ":" + direction
        now = time.monotonic() if now is None else float(now)
        last = self._flood_warned_at.get(key, float("-inf"))
        if now - last < FLOOD_WARN_MIN_INTERVAL_S:
            return None
        self._flood_warned_at[key] = now
        label = _COMPONENT_LABELS.get(component, component)
        entry = {
            "ts": time.time(),
            "component": component,
            "label": label,
            "direction": direction,
            "bps": round(rate, 1),
            "kbps": round(rate / 1024.0, 1),
        }
        with self._flood_warn_lock:
            self._flood_warnings.append(entry)
        _log.warning(
            "Sustained high traffic on %s: %.1f KB/s %s. "
            "Check for a retry loop or a stuck sender.",
            label,
            rate / 1024.0,
            "outbound" if direction == "tx" else "inbound",
        )
        return entry

    # -- active transfers --------------------------------------------------

    def transfer_progress(
        self,
        transfer_id: str,
        *,
        kind: str,
        direction: str = "tx",
        peer: str | None = None,
        done: int | None = None,
        total: int | None = None,
        progress: float | None = None,
        label: str | None = None,
    ) -> None:
        """Report transfer progress and meter the byte delta.

        Components call this from their existing progress callbacks. The
        delta since the previous report is attributed to kind, so the
        component table and the transfer list cannot disagree.
        """
        if not transfer_id or not kind:
            return
        now = time.monotonic()
        delta = 0
        with self._lock:
            entry = self._transfers.get(transfer_id)
            if entry is None:
                entry = {
                    "id": transfer_id,
                    "kind": kind,
                    "direction": "rx" if direction == "rx" else "tx",
                    "peer": peer,
                    "label": label,
                    "total": None,
                    "done": 0,
                    "progress": 0.0,
                    "started_at": time.time(),
                }
                self._transfers[transfer_id] = entry
                self._prune_transfers_locked(now)
            if peer:
                entry["peer"] = peer
            if label:
                entry["label"] = label
            if direction:
                entry["direction"] = "rx" if direction == "rx" else "tx"
            if total is not None:
                try:
                    entry["total"] = max(0, int(total))
                except (TypeError, ValueError):
                    pass
            if done is not None:
                try:
                    done_i = max(0, int(done))
                except (TypeError, ValueError):
                    done_i = None
                if done_i is not None:
                    delta = max(0, done_i - int(entry.get("done") or 0))
                    entry["done"] = max(int(entry.get("done") or 0), done_i)
            if progress is not None:
                try:
                    entry["progress"] = min(1.0, max(0.0, float(progress)))
                except (TypeError, ValueError):
                    pass
            elif entry.get("total"):
                entry["progress"] = min(
                    1.0,
                    float(entry.get("done") or 0) / float(entry["total"]),
                )
            entry["updated_at"] = time.time()
        if delta:
            if entry.get("direction") == "rx":
                self.record(kind, rx=delta, peer=entry.get("peer"))
            else:
                self.record(kind, tx=delta, peer=entry.get("peer"))

    def transfer_finished(self, transfer_id: str) -> None:
        """Drop a finished transfer from the active list."""
        if not transfer_id:
            return
        with self._lock:
            self._transfers.pop(transfer_id, None)

    def active_transfers(self) -> list[dict]:
        with self._lock:
            return self._active_transfers_locked()

    def _active_transfers_locked(self) -> list[dict]:
        """Caller holds _lock. snapshot() also builds payloads under it."""
        self._prune_transfers_locked(time.monotonic())
        entries = [
            {
                "id": entry.get("id"),
                "kind": entry.get("kind"),
                "label": entry.get("label")
                or _COMPONENT_LABELS.get(entry.get("kind"), entry.get("kind")),
                "direction": entry.get("direction"),
                "peer": entry.get("peer"),
                "done": int(entry.get("done") or 0),
                "total": entry.get("total"),
                "progress": round(float(entry.get("progress") or 0.0), 3),
                "started_at": entry.get("started_at"),
            }
            for entry in self._transfers.values()
        ]
        entries.sort(key=lambda e: e.get("started_at") or 0.0, reverse=True)
        return entries

    def _prune_transfers_locked(self, now_monotonic: float) -> None:
        """Caller holds _lock. Drop stale entries, then cap the registry."""
        cutoff = time.time() - TRANSFER_STALE_S
        stale = [
            tid
            for tid, entry in self._transfers.items()
            if (entry.get("updated_at") or entry.get("started_at") or 0.0) < cutoff
        ]
        for tid in stale:
            self._transfers.pop(tid, None)
        if len(self._transfers) <= MAX_TRANSFERS:
            return
        ordered = sorted(
            self._transfers.items(),
            key=lambda item: item[1].get("started_at") or 0.0,
        )
        for tid, _entry in ordered[: len(self._transfers) - MAX_TRANSFERS]:
            self._transfers.pop(tid, None)

    def recent_warnings(self) -> list[dict]:
        with self._flood_warn_lock:
            return list(self._flood_warnings)

    def sample_interfaces(self, interface_rows: list[dict]) -> list[dict]:
        """Feed raw interface counter rows for residual flood detection.

        Rows are the same shape snapshot() consumes. The app calls this
        from its bounded interface stats path, so announce storms, path
        request sprays, and transport forwarding are still caught when no
        UI page is polling. Returns warnings emitted by this sample.
        """
        if not isinstance(interface_rows, list):
            return []
        now = time.monotonic()
        with self._lock:
            have_baseline = self._iface_totals is not None
            elapsed = now - self._iface_sample_at if self._iface_sample_at else 0.0
            if have_baseline and elapsed < FLOOD_SAMPLE_INTERVAL_S:
                return []
            tx = sum(
                row.get("txb") or 0 for row in interface_rows if isinstance(row, dict)
            )
            rx = sum(
                row.get("rxb") or 0 for row in interface_rows if isinstance(row, dict)
            )
            prev = self._iface_totals
            self._iface_sample_at = now
            self._iface_totals = (tx, rx)
        if prev is None or elapsed <= 0:
            return []
        tx_rate = max(0.0, (tx - prev[0]) / elapsed)
        rx_rate = max(0.0, (rx - prev[1]) / elapsed)
        return self._check_total_rates(tx_rate, rx_rate, now)

    def _check_total_rates(
        self,
        tx_rate: float,
        rx_rate: float,
        now: float | None = None,
    ) -> list[dict]:
        emitted = []
        if tx_rate >= FLOOD_TOTAL_TX_BPS:
            warning = self._emit_flood_warning("total", "tx", tx_rate, now=now)
            if warning is not None:
                emitted.append(warning)
        if rx_rate >= FLOOD_TOTAL_RX_BPS:
            warning = self._emit_flood_warning("total", "rx", rx_rate, now=now)
            if warning is not None:
                emitted.append(warning)
        return emitted

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
                raw_tx = max(0.0, (total_tx - self._last_totals.tx) / elapsed)
                raw_rx = max(0.0, (total_rx - self._last_totals.rx) / elapsed)
                self._total_rates = {
                    "tx_bps": self._smooth("tot:tx", raw_tx),
                    "rx_bps": self._smooth("tot:rx", raw_rx),
                }
                # A UI poll is also a sample: warn when the wire total is
                # running hot even if the background guard is not started.
                # Detection uses the raw rate, the smoothed rate is for
                # display only.
                self._check_total_rates(raw_tx, raw_rx)
            else:
                # Seed the smoother at zero on the first sample so the first
                # burst ramps like every other series does.
                self._smooth("tot:tx", 0.0)
                self._smooth("tot:rx", 0.0)
            self._last_totals.tx = total_tx
            self._last_totals.rx = total_rx
            self._last_sample_at = now
            self._last_payload = self._build_payload(elapsed_override=elapsed)
            # History entries carry the dominant component so the chart
            # tooltip can name what was driving each point in time.
            top_id = None
            top_bps = 0.0
            for row in self._last_payload.get("components") or []:
                rate = (row.get("tx_bps") or 0.0) + (row.get("rx_bps") or 0.0)
                if rate > top_bps:
                    top_id = row.get("id")
                    top_bps = rate
            self._history.append(
                {
                    "t": time.time(),
                    "tx_bps": self._total_rates["tx_bps"],
                    "rx_bps": self._total_rates["rx_bps"],
                    "top": top_id if top_bps >= 1.0 else None,
                    "top_bps": round(top_bps, 1),
                }
            )
            self._last_payload["history"] = list(self._history)
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
            "peers_total": len(self._peers),
            "transfers": self._active_transfers_locked(),
            "totals": totals,
            "residual": residual,
            "history": list(self._history),
            "warnings": list(self._flood_warnings),
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

    # In-flight transfers explain an active burst better than any rate.
    transfers = payload.get("transfers") or []
    if transfers:
        kinds = sorted({t.get("kind") for t in transfers if t.get("kind")})
        hints.append(
            {
                "id": "active_transfers",
                "severity": "info",
                "params": {
                    "count": len(transfers),
                    "kinds": ", ".join(kinds),
                },
            },
        )

    # Flood warnings lead: they explain why the numbers were high and what
    # to check, and stay visible after a burst ends.
    hints.extend(
        {
            "id": "flood_warning",
            "severity": "warning",
            "params": {
                "component": warning.get("label") or warning.get("component"),
                "kbps": warning.get("kbps"),
                "direction": warning.get("direction"),
            },
        }
        for warning in reversed((payload.get("warnings") or [])[-2:])
    )

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
        _meter.start_flood_guard()
    return _meter
