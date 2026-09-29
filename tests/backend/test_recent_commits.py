# SPDX-License-Identifier: 0BSD

"""Adversarial and fuzz tests for rnstatus traffic-total formatting."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st


def test_traffic_totals_data_share():
    from meshchatx.src.backend.rnstatus_handler import _format_traffic_totals

    stats = {
        "rxs": 100,
        "txs": 200,
        "prxs": 10,
        "arxs": 20,
        "ptxs": 30,
        "atxs": 40,
    }
    totals = _format_traffic_totals(stats)
    assert totals is not None
    assert totals["data_rx_pct"] == 70
    assert totals["data_tx_pct"] == 65


@settings(max_examples=80, deadline=None)
@given(
    rxs=st.floats(
        min_value=1.0,
        max_value=1_000_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    txs=st.floats(
        min_value=1.0,
        max_value=1_000_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    prxs=st.floats(
        min_value=0.0,
        max_value=500_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    arxs=st.floats(
        min_value=0.0,
        max_value=500_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    ptxs=st.floats(
        min_value=0.0,
        max_value=500_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    atxs=st.floats(
        min_value=0.0,
        max_value=500_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_traffic_totals_data_share_fuzz(rxs, txs, prxs, arxs, ptxs, atxs):
    from meshchatx.src.backend.rnstatus_handler import _format_traffic_totals

    stats = {
        "rxs": rxs,
        "txs": txs,
        "prxs": min(prxs, rxs),
        "arxs": min(arxs, max(0.0, rxs - min(prxs, rxs))),
        "ptxs": min(ptxs, txs),
        "atxs": min(atxs, max(0.0, txs - min(ptxs, txs))),
    }
    totals = _format_traffic_totals(stats)
    assert totals is not None
    rx_part = max(0.0, rxs - (stats["prxs"] + stats["arxs"]))
    tx_part = max(0.0, txs - (stats["ptxs"] + stats["atxs"]))
    if not (rxs and txs):
        assert "data_rx_pct" not in totals
        assert "data_tx_pct" not in totals
        return
    if rx_part <= 0:
        assert "data_rx_pct" not in totals
    else:
        assert totals["data_rx_pct"] == int(min(100.0, (rx_part / rxs) * 100.0))
    if tx_part <= 0:
        assert "data_tx_pct" not in totals
    else:
        assert totals["data_tx_pct"] == int(min(100.0, (tx_part / txs) * 100.0))


def test_traffic_totals_keeps_truncated_zero_data_share():
    from meshchatx.src.backend.rnstatus_handler import _format_traffic_totals

    totals = _format_traffic_totals(
        {
            "rxs": 432934.0,
            "txs": 1.0,
            "prxs": 0.0,
            "arxs": 432407.0,
            "ptxs": 0.0,
            "atxs": 0.0,
        },
    )
    assert totals is not None
    assert totals["data_rx_pct"] == 0
    assert totals["data_tx_pct"] == 100


@settings(max_examples=60, deadline=None)
@given(
    part=st.floats(
        min_value=0.0,
        max_value=10_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    total=st.floats(
        min_value=0.0,
        max_value=10_000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_flow_share_percent(part, total):
    from meshchatx.src.backend.rnstatus_handler import _flow_share_percent

    result = _flow_share_percent(part, total)
    if total <= 0 or part <= 0:
        assert result is None
    else:
        assert result == int(min(100.0, (part / total) * 100.0))

