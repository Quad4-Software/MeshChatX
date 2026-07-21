# SPDX-License-Identifier: 0BSD
"""Oracle tests for LXMF state and method reporting.

Guarantee: MeshChatX API state and method strings match LXMF.LXMessage
constants. Propagation is a delivery method, never a lifecycle state.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import LXMF
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.lxmf_utils import (
    convert_lxmf_message_to_dict,
    convert_lxmf_method_to_string,
    convert_lxmf_state_to_string,
)

# Independent contract: derived from LXMF constant names, not from MeshChatX
# if/elif branches. If LXMF adds a state, this table must be updated deliberately.
LXMF_STATE_ORACLE = {
    LXMF.LXMessage.GENERATING: "generating",
    LXMF.LXMessage.OUTBOUND: "outbound",
    LXMF.LXMessage.SENDING: "sending",
    LXMF.LXMessage.SENT: "sent",
    LXMF.LXMessage.DELIVERED: "delivered",
    LXMF.LXMessage.REJECTED: "rejected",
    LXMF.LXMessage.CANCELLED: "cancelled",
    LXMF.LXMessage.FAILED: "failed",
}

LXMF_METHOD_ORACLE = {
    LXMF.LXMessage.OPPORTUNISTIC: "opportunistic",
    LXMF.LXMessage.DIRECT: "direct",
    LXMF.LXMessage.PROPAGATED: "propagated",
    LXMF.LXMessage.PAPER: "paper",
}

API_LIFECYCLE_STATES = frozenset(LXMF_STATE_ORACLE.values()) | {"unknown"}
API_DELIVERY_METHODS = frozenset(LXMF_METHOD_ORACLE.values()) | {"unknown"}

# LXMF has no lifecycle state for "on propagation node". That meaning is
# method=PROPAGATED + state=SENT (or later DELIVERED).
assert "propagated" not in LXMF_STATE_ORACLE.values()


def _msg(**attrs):
    return SimpleNamespace(**attrs)


def _mock_lxmessage(*, state, method):
    mock_msg = MagicMock(spec=LXMF.LXMessage)
    mock_msg.hash = b"m" * 16
    mock_msg.source_hash = b"s" * 16
    mock_msg.destination_hash = b"d" * 16
    mock_msg.incoming = False
    mock_msg.state = state
    mock_msg.progress = 1.0 if state == LXMF.LXMessage.DELIVERED else 0.0
    mock_msg.method = method
    mock_msg.delivery_attempts = 0
    mock_msg.title = b""
    mock_msg.content = b"hello"
    mock_msg.timestamp = 1_700_000_000
    mock_msg.rssi = None
    mock_msg.snr = None
    mock_msg.q = None
    mock_msg.get_fields.return_value = {}
    mock_msg.outbound_ticket = None
    mock_msg.stamp_cost = None
    mock_msg.stamp = None
    mock_msg.defer_stamp = False
    return mock_msg


@pytest.mark.parametrize(("lxmf_state", "expected"), list(LXMF_STATE_ORACLE.items()))
def test_oracle_state_constant_maps_to_api_string(lxmf_state, expected):
    assert convert_lxmf_state_to_string(_msg(state=lxmf_state)) == expected


@pytest.mark.parametrize(("lxmf_method", "expected"), list(LXMF_METHOD_ORACLE.items()))
def test_oracle_method_constant_maps_to_api_string(lxmf_method, expected):
    assert convert_lxmf_method_to_string(_msg(method=lxmf_method)) == expected


@given(state=st.sampled_from(list(LXMF_STATE_ORACLE.keys())))
@settings(max_examples=64, deadline=None)
def test_oracle_known_states_never_unknown(state):
    reported = convert_lxmf_state_to_string(_msg(state=state))
    assert reported == LXMF_STATE_ORACLE[state]
    assert reported != "unknown"


@given(method=st.sampled_from(list(LXMF_METHOD_ORACLE.keys())))
@settings(max_examples=32, deadline=None)
def test_oracle_known_methods_never_unknown(method):
    reported = convert_lxmf_method_to_string(_msg(method=method))
    assert reported == LXMF_METHOD_ORACLE[method]
    assert reported != "unknown"


@given(
    state=st.integers(min_value=0, max_value=512).filter(
        lambda v: v not in LXMF_STATE_ORACLE
    )
)
@settings(max_examples=80, deadline=None)
def test_oracle_unknown_state_ints_report_unknown(state):
    assert convert_lxmf_state_to_string(_msg(state=state)) == "unknown"


@given(
    method=st.integers(min_value=0, max_value=64).filter(
        lambda v: v not in LXMF_METHOD_ORACLE
    )
)
@settings(max_examples=40, deadline=None)
def test_oracle_unknown_method_ints_report_unknown(method):
    assert convert_lxmf_method_to_string(_msg(method=method)) == "unknown"


@given(
    state=st.sampled_from(list(LXMF_STATE_ORACLE.keys())),
    method=st.sampled_from(list(LXMF_METHOD_ORACLE.keys())),
)
@settings(max_examples=64, deadline=None)
def test_oracle_message_dict_reports_lxmf_status_pair(state, method):
    """API dict state/method must match converters and stay in closed vocabularies."""
    payload = convert_lxmf_message_to_dict(_mock_lxmessage(state=state, method=method))
    expected_state = LXMF_STATE_ORACLE[state]
    expected_method = LXMF_METHOD_ORACLE[method]
    assert payload["state"] == expected_state
    assert payload["method"] == expected_method
    assert payload["state"] in API_LIFECYCLE_STATES
    assert payload["method"] in API_DELIVERY_METHODS
    # Propagation is method-only. Lifecycle must never be labeled "propagated".
    assert payload["state"] != "propagated"


def test_oracle_propagated_sent_is_on_node_not_delivered():
    """Parked on a propagation node is SENT + PROPAGATED, not DELIVERED."""
    payload = convert_lxmf_message_to_dict(
        _mock_lxmessage(state=LXMF.LXMessage.SENT, method=LXMF.LXMessage.PROPAGATED)
    )
    assert payload["state"] == "sent"
    assert payload["method"] == "propagated"


def test_oracle_propagated_delivered_means_recipient_got_mail():
    payload = convert_lxmf_message_to_dict(
        _mock_lxmessage(
            state=LXMF.LXMessage.DELIVERED,
            method=LXMF.LXMessage.PROPAGATED,
        )
    )
    assert payload["state"] == "delivered"
    assert payload["method"] == "propagated"


def test_oracle_direct_delivered_is_not_propagated():
    payload = convert_lxmf_message_to_dict(
        _mock_lxmessage(state=LXMF.LXMessage.DELIVERED, method=LXMF.LXMessage.DIRECT)
    )
    assert payload["state"] == "delivered"
    assert payload["method"] == "direct"


def test_oracle_opportunistic_failed_still_reports_failed_state():
    """Backend keeps LXMF FAILED. UI may treat opportunistic+failed as deferred wait."""
    payload = convert_lxmf_message_to_dict(
        _mock_lxmessage(
            state=LXMF.LXMessage.FAILED,
            method=LXMF.LXMessage.OPPORTUNISTIC,
        )
    )
    assert payload["state"] == "failed"
    assert payload["method"] == "opportunistic"


def test_oracle_paper_method_preserved_across_states():
    for state, state_name in (
        (LXMF.LXMessage.SENT, "sent"),
        (LXMF.LXMessage.DELIVERED, "delivered"),
    ):
        payload = convert_lxmf_message_to_dict(
            _mock_lxmessage(state=state, method=LXMF.LXMessage.PAPER)
        )
        assert payload["state"] == state_name
        assert payload["method"] == "paper"


def test_lxmf_status_oracle_proved():
    """PROVED marker: full known state/method tables convert correctly."""
    for lxmf_state, expected in LXMF_STATE_ORACLE.items():
        assert convert_lxmf_state_to_string(_msg(state=lxmf_state)) == expected
    for lxmf_method, expected in LXMF_METHOD_ORACLE.items():
        assert convert_lxmf_method_to_string(_msg(method=lxmf_method)) == expected
    print("LXMF_STATUS_REPORTING_PROVED")
