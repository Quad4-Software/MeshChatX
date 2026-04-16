import asyncio
import tracemalloc
import time
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend.telephone_manager import TelephoneManager


@pytest.fixture
def telephone_manager():
    tm = TelephoneManager(identity=MagicMock())
    tm.telephone = MagicMock()
    tm.telephone.busy = False
    tm.telephone.call_status = 3
    tm.telephone.active_call = None
    tm._path_poll_interval_s = 0.005
    tm._path_retry_interval_s = 0.01
    tm._status_poll_interval_s = 0.01
    tm._status_events = []
    tm.on_initiation_status_callback = lambda status, _target: tm._status_events.append(
        status
    )
    return tm


@pytest.mark.asyncio
async def test_initiate_retries_path_requests_during_lookup(telephone_manager):
    destination_hash = bytes.fromhex("aa" * 16)
    state = {"calls": 0}
    telephone_manager._path_retry_interval_s = 0.0

    def has_path(_destination_hash):
        state["calls"] += 1
        return state["calls"] >= 8

    telephone_manager.telephone.call.side_effect = lambda _identity: setattr(
        telephone_manager.telephone, "call_status", 0
    )

    with (
        patch("meshchatx.src.backend.telephone_manager.RNS.Identity.recall", return_value=MagicMock()),
        patch("meshchatx.src.backend.telephone_manager.RNS.Transport.has_path", side_effect=has_path),
        patch("meshchatx.src.backend.telephone_manager.RNS.Transport.request_path") as request_path,
    ):
        await telephone_manager.initiate(destination_hash, timeout_seconds=1)

    assert request_path.call_count >= 1


@pytest.mark.asyncio
async def test_initiate_cancels_quickly_while_finding_path_identity(telephone_manager):
    destination_hash = bytes.fromhex("bb" * 16)
    cancellation_triggered = {"done": False}

    def request_path_and_cancel(_destination_hash):
        if not cancellation_triggered["done"]:
            cancellation_triggered["done"] = True
            telephone_manager._update_initiation_status(None, None)

    with (
        patch("meshchatx.src.backend.telephone_manager.RNS.Identity.recall", return_value=None),
        patch("meshchatx.src.backend.telephone_manager.RNS.Transport.has_path", return_value=False),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.request_path",
            side_effect=request_path_and_cancel,
        ),
    ):
        task = asyncio.create_task(telephone_manager.initiate(destination_hash, timeout_seconds=5))
        result = await asyncio.wait_for(task, timeout=0.3)

    assert result is None


@pytest.mark.asyncio
async def test_initiate_cancels_quickly_while_dialling(telephone_manager):
    destination_hash = bytes.fromhex("cc" * 16)
    telephone_manager.telephone.call_status = 2

    def blocking_call(_identity):
        time.sleep(0.2)

    telephone_manager.telephone.call.side_effect = blocking_call

    with (
        patch("meshchatx.src.backend.telephone_manager.RNS.Identity.recall", return_value=MagicMock()),
        patch("meshchatx.src.backend.telephone_manager.RNS.Transport.has_path", return_value=True),
    ):
        task = asyncio.create_task(telephone_manager.initiate(destination_hash, timeout_seconds=5))
        for _ in range(200):
            if telephone_manager.initiation_status in ("Establishing link...", "Calling..."):
                break
            await asyncio.sleep(0)

        telephone_manager._update_initiation_status(None, None)

        result = await asyncio.wait_for(task, timeout=0.5)

    assert result is None
    assert telephone_manager.telephone.hangup.called


@pytest.mark.asyncio
async def test_cancel_between_identity_resolved_and_path_request(telephone_manager):
    destination_hash = bytes.fromhex("dd" * 16)

    async def cancel_during_path(*_args, **_kwargs):
        telephone_manager._update_initiation_status(None, None)
        return False

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=False,
        ),
        patch.object(telephone_manager, "_await_path", side_effect=cancel_during_path),
    ):
        result = await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=1),
            timeout=0.3,
        )

    assert result is None
    assert not telephone_manager.telephone.call.called


@pytest.mark.asyncio
async def test_cancel_after_path_found_before_dialling_stabilizes(telephone_manager):
    destination_hash = bytes.fromhex("ee" * 16)

    def slow_call(_identity):
        time.sleep(0.1)
        telephone_manager.telephone.call_status = 0

    telephone_manager.telephone.call.side_effect = slow_call

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
    ):
        task = asyncio.create_task(telephone_manager.initiate(destination_hash, timeout_seconds=2))
        for _ in range(200):
            if telephone_manager.initiation_status == "Establishing link...":
                break
            await asyncio.sleep(0)
        telephone_manager._update_initiation_status(None, None)
        result = await asyncio.wait_for(task, timeout=0.4)

    assert result is None
    assert telephone_manager.telephone.hangup.called


