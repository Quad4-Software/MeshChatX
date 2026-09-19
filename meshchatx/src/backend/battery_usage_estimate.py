# SPDX-License-Identifier: 0BSD
"""Estimate MeshChatX battery drain from process CPU time.

OS APIs rarely expose per-app battery without privileged permissions.
This module derives a conservative estimate from cumulative process CPU
time versus wall-clock uptime so About can show app-level usage instead
of only the host pack percentage.
"""

from __future__ import annotations

import os
import time
from typing import Any

# Rough calibration: one busy logical core ~ this many battery percent per hour
# on a typical phone or thin laptop. Tuned to be conservative and capped.
_ONE_CORE_PERCENT_PER_HOUR = 10.0
_MAX_PERCENT_PER_HOUR = 40.0
_MIN_UPTIME_FOR_RATE_S = 30.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def drain_intensity(estimated_percent_per_hour: float | None) -> str | None:
    """Map an estimated %/hr rate to a coarse intensity label."""
    if estimated_percent_per_hour is None:
        return None
    if estimated_percent_per_hour < 0.5:
        return "low"
    if estimated_percent_per_hour < 2.0:
        return "moderate"
    if estimated_percent_per_hour < 6.0:
        return "high"
    return "very_high"


def estimate_battery_usage(
    *,
    cpu_time_seconds: float | None,
    uptime_seconds: float | None,
    cpu_count: int | None = 1,
    on_battery: bool | None = None,
    host_level: int | None = None,
) -> dict[str, Any] | None:
    """Build an estimated MeshChatX battery-usage payload.

    avg_cpu_percent is percent of one logical core (may exceed 100 on
    multi-threaded work). machine_share_percent normalizes by CPU count.
    estimated_percent_per_hour is a rough battery pack drain rate.
    """
    if cpu_time_seconds is None or uptime_seconds is None:
        return None
    try:
        cpu_time = float(cpu_time_seconds)
        uptime = float(uptime_seconds)
    except (TypeError, ValueError):
        return None
    if cpu_time < 0 or uptime <= 0:
        return None

    cores = 1
    if cpu_count is not None:
        try:
            cores = max(1, int(cpu_count))
        except (TypeError, ValueError):
            cores = 1

    one_core_fraction = cpu_time / uptime
    avg_cpu_percent = one_core_fraction * 100.0
    machine_share_percent = _clamp((one_core_fraction / cores) * 100.0, 0.0, 100.0)

    estimated_percent_per_hour = None
    confidence = "warming_up"
    if uptime >= _MIN_UPTIME_FOR_RATE_S:
        estimated_percent_per_hour = _clamp(
            one_core_fraction * _ONE_CORE_PERCENT_PER_HOUR,
            0.0,
            _MAX_PERCENT_PER_HOUR,
        )
        confidence = "estimate"

    intensity = drain_intensity(estimated_percent_per_hour)

    return {
        "avg_cpu_percent": round(avg_cpu_percent, 1),
        "machine_share_percent": round(machine_share_percent, 1),
        "estimated_percent_per_hour": (
            round(estimated_percent_per_hour, 1)
            if estimated_percent_per_hour is not None
            else None
        ),
        "intensity": intensity,
        "cpu_time_seconds": round(cpu_time, 2),
        "uptime_seconds": round(uptime, 1),
        "cpu_count": cores,
        "method": "cpu_time",
        "confidence": confidence,
        "on_battery": on_battery,
        "host_level": host_level,
    }


def read_linux_host_battery() -> tuple[int | None, bool | None]:
    """Best-effort host pack reading from sysfs (Linux laptops and some SBCs)."""
    power_root = "/sys/class/power_supply"
    if not os.path.isdir(power_root):
        return None, None
    try:
        entries = sorted(os.listdir(power_root))
    except OSError:
        return None, None

    level = None
    charging = None
    for name in entries:
        base = os.path.join(power_root, name)
        type_path = os.path.join(base, "type")
        try:
            with open(type_path, encoding="utf-8") as handle:
                supply_type = handle.read().strip().lower()
        except OSError:
            continue
        if supply_type != "battery":
            continue
        capacity_path = os.path.join(base, "capacity")
        status_path = os.path.join(base, "status")
        try:
            with open(capacity_path, encoding="utf-8") as handle:
                raw = int(handle.read().strip())
            if 0 <= raw <= 100:
                level = raw
        except (OSError, ValueError):
            pass
        try:
            with open(status_path, encoding="utf-8") as handle:
                status = handle.read().strip().lower()
            if status in ("charging", "full"):
                charging = True
            elif status in ("discharging", "not charging"):
                charging = False
        except OSError:
            pass
        if level is not None:
            break
    return level, charging


