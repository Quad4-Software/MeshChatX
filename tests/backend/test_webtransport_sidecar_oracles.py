# SPDX-License-Identifier: 0BSD

"""WebTransport sidecar status and framing oracles."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.webtransport_sidecar import (
    CLOSED_REASONS,
    WT_REASON_DISABLED,
    WT_REASON_HTTP_ONLY,
    build_webtransport_status,
    wt_frame_encode,
    wt_frame_feed,
)


def test_status_disabled_by_default():
    state = build_webtransport_status(
        https_enabled=True,
        sidecar_enabled=False,
        env_enabled=False,
    )
    assert state.server_available is False
    assert state.reason == WT_REASON_DISABLED
    assert state.reason in CLOSED_REASONS


def test_status_http_only():
    state = build_webtransport_status(
        https_enabled=False,
        sidecar_enabled=True,
        env_enabled=True,
    )
    assert state.reason == WT_REASON_HTTP_ONLY


def test_status_dict_shape():
    state = build_webtransport_status(
        https_enabled=True,
        sidecar_enabled=False,
        env_enabled=False,
    )
    d = state.status_dict()
    assert d["experimental"] is True
    assert d["server_available"] is False
    assert d["client_probe_supported"] is True


@given(
    obj=st.fixed_dictionaries(
        {
            "type": st.sampled_from(["ping", "announce", "error"]),
            "n": st.integers(min_value=0, max_value=1000),
        },
    ),
)
@settings(max_examples=40, deadline=None)
def test_wt_frame_round_trip(obj):
    raw = wt_frame_encode(obj).decode("utf-8")
    objects, buf, errors = wt_frame_feed("", raw)
    assert errors == []
    assert buf == ""
    assert objects == [obj]


def test_wt_frame_rejects_oversize_line():
    huge = '{"type":"' + ("a" * (1024 * 1024 + 10)) + '"}\n'
    objects, _buf, errors = wt_frame_feed("", huge)
    assert objects == []
    assert "line_too_large" in errors


def test_wt_frame_rejects_nul():
    objects, _buf, errors = wt_frame_feed("", '{"type":"x\x00"}\n')
    assert "embedded_nul" in errors or "invalid_json" in errors
