# SPDX-License-Identifier: 0BSD
"""Metamorphic properties for periodic-action scheduling helpers."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.constants import MIN_ANNOUNCE_INTERVAL_SECONDS
from meshchatx.src.backend.meshchat_utils import (
    clamp_interval_floor,
    interval_action_due,
)

SANE = st.integers(min_value=-1000, max_value=10_000_000)


class TestClampIntervalFloor:
    @given(v=SANE)
    @settings(max_examples=100, deadline=2000)
    def test_positive_sub_floor_raised(self, v):
        out = clamp_interval_floor(v)
        if (
            isinstance(v, int)
            and not isinstance(v, bool)
            and 0 < v < MIN_ANNOUNCE_INTERVAL_SECONDS
        ):
            assert out == MIN_ANNOUNCE_INTERVAL_SECONDS
        else:
            assert out == v

    @given(v=SANE)
    @settings(max_examples=100, deadline=2000)
    def test_idempotent(self, v):
        once = clamp_interval_floor(v)
        assert clamp_interval_floor(once) == once

    @given(
        a=st.integers(min_value=1, max_value=10_000_000),
        b=st.integers(min_value=1, max_value=10_000_000),
    )
    @settings(max_examples=100, deadline=2000)
    def test_monotonic_on_positives(self, a, b):
        if a <= b:
            assert clamp_interval_floor(a) <= clamp_interval_floor(b)

    def test_zero_negative_none_pass_through(self):
        assert clamp_interval_floor(0) == 0
        assert clamp_interval_floor(-50) == -50
        assert clamp_interval_floor(None) is None
        assert clamp_interval_floor("bogus") == "bogus"


class TestIntervalActionDue:
    def test_disabled_never_due(self):
        assert interval_action_due(False, None, 60, now=1000.0) is False
        assert interval_action_due(False, 0, 60, now=1e12) is False

    def test_never_run_before_is_due(self):
        assert interval_action_due(True, None, 3600, now=1000.0) is True

    def test_nonpositive_interval_never_due(self):
        assert interval_action_due(True, None, 0, now=1000.0) is False
        assert interval_action_due(True, None, -5, now=1000.0) is False

    def test_just_run_is_not_due(self):
        assert interval_action_due(True, 1000, 3600, now=1000.0) is False
        assert interval_action_due(True, 1000, 3600, now=1000.5) is False

    def test_interval_elapsed_is_due(self):
        # strict >: exactly at the boundary is not yet due
        assert interval_action_due(True, 1000, 3600, now=1000.0 + 3600) is False
        assert interval_action_due(True, 1000, 3600, now=1000.0 + 3600.001) is True

    def test_future_last_at_treated_as_due(self):
        # Corrupted/restored future timestamp must not stall scheduling.
        assert interval_action_due(True, 5000, 3600, now=1000.0) is True

    @given(
        last=st.integers(min_value=0, max_value=10**9),
        now=st.integers(min_value=0, max_value=10**9),
        shift=st.integers(min_value=1, max_value=10**9),
    )
    @settings(max_examples=200, deadline=2000)
    def test_time_shift_invariance(self, last, now, shift):
        # Shifting both timestamps must not change the decision: scheduling
        # depends on elapsed time, not the absolute epoch.
        base = interval_action_due(True, last, 3600, now=now)
        shifted = interval_action_due(True, last + shift, 3600, now=now + shift)
        assert base == shifted

    @given(
        last=st.integers(min_value=0, max_value=10**9),
        short_iv=st.integers(min_value=1, max_value=10**6),
        now=st.integers(min_value=0, max_value=10**9),
    )
    @settings(max_examples=200, deadline=2000)
    def test_longer_interval_never_due_sooner(self, last, short_iv, now):
        long_iv = short_iv * 10
        if interval_action_due(True, last, long_iv, now=now):
            assert interval_action_due(True, last, short_iv, now=now)

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
    def test_weird_timestamps_do_not_crash(self, bad):
        interval_action_due(True, bad, 3600, now=1000.0)
        interval_action_due(True, 1000, 3600, now=bad)
