# SPDX-License-Identifier: 0BSD
"""Adversarial stat dicts for rnstatus formatters: never raise, never 500."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.rnstatus_handler import (
    _format_queue_stats,
    _format_traffic_totals,
    _format_transport_flow_section,
    fmt_packet_count,
    fmt_per_second,
    fmt_percentage,
    size_str,
    speed_str,
)

WEIRD = [
    None,
    "abc",
    "",
    "NaN",
    float("nan"),
    float("inf"),
    -float("inf"),
    -1,
    0,
    1e300,
    [1, 2],
    {"x": 1},
    True,
    b"\x00\xff",
    2**63,
]


class TestSizeStrNeverRaises:
    @pytest.mark.parametrize("v", WEIRD)
    def test_size_str(self, v):
        size_str(v)

    @pytest.mark.parametrize("v", WEIRD)
    def test_speed_str(self, v):
        speed_str(v)

    @pytest.mark.parametrize("v", WEIRD)
    def test_fmt_helpers(self, v):
        fmt_packet_count(v)
        fmt_per_second(v)
        fmt_percentage(v)

    def test_size_str_negative_and_huge(self):
        assert "YB" in size_str(1e30) or "ZB" in size_str(1e30)
        size_str(-500)


class TestSectionFormattersNeverRaise:
    @pytest.mark.parametrize("v", WEIRD)
    def test_traffic_totals(self, v):
        _format_traffic_totals({"rxb": v, "txb": v, "rxs": v, "txs": v})

    @pytest.mark.parametrize("v", WEIRD)
    def test_transport_flow_section(self, v):
        _format_transport_flow_section(
            {"arxb": v, "atxb": v, "arxs": v, "atxs": v, "arxf": v, "atxf": v},
            rxb_key="arxb",
            txb_key="atxb",
            rxs_key="arxs",
            txs_key="atxs",
            rxf_key="arxf",
            txf_key="atxf",
            total_rxs=v,
            total_txs=v,
        )

    @pytest.mark.parametrize("v", WEIRD)
    def test_queue_stats(self, v):
        _format_queue_stats(dict.fromkeys(("tqpressure", "rxqt", "rxqtd"), v))

    @given(v=st.one_of(st.floats(allow_nan=True, allow_infinity=True), st.integers()))
    @settings(max_examples=80, deadline=2000)
    def test_numeric_property(self, v):
        size_str(v)
        speed_str(v)