def _proc_self_cpu_and_uptime() -> tuple[float | None, float | None]:
    """Read own process CPU time and uptime from /proc/self/stat.

    Fallback for platforms where psutil cannot read process stats, such as
    Android where SELinux restricts /proc access under Chaquopy. Reading
    /proc/self remains allowed. Returns (cpu_seconds, uptime_seconds).
    """
    try:
        with open("/proc/self/stat", encoding="utf-8") as handle:
            stat = handle.read()
        # comm (field 2) may contain spaces and parentheses, so parse the
        # fields after the last ')' where index 0 is state (field 3).
        tail = stat.rpartition(")")[2].split()
        utime = int(tail[11])  # field 14
        stime = int(tail[12])  # field 15
        starttime = int(tail[19])  # field 22
        try:
            ticks = os.sysconf("SC_CLK_TCK")
        except (ValueError, OSError, AttributeError):
            ticks = 100  # USER_HZ is 100 on all Android/Linux kernels
        try:
            with open("/proc/uptime", encoding="utf-8") as handle:
                sys_uptime = float(handle.read().split()[0])
        except OSError:
            try:
                # CLOCK_BOOTTIME shares the epoch of the /proc stat starttime
                # jiffies counter, including time spent suspended. Plain
                # CLOCK_MONOTONIC skips suspend time and can sit below
                # starttime on phones, which would zero the uptime result.
                sys_uptime = time.clock_gettime(time.CLOCK_BOOTTIME)
            except (OSError, AttributeError):
                sys_uptime = time.monotonic()
        cpu_seconds = (utime + stime) / ticks
        uptime_seconds = max(0.0, sys_uptime - starttime / ticks)
        return cpu_seconds, uptime_seconds
    except Exception:
        return None, None


class BatteryUsageTracker:
    """Snapshot MeshChatX process CPU into a battery-usage estimate."""

    def __init__(self) -> None:
        self._last: dict[str, Any] | None = None

    def snapshot(self, process: Any) -> dict[str, Any] | None:
        if process is None:
            # Caller could not build a psutil.Process at all; /proc/self is
            # still readable on platforms like Android, so fall back to it.
            cpu_time, uptime = _proc_self_cpu_and_uptime()
            if cpu_time is None or uptime is None:
                return self._last
        else:
            try:
                times = process.cpu_times()
                cpu_time = float(getattr(times, "user", 0.0)) + float(
                    getattr(times, "system", 0.0),
                )
                create_time = float(process.create_time())
                uptime = max(0.0, time.time() - create_time)
            except Exception:
                cpu_time, uptime = None, None
            if cpu_time is None or uptime is None or uptime <= 0:
                # psutil can succeed but return unusable values on platforms
                # that restrict /proc (Android): fall back to /proc/self.
                cpu_time, uptime = _proc_self_cpu_and_uptime()
            if cpu_time is None or uptime is None:
                return self._last
        try:
            import psutil

            cpu_count = psutil.cpu_count(logical=True) or (os.cpu_count() or 1)
        except Exception:
            cpu_count = os.cpu_count() or 1

        host_level, charging = read_linux_host_battery()
        on_battery = None
        if charging is True:
            on_battery = False
        elif charging is False:
            on_battery = True

        estimate = estimate_battery_usage(
            cpu_time_seconds=cpu_time,
            uptime_seconds=uptime,
            cpu_count=cpu_count,
            on_battery=on_battery,
            host_level=host_level,
        )
        if estimate is not None:
            self._last = estimate
        return estimate
