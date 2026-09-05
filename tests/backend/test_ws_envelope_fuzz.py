# SPDX-License-Identifier: 0BSD

"""Envelope validation fuzz with closed error codes."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.websocket_runtime import validate_ws_envelope

KNOWN = frozenset({"ping", "config.set", "sync.subscribe", "ws.subscribe"})
CLOSED_ERRORS = frozenset(
    {
        "invalid_envelope",
        "missing_type",
        "invalid_request_id",
        "invalid_destination_hash",
        "invalid_b64_field",
        "invalid_since_seq",
        "invalid_topics",
        "payload_too_large",
        "invalid_uri",
        "invalid_content",
    },
)


@given(
    data=st.one_of(
        st.none(),
        st.integers(),
        st.text(max_size=40),
        st.lists(st.integers(), max_size=5),
        st.dictionaries(
            keys=st.sampled_from(["type", "request_id", "since_seq", "topics", "x"]),
            values=st.one_of(
                st.none(),
                st.integers(),
                st.text(max_size=20),
                st.lists(st.text(max_size=8), max_size=3),
                st.booleans(),
            ),
            max_size=6,
        ),
    ),
)
@settings(max_examples=120, deadline=None)
def test_validate_ws_envelope_closed_outcomes(data):
    msg_type, err = validate_ws_envelope(data, KNOWN)
    if err is not None:
        assert err in CLOSED_ERRORS
    if not isinstance(data, dict):
        assert err == "invalid_envelope"
        return
    t = data.get("type")
    if not isinstance(t, str) or not t.strip():
        assert err == "missing_type"
