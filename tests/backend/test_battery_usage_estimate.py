# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.battery_usage_estimate import (
    BatteryUsageTracker,
    drain_intensity,
    estimate_battery_usage,
)


def test_estimate_scales_with_cpu_time():
    idle = estimate_battery_usage(
        cpu_time_seconds=6.0,
        uptime_seconds=600.0,
        cpu_count=4,
    )
    assert idle is not None
    assert idle["avg_cpu_percent"] == 1.0
    assert idle["machine_share_percent"] == 0.2
    assert idle["estimated_percent_per_hour"] == 0.1
    assert idle["intensity"] == "low"
    assert idle["confidence"] == "estimate"
    assert idle["method"] == "cpu_time"

    busy = estimate_battery_usage(
        cpu_time_seconds=300.0,
        uptime_seconds=600.0,
        cpu_count=4,
    )
    assert busy is not None
    assert busy["avg_cpu_percent"] == 50.0
    assert busy["estimated_percent_per_hour"] == 5.0
    assert busy["intensity"] == "high"


def test_estimate_warms_up_before_rate():
    early = estimate_battery_usage(
        cpu_time_seconds=1.0,
        uptime_seconds=10.0,
        cpu_count=2,
    )
    assert early is not None
    assert early["estimated_percent_per_hour"] is None
    assert early["confidence"] == "warming_up"
    assert early["intensity"] is None


def test_estimate_rejects_bad_inputs():
    assert estimate_battery_usage(cpu_time_seconds=None, uptime_seconds=10) is None
    assert estimate_battery_usage(cpu_time_seconds=-1, uptime_seconds=10) is None
    assert estimate_battery_usage(cpu_time_seconds=1, uptime_seconds=0) is None


def test_drain_intensity_buckets():
    assert drain_intensity(0.2) == "low"
    assert drain_intensity(1.0) == "moderate"
    assert drain_intensity(3.0) == "high"
    assert drain_intensity(9.0) == "very_high"
    assert drain_intensity(None) is None


def test_tracker_snapshot_from_fake_process():
    class _Times:
        user = 12.0
        system = 3.0

    class _Proc:
        def cpu_times(self):
            return _Times()

        def create_time(self):
            import time

            return time.time() - 120.0

    tracker = BatteryUsageTracker()
    snap = tracker.snapshot(_Proc())
    assert snap is not None
    assert snap["cpu_time_seconds"] == 15.0
    assert snap["uptime_seconds"] >= 119.0
    assert snap["estimated_percent_per_hour"] is not None