@pytest.mark.asyncio
async def test_request_path_exceptions_do_not_abort_discovery(telephone_manager):
    destination_hash = bytes.fromhex("12" * 16)
    has_path_calls = {"count": 0}

    def has_path(_destination_hash):
        has_path_calls["count"] += 1
        return has_path_calls["count"] > 5

    request_errors = [RuntimeError("boom-1"), RuntimeError("boom-2"), None]

    def request_path(_destination_hash):
        value = request_errors.pop(0) if request_errors else None
        if isinstance(value, Exception):
            raise value

    telephone_manager.telephone.call.side_effect = lambda _identity: setattr(
        telephone_manager.telephone, "call_status", 0
    )

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            side_effect=has_path,
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.request_path",
            side_effect=request_path,
        ) as mocked_request_path,
    ):
        await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=1),
            timeout=0.5,
        )

    assert mocked_request_path.call_count >= 2


@pytest.mark.asyncio
async def test_flapping_path_state_recovers_and_dials(telephone_manager):
    destination_hash = bytes.fromhex("34" * 16)
    path_states = [False, True, False, True, True]

    def has_path(_destination_hash):
        if path_states:
            return path_states.pop(0)
        return True

    telephone_manager.telephone.call.side_effect = lambda _identity: setattr(
        telephone_manager.telephone, "call_status", 0
    )

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            side_effect=has_path,
        ),
        patch("meshchatx.src.backend.telephone_manager.RNS.Transport.request_path"),
    ):
        result = await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=1),
            timeout=0.5,
        )

    assert result is None
    assert telephone_manager.telephone.call.called


@pytest.mark.asyncio
async def test_call_thread_exception_surfaces_without_hanging(telephone_manager):
    destination_hash = bytes.fromhex("56" * 16)
    telephone_manager.telephone.call.side_effect = RuntimeError("dial failed")

    async def no_wait(_seconds):
        return None

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
        patch("meshchatx.src.backend.telephone_manager.asyncio.sleep", side_effect=no_wait),
    ):
        result = await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=1),
            timeout=0.5,
        )

    assert result is None
    assert telephone_manager.initiation_status is None


@pytest.mark.asyncio
async def test_inconsistent_call_status_finishes_within_timeout(telephone_manager):
    destination_hash = bytes.fromhex("78" * 16)

    def inconsistent_call(_identity):
        telephone_manager.telephone.call_status = 5
        return None

    telephone_manager.telephone.call.side_effect = inconsistent_call
    async def no_wait(_seconds):
        return None

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
        patch("meshchatx.src.backend.telephone_manager.asyncio.sleep", side_effect=no_wait),
    ):
        result = await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=0.2),
            timeout=0.8,
        )

    assert result is None


@pytest.mark.asyncio
async def test_lxst_status_mapping_updates_ui_initiation_states(telephone_manager):
    destination_hash = bytes.fromhex("9a" * 16)

    def status_progression_call(_identity):
        telephone_manager.telephone.call_status = 2
        time.sleep(0.02)
        telephone_manager.telephone.call_status = 4
        time.sleep(0.02)
        telephone_manager.telephone.call_status = 5
        time.sleep(0.02)
        telephone_manager.telephone.call_status = 0

    telephone_manager.telephone.call.side_effect = status_progression_call

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
    ):
        await asyncio.wait_for(
            telephone_manager.initiate(destination_hash, timeout_seconds=1),
            timeout=0.8,
        )

    assert "Calling..." in telephone_manager._status_events
    assert "Ringing..." in telephone_manager._status_events
    assert "Establishing link..." in telephone_manager._status_events
    assert telephone_manager.initiation_status is None


@pytest.mark.asyncio
async def test_lxst_busy_and_rejected_end_without_stuck_status(telephone_manager):
    destination_hash = bytes.fromhex("bc" * 16)

    for terminal_state in (0, 1):
        telephone_manager._status_events.clear()
        telephone_manager.telephone.call_status = 3
        telephone_manager.telephone.call.side_effect = lambda _identity, state=terminal_state: setattr(
            telephone_manager.telephone, "call_status", state
        )

        with (
            patch(
                "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
                return_value=MagicMock(),
            ),
            patch(
                "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
                return_value=True,
            ),
        ):
            result = await asyncio.wait_for(
                telephone_manager.initiate(destination_hash, timeout_seconds=0.6),
                timeout=0.8,
            )

        assert result is None
        assert telephone_manager.initiation_status is None


@pytest.mark.asyncio
async def test_rapid_dial_cancel_soak_has_bounded_memory(telephone_manager):
    destination_hash = bytes.fromhex("de" * 16)
    loops = 120

    def slow_call(_identity):
        time.sleep(0.03)
        telephone_manager.telephone.call_status = 2

    telephone_manager.telephone.call.side_effect = slow_call

    with (
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Identity.recall",
            return_value=MagicMock(),
        ),
        patch(
            "meshchatx.src.backend.telephone_manager.RNS.Transport.has_path",
            return_value=True,
        ),
    ):
        tracemalloc.start()
        for _ in range(loops):
            telephone_manager.telephone.call_status = 3
            task = asyncio.create_task(telephone_manager.initiate(destination_hash, timeout_seconds=1))
            await asyncio.sleep(0.005)
            telephone_manager._update_initiation_status(None, None)
            await asyncio.wait_for(task, timeout=0.5)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Keep this lax enough for CI variance while still catching obvious leaks.
    assert peak < 80 * 1024 * 1024
