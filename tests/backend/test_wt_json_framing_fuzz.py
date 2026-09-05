# SPDX-License-Identifier: 0BSD

"""Newline JSON framing fuzz for experimental WebTransport."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.webtransport_sidecar import wt_frame_encode, wt_frame_feed

CLOSED_ERRORS = frozenset(
    {
        "frame_overflow",
        "line_too_large",
        "embedded_nul",
        "invalid_json",
        "not_object",
    },
)


@given(
    obj=st.fixed_dictionaries(
        {
            "type": st.sampled_from(["ping", "announce", "lxmf.delivery", "error"]),
            "seq": st.integers(min_value=0, max_value=10_000),
        },
    ),
)
@settings(max_examples=60, deadline=None)
def test_valid_objects_round_trip(obj):
    raw = wt_frame_encode(obj).decode("utf-8")
    objects, buf, errors = wt_frame_feed("", raw)
    assert errors == []
    assert buf == ""
    assert objects == [obj]


@given(chunk=st.text(max_size=200))
@settings(max_examples=80, deadline=None)
def test_arbitrary_chunks_closed_errors_or_partial_buffer(chunk):
    objects, buf, errors = wt_frame_feed("", chunk if chunk.endswith("\n") else chunk)
    for err in errors:
        assert err in CLOSED_ERRORS
    assert isinstance(objects, list)
    assert isinstance(buf, str)


def test_truncated_line_stays_in_buffer():
    objects, buf, errors = wt_frame_feed("", '{"type":"ping"')
    assert objects == []
    assert errors == []
    assert "ping" in buf


def test_embedded_nul_rejected():
    _objects, _buf, errors = wt_frame_feed("", '{"type":"x\\u0000"}\n')
    # JSON may accept unicode nul as character; binary NUL path:
    _objects2, _buf2, errors2 = wt_frame_feed("", '{"type":"x\x00"}\n')
    assert "embedded_nul" in errors2 or "invalid_json" in errors2
