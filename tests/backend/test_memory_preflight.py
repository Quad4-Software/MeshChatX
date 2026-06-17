# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

from meshchatx.src.backend.recovery.memory_preflight import (
    evaluate_startup_memory,
    format_memory_log_line,
    parse_memory_log_line,
)


def _mock_memory(total_mb, available_mb, percent):
    mem = MagicMock()
    mem.total = int(total_mb * 1024**2)
    mem.available = int(available_mb * 1024**2)
    mem.percent = percent
    return mem


def test_evaluate_startup_memory_ok():
    with patch(
        "meshchatx.src.backend.recovery.memory_preflight.psutil.virtual_memory",
        return_value=_mock_memory(16384, 8192, 50),
    ):
        result = evaluate_startup_memory(emergency=False)
    assert result["action"] == "ok"
    assert result["low_memory"] is False


def test_evaluate_startup_memory_warn_on_low_total():
    with patch(
        "meshchatx.src.backend.recovery.memory_preflight.psutil.virtual_memory",
        return_value=_mock_memory(4096, 900, 86),
    ):
        result = evaluate_startup_memory(emergency=False)
    assert result["action"] == "warn"
    assert result["low_memory"] is True


def test_evaluate_startup_memory_critical_warn():
    with patch(
        "meshchatx.src.backend.recovery.memory_preflight.psutil.virtual_memory",
        return_value=_mock_memory(4096, 320, 92),
    ):
        result = evaluate_startup_memory(emergency=False)
    assert result["action"] == "warn"
    assert "strongly recommended" in result["message"]


def test_evaluate_startup_memory_abort():
    with patch(
        "meshchatx.src.backend.recovery.memory_preflight.psutil.virtual_memory",
        return_value=_mock_memory(4096, 120, 97),
    ):
        result = evaluate_startup_memory(emergency=False)
    assert result["action"] == "abort"


def test_evaluate_startup_memory_already_in_emergency():
    with patch(
        "meshchatx.src.backend.recovery.memory_preflight.psutil.virtual_memory",
        return_value=_mock_memory(4096, 320, 92),
    ):
        result = evaluate_startup_memory(emergency=True)
    assert result["action"] == "warn"
    assert result["emergency_requested"] is True


def test_format_and_parse_memory_log_line():
    result = {
        "total_mb": 4096.0,
        "available_mb": 512.5,
        "percent_used": 87.5,
        "action": "warn",
        "emergency_requested": False,
    }
    line = format_memory_log_line(result)
    assert line.startswith("MESHCHAT_MEMORY:")
    parsed = parse_memory_log_line(f"booting\n{line}\n")
    assert parsed["available_mb"] == 512.5
    assert parsed["action"] == "warn"
    assert parsed["emergency"] is False
