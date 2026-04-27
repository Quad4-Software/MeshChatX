# SPDX-License-Identifier: 0BSD

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend import reticulum_pathfinding as rp
from meshchatx.src.backend.reticulum_pathfinding import OutboundPathOutcome

DEST = bytes(16)


def _put_path_entry(dest, entry, cleanup: list) -> None:
    with RNS.Transport.path_table_lock:
        RNS.Transport.path_table[dest] = entry
    cleanup.append(dest)


def test_should_rediscover_when_no_path():
    with patch.object(RNS.Transport, "has_path", return_value=False):
        assert rp.should_rediscover_path(DEST) is True


def test_should_rediscover_when_unresponsive():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=True),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        assert rp.should_rediscover_path(DEST) is True


def test_should_rediscover_when_expired():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=True,
        ),
    ):
        assert rp.should_rediscover_path(DEST) is True


def test_no_rediscover_when_fresh():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
    ):
        assert rp.should_rediscover_path(DEST) is False


def test_path_metadata_no_path():
    with patch.object(RNS.Transport, "has_path", return_value=False):
        m = rp.path_metadata_for_api(DEST)
    assert m["path_stale"] is True
    assert m["path_unresponsive"] is False


def test_path_table_entry_expired_ap_mode():
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_ACCESS_POINT
    entry = [
        time.time() - RNS.Transport.AP_PATH_TIME - 5,
        None,
        1,
        0,
        None,
        iface,
        None,
    ]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is True


def test_path_table_entry_fresh_ap_mode():
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_ACCESS_POINT
    entry = [time.time(), None, 1, 0, None, iface, None]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is False


def test_prepare_fresh_drops_and_requests_when_stale():
    r = MagicMock()
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.should_rediscover_path",
            return_value=True,
        ),
        patch.object(RNS.Transport, "request_path") as mock_req,
    ):
        assert rp.prepare_fresh_path_request(r, DEST) == "path_refresh_requested"
        r.drop_path.assert_called_once_with(DEST)
        mock_req.assert_called_once_with(DEST)


def test_prepare_fresh_noop_when_reusing():
    r = MagicMock()
    with (
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.should_rediscover_path",
            return_value=False,
        ),
        patch.object(RNS.Transport, "request_path") as mock_req,
    ):
        assert rp.prepare_fresh_path_request(r, DEST) == "reused_valid_path"
        r.drop_path.assert_not_called()
        mock_req.assert_not_called()


def test_path_table_entry_expired_roaming_mode():
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_ROAMING
    entry = [
        time.time() - RNS.Transport.ROAMING_PATH_TIME - 5,
        None,
        1,
        0,
        None,
        iface,
        None,
    ]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is True


def test_path_table_entry_fresh_roaming_mode():
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_ROAMING
    entry = [time.time(), None, 1, 0, None, iface, None]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is False


def test_path_table_entry_expired_default_mode():
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_FULL
    old = time.time() - RNS.Transport.DESTINATION_TIMEOUT - 1
    entry = [old, None, 1, 0, None, iface, None]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is True


def test_path_table_entry_expired_when_rvcd_if_is_none():
    old = time.time() - RNS.Transport.DESTINATION_TIMEOUT - 1
    entry = [old, None, 1, 0, None, None, None]
    assert rp._path_table_entry_is_expired_by_reticulum_rules(entry) is True


def test_transport_path_table_entry_is_expired_uses_path_table():
    to_del = []
    dest = bytes([0x1B] * 16)
    iface = MagicMock()
    iface.mode = RNS.Interfaces.Interface.Interface.MODE_ROAMING
    _put_path_entry(
        dest,
        [
            time.time() - RNS.Transport.ROAMING_PATH_TIME - 2,
            None,
            1,
            0,
            None,
            iface,
            None,
        ],
        to_del,
    )
    try:
        assert rp.transport_path_table_entry_is_expired(dest) is True
    finally:
        with RNS.Transport.path_table_lock:
            for d in to_del:
                RNS.Transport.path_table.pop(d, None)


def test_path_metadata_when_has_path_stale():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=True,
        ),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=False),
    ):
        m = rp.path_metadata_for_api(DEST)
    assert m == {"path_stale": True, "path_unresponsive": False}


def test_path_metadata_when_unresponsive():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.transport_path_table_entry_is_expired",
            return_value=False,
        ),
        patch.object(RNS.Transport, "path_is_unresponsive", return_value=True),
    ):
        m = rp.path_metadata_for_api(DEST)
    assert m == {"path_stale": False, "path_unresponsive": True}


