"""
Regression tests for conversation/bell unread semantics: no false positives from
outgoing-latest threads or inconsistent read cursors.
"""

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.lxmf_utils import compute_lxmf_conversation_unread_from_latest_row


def _row(incoming, last_read_iso, ts):
    return {
        "is_incoming": incoming,
        "last_read_at": last_read_iso,
        "timestamp": ts,
    }


class TestComputeLxmfUnreadFromRow:
    def test_outgoing_never_unread(self):
        base_ts = 1_700_000_000.0
        for last in (None, datetime.fromtimestamp(base_ts - 1, UTC).isoformat()):
            assert (
                compute_lxmf_conversation_unread_from_latest_row(
                    _row(0, last, base_ts),
                )
                is False
            )
            assert (
                compute_lxmf_conversation_unread_from_latest_row(
                    _row(False, last, base_ts),
                )
                is False
            )

    def test_incoming_unread_when_no_read_cursor(self):
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                _row(1, None, 1_700_000_000.0),
            )
            is True
        )

    def test_incoming_unread_when_bool_true(self):
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                _row(True, None, 1_700_000_000.0),
            )
            is True
        )

    @settings(max_examples=200)
    @given(
        ts=st.floats(
            min_value=1_000_000_000.0,
            max_value=2_000_000_000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        delta=st.floats(
            min_value=1.0,
            max_value=86_400.0,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_incoming_newer_than_read_always_unread(self, ts, delta):
        read_at = datetime.fromtimestamp(ts - delta, UTC).isoformat()
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                _row(1, read_at, ts),
            )
            is True
        )

    @settings(max_examples=200)
    @given(
        ts=st.floats(
            min_value=1_000_000_100.0,
            max_value=2_000_000_000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        delta=st.floats(
            min_value=0.001,
            max_value=86_400.0,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_incoming_older_or_equal_read_never_unread(self, ts, delta):
        read_at = datetime.fromtimestamp(ts + delta, UTC).isoformat()
        assert (
            compute_lxmf_conversation_unread_from_latest_row(
                _row(1, read_at, ts),
            )
            is False
        )


@pytest.mark.parametrize(
    ("incoming", "expect_unread"),
    [
        (0, False),
        (1, True),
    ],
)
def test_sqlite_integer_incoming_flags(incoming, expect_unread):
    row = _row(incoming, None, 1_700_000_000.0)
    assert compute_lxmf_conversation_unread_from_latest_row(row) is expect_unread