def test_prepare_fresh_uses_expire_path_without_reticulum():
    with (
        patch.object(RNS.Transport, "has_path", return_value=True),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.should_rediscover_path",
            return_value=True,
        ),
        patch.object(RNS.Transport, "expire_path") as ex,
        patch.object(RNS.Transport, "request_path") as req,
    ):
        assert rp.prepare_fresh_path_request(None, DEST) == "path_refresh_requested"
        ex.assert_called_once_with(DEST)
        req.assert_called_once_with(DEST)


def test_lxmf_path_wait_cap_uses_rns_default():
    v = rp.lxmf_path_wait_cap_seconds()
    assert 30.0 <= v <= 120.0


def test_lxmf_path_wait_cap_falls_back_when_float_fails():
    with patch.object(RNS.Transport, "PATH_REQUEST_TIMEOUT", "x"):
        assert rp.lxmf_path_wait_cap_seconds() == 30.0


def test_nudge_path_request_forwards_to_transport():
    with patch.object(RNS.Transport, "request_path") as m:
        rp.nudge_path_request(DEST)
        m.assert_called_once_with(DEST)


@pytest.mark.asyncio
async def test_meshchat_await_transport_path_delegates_to_module():
    from meshchatx.meshchat import ReticulumMeshChat

    outcome = OutboundPathOutcome(True, "reused_valid_path", False)
    with patch(
        "meshchatx.meshchat.reticulum_pathfinding.await_transport_path_for_outbound_lxmf",
        new=AsyncMock(return_value=outcome),
    ) as m:
        inst = object.__new__(ReticulumMeshChat)
        inst.reticulum = object()
        r = await ReticulumMeshChat._await_transport_path(inst, DEST)
    assert r.path_available is True
    m.assert_called_once_with(inst.reticulum, DEST)


@pytest.mark.asyncio
async def test_await_outbound_lxmf_returns_true_when_path_immediate():
    with (
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.prepare_fresh_path_request",
            return_value="reused_valid_path",
        ) as prep,
        patch.object(
            RNS.Transport,
            "has_path",
            return_value=True,
        ),
    ):
        out = await rp.await_transport_path_for_outbound_lxmf(MagicMock(), DEST)
    assert out.path_available is True
    assert out.prepare_measure == "reused_valid_path"
    assert out.used_nudge is False
    prep.assert_called_once()


def test_format_outbound_path_finding_measure_appends_nudge():
    o = OutboundPathOutcome(True, "new_path_requested", True)
    assert rp.format_outbound_path_finding_measure(o) == "new_path_requested+nudge"
    o2 = OutboundPathOutcome(True, "reused_valid_path", False)
    assert rp.format_outbound_path_finding_measure(o2) == "reused_valid_path"


def test_prepare_fresh_requests_when_no_path_but_rediscover():
    r = MagicMock()
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.should_rediscover_path",
            return_value=True,
        ),
        patch.object(RNS.Transport, "request_path") as mock_req,
    ):
        assert rp.prepare_fresh_path_request(r, DEST) == "new_path_requested"
        r.drop_path.assert_not_called()
        mock_req.assert_called_once_with(DEST)


@pytest.mark.asyncio
async def test_await_outbound_lxmf_returns_false_after_waits_exhausted():
    nudge = MagicMock()
    with (
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.prepare_fresh_path_request",
        ),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.lxmf_path_wait_cap_seconds",
            return_value=0.0,
        ),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.nudge_path_request",
            nudge,
        ),
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.time.time",
            side_effect=[0.0, 0.0, 0.0, 0.0, 100.0],
        ),
    ):
        out = await rp.await_transport_path_for_outbound_lxmf(MagicMock(), DEST)
    assert out.path_available is False
    assert out.used_nudge is True
    nudge.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_path_returns_true_immediately():
    with (
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.prepare_fresh_path_request",
        ) as p,
        patch.object(RNS.Transport, "has_path", return_value=True),
    ):
        ok = await rp.wait_for_path(MagicMock(), DEST, 5.0, 0.01)
    assert ok is True
    p.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_path_times_out():
    with (
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.prepare_fresh_path_request",
        ),
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.asyncio.sleep",
            new_callable=AsyncMock,
        ),
        patch(
            "meshchatx.src.backend.reticulum_pathfinding.time.monotonic",
            side_effect=[0.0, 0.0, 0.02],
        ),
    ):
        ok = await rp.wait_for_path(MagicMock(), DEST, 0.01, 0.01)
    assert ok is False
